# Updated 2017 for xcat test purpose
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Base conductor manager functionality."""

import inspect
import threading

import futurist
from futurist import periodics
from futurist import rejection
from oslo_db import exception as db_exception
from oslo_log import log
from oslo_utils import excutils

from xcat3.common import exception
from xcat3.common.i18n import _, _LC, _LE, _LI, _LW
from xcat3.common import rpc
from xcat3.conf import CONF
from xcat3.db import api as dbapi
from xcat3.network import rpcapi as network_api
from xcat3 import objects

LOG = log.getLogger(__name__)


class BaseConductorManager(object):
    def __init__(self, host, topic):
        super(BaseConductorManager, self).__init__()
        if not host:
            host = CONF.host
        self.host = host
        self.topic = topic
        self.sensors_notifier = rpc.get_sensors_notifier()
        self._started = False
        self.type = 'conductor'
        self.network_api = network_api.NetworkAPI()

    def init_host(self, admin_context=None):
        """Initialize the conductor host.

        :param admin_context: the admin context to pass to periodic tasks.
        :raises: RuntimeError when conductor is already running.
        """
        if self._started:
            raise RuntimeError(_('Attempt to start an already running '
                                 'conductor manager'))

        self.dbapi = dbapi.get_instance()

        self._keepalive_evt = threading.Event()

        rejection_func = rejection.reject_when_reached(
            CONF.conductor.workers_pool_size)
        self._executor = futurist.GreenThreadPoolExecutor(
            max_workers=CONF.conductor.workers_pool_size,
            check_and_reject=rejection_func)

        self._periodic_task_callables = []
        self._collect_periodic_tasks(self, (admin_context,))
        if (len(self._periodic_task_callables) >
                CONF.conductor.workers_pool_size):
            LOG.warning(_LW('This conductor has %(tasks)d periodic tasks '
                            'enabled, but only %(workers)d task workers '
                            'allowed by [conductor]workers_pool_size option'),
                        {'tasks': len(self._periodic_task_callables),
                         'workers': CONF.conductor.workers_pool_size})

        self._periodic_tasks = periodics.PeriodicWorker(
            self._periodic_task_callables,
            executor_factory=periodics.ExistingExecutor(self._executor))

        # Start periodic tasks
        self._periodic_tasks_worker = self._executor.submit(
            self._periodic_tasks.start, allow_empty=True)
        self._periodic_tasks_worker.add_done_callback(
            self._on_periodic_tasks_stop)
        try:
            # Register this service with the cluster
            self.service = objects.Service.register(
                admin_context, self.host, self.type)
        except exception.ServiceAlreadyRegistered:
            # This service was already registered and did not shut down
            # properly, so log a warning and update the record.
            LOG.warning(
                _LW(
                    "A service with hostname %(hostname)s type %(type)s"
                    " was previously registered. Updating registration"),
                {'hostname': self.host, 'type': self.type})
            self.service = objects.Service.register(
                admin_context, self.host, self.type, update_existing=True)

        # Spawn a dedicated greenthread for the keepalive
        try:
            self._spawn_worker(self._service_record_keepalive)
            LOG.info(_LI('Successfully started service with hostname '
                         '%(hostname)s type %(type)s.'),
                     {'hostname': self.host, 'type': self.type})
        except exception.NoFreeServiceWorker:
            with excutils.save_and_reraise_exception():
                LOG.critical(_LC('Failed to start keepalive'))
                self.del_host()

        self._started = True

    def del_host(self, deregister=True):
        # Conductor deregistration fails if called on non-initialized
        # service (e.g. when rpc server is unreachable).
        if not hasattr(self, 'service'):
            return
        self._keepalive_evt.set()
        if deregister:
            try:
                # Inform the cluster that this service is shutting down.
                # Note that rebalancing will not occur immediately, but when
                # the periodic sync takes place.
                self.service.unregister()
                LOG.info(_LI('Successfully stopped service with hostname '
                             '%(hostname)s type %(type)s.'),
                         {'hostname': self.host, 'type': self.type})
            except exception.ServiceNotFound:
                pass
        else:
            LOG.info(_LI('Not deregistering service with hostname '
                         '%(hostname)s type %(type)s.'),
                     {'hostname': self.host, 'type': self.type})
        # Waiting here to give workers the chance to finish. This has the
        # benefit of releasing locks workers placed on nodes, as well as
        # having work complete normally.
        self._periodic_tasks.stop()
        self._periodic_tasks.wait()
        self._executor.shutdown(wait=True)
        self._started = False

    def _collect_periodic_tasks(self, obj, args):
        """Collect periodic tasks from a given object.

        Populates self._periodic_task_callables with tuples
        (callable, args, kwargs).

        :param obj: object containing periodic tasks as methods
        :param args: tuple with arguments to pass to every task
        """
        for name, member in inspect.getmembers(obj):
            if periodics.is_periodic(member):
                LOG.debug('Found periodic task %(owner)s.%(member)s',
                          {'owner': obj.__class__.__name__,
                           'member': name})
                self._periodic_task_callables.append((member, args, {}))

    def _on_periodic_tasks_stop(self, fut):
        try:
            fut.result()
        except Exception as exc:
            LOG.critical(_LC('Periodic tasks worker has failed: %s'), exc)
        else:
            LOG.info(_LI('Successfully shut down periodic tasks'))

    def _spawn_worker(self, func, *args, **kwargs):
        """Create a greenthread to run func(*args, **kwargs).

        Spawns a greenthread if there are free slots in pool, otherwise raises
        exception. Execution control returns immediately to the caller.

        :returns: Future object.
        :raises: NoFreeServiceWorker if worker pool is currently full.

        """
        try:
            return self._executor.submit(func, *args, **kwargs)
        except futurist.RejectedSubmission:
            raise exception.NoFreeServiceWorker()

    def _service_record_keepalive(self):
        while not self._keepalive_evt.is_set():
            try:
                self.service.touch()
            except db_exception.DBConnectionError:
                LOG.warning(_LW('Conductor could not connect to database '
                                'while heartbeating.'))
            self._keepalive_evt.wait(CONF.heartbeat_interval)
