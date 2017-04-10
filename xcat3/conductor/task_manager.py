# coding=utf-8

# Copyright 2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
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

"""
A context manager to perform a series of tasks on a set of resources.

:class:`TaskManager` is a context manager, created on-demand to allow
synchronized access to a nodes and its resources.

The :class:`TaskManager` will, by default, acquire an exclusive lock on
nodes for the duration that the TaskManager instance exists. You may
create a TaskManager instance without locking by passing "shared=True"
when creating it, but certain operations on the resources held by such
an instance of TaskManager will not be possible. Requiring this exclusive
lock guards against parallel operations interfering with each other.

A shared lock is useful when performing non-interfering operations,
such as validating the driver interfaces.

An exclusive lock is stored in the database to coordinate between
:class:`xcat3.conductor.manager` instances, that are typically deployed on
different hosts.

:class:`TaskManager` methods, as well as driver methods, may be decorated to
determine whether their invocation requires an exclusive lock.

The TaskManager instance exposes certain nodes resources and properties as
attributes that you may access:

    task.context
        The context passed to TaskManager()
    task.shared
        False if Node is locked, True if it is not locked. (The
        'shared' kwarg arg of TaskManager())
    task.nodes
        The Node object
Example usage:

::

    with task_manager.acquire(context, node_name, purpose='power on') as task:
        task.driver.power.power_on(task.nodes)

If you need to execute task-requiring code in a background thread, the
TaskManager instance provides an interface to handle this for you, making
sure to release resources when the thread finishes (successfully or if
an exception occurs). Common use of this is within the Manager like so:

::

    with task_manager.acquire(context, node_id, purpose='some work') as task:
        <do some work>
        task.spawn_after(self._spawn_worker,
                         utils.node_power_action, task, new_state)

All exceptions that occur in the current GreenThread as part of the
spawn handling are re-raised. You can specify a hook to execute custom
code when such exceptions occur. For example, the hook is a more elegant
solution than wrapping the "with task_manager.acquire()" with a
try..exception block. (Note that this hook does not handle exceptions
raised in the background thread.):

::

    def on_error(e):
        if isinstance(e, Exception):
            ...

    with task_manager.acquire(context, node_name, purpose='some work') as task:
        <do some work>
        task.set_spawn_error_hook(on_error)
        task.spawn_after(self._spawn_worker,
                         utils.node_power_action, task, new_state)

"""

import copy

import futurist
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import timeutils
import retrying
import six

from xcat3.common import exception
from xcat3.common.i18n import _, _LE, _LI, _LW
from xcat3 import objects

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


def require_exclusive_lock(f):
    """Decorator to require an exclusive lock.

    Decorated functions must take a :class:`TaskManager` as the first
    parameter. Decorated class methods should take a :class:`TaskManager`
    as the first parameter after "self".

    """

    @six.wraps(f)
    def wrapper(*args, **kwargs):
        # NOTE(dtantsur): this code could be written simpler, but then unit
        # testing decorated functions is pretty hard, as we usually pass a Mock
        # object instead of TaskManager there.
        if len(args) > 1:
            task = args[1] if isinstance(args[1], TaskManager) else args[0]
        else:
            task = args[0]
        if task.shared:
            raise exception.ExclusiveLockRequired()
        # NOTE(lintan): This is a workaround to set the context of async tasks,
        # which should contain an exclusive lock.
        task.context.ensure_thread_contain_context()
        return f(*args, **kwargs)

    return wrapper


def acquire(context, node_names, shared=False, obj_info=None,
            purpose='unspecified action'):
    """Shortcut for acquiring a lock on a Node.

    :param context: Request context.
    :param node_names: nodes to lock.
    :param shared: Boolean indicating whether to take a shared or exclusive
                   lock. Default: False.
    :param purpose: human-readable purpose to put to debug logs.
    :returns: An instance of :class:`TaskManager`.

    """
    # NOTE(lintan): This is a workaround to set the context of periodic tasks.
    context.ensure_thread_contain_context()
    return TaskManager(context, node_names, shared=shared, obj_info=obj_info,
                       purpose=purpose)


class TaskManager(object):
    """Context manager for tasks.

    This class wraps the locking, driver loading, and acquisition
    of related resources (eg, Node and Ports) when beginning a unit of work.

    """

    def __init__(self, context, node_names, shared=False, obj_info=None,
                 purpose='unspecified action'):
        """Create a new TaskManager.

        Acquire a lock on nodes. The lock can be either shared or
        exclusive. Shared locks may be used for read-only or
        non-disruptive actions only, and must be considerate to what
        other threads may be doing on the same nodes at the same time.

        :param context: request context
        :param node_names: names of nodes to lock.
        :param shared: Boolean indicating whether to take a shared or exclusive
                       lock. Default: False.
        :param purpose: human-readable purpose to put to debug logs.
        :raises: NodeNotFound
        :raises: NodeLocked

        """
        self._spawn_method = None
        self._on_error_method = None

        self.context = context
        self._nodes = None
        self.node_names = node_names
        self.shared = shared
        self._purpose = purpose
        self._debug_timer = timeutils.StopWatch()
        self.obj_info = obj_info

        try:
            LOG.debug("Attempting to get %(type)s lock on nodes %(names)s (for"
                      " %(purpose)s)",
                      {'type': 'shared' if shared else 'exclusive',
                       'names': node_names, 'purpose': purpose})
            if not self.shared:
                self._lock()
            else:
                self._debug_timer.restart()
                self.nodes = objects.Node.list_in(context, node_names,
                                                  filters=['reservation'],
                                                  obj_info=obj_info)

        except Exception:
            with excutils.save_and_reraise_exception():
                self.release_resources()

    @property
    def nodes(self):
        return self._nodes

    @nodes.setter
    def nodes(self, nodes):
        self._nodes = nodes

    def _lock(self):
        self._debug_timer.restart()

        # NodeLocked exceptions can be annoying. Let's try to alleviate
        # some of that pain by retrying our lock attempts. The retrying
        # module expects a wait_fixed value in milliseconds.
        @retrying.retry(
            retry_on_exception=lambda e: isinstance(e, exception.NodeLocked),
            stop_max_attempt_number=CONF.conductor.node_locked_retry_attempts,
            wait_fixed=CONF.conductor.node_locked_retry_interval * 1000)
        def reserve_nodes():
            self.nodes = objects.Node.reserve_nodes(self.context, CONF.host,
                                                    self.node_names,
                                                    self.obj_info)
            LOG.debug("Node %(names)s successfully reserved for %(purpose)s "
                      "(took %(time).2f seconds)",
                      {'names': self.node_names, 'purpose': self._purpose,
                       'time': self._debug_timer.elapsed()})
            self._debug_timer.restart()

        reserve_nodes()

    def upgrade_lock(self, purpose=None):
        """Upgrade a shared lock to an exclusive lock.

        Also reloads nodes object from the database.
        If lock is already exclusive only changes the lock purpose
        when provided with one.

        :param purpose: optionally change the purpose of the lock
        :raises: NodeLocked if an exclusive lock remains on the nodes after
                            "node_locked_retry_attempts"
        """
        if purpose is not None:
            self._purpose = purpose
        if self.shared:
            LOG.debug('Upgrading shared lock on nodes %(names)s for '
                      '%(purpose)s to an exclusive one (shared lock was held '
                      '%(time).2f seconds)',
                      {'names': self.node_names, 'purpose': self._purpose,
                       'time': self._debug_timer.elapsed()})
            self._lock()
            self.shared = False

    def spawn_after(self, _spawn_method, *args, **kwargs):
        """Call this to spawn a thread to complete the task.

        The specified method will be called when the TaskManager instance
        exits.

        :param _spawn_method: a method that returns a GreenThread object
        :param args: args passed to the method.
        :param kwargs: additional kwargs passed to the method.

        """
        self._spawn_method = _spawn_method
        self._spawn_args = args
        self._spawn_kwargs = kwargs

    def set_spawn_error_hook(self, _on_error_method, *args, **kwargs):
        """Create a hook to handle exceptions when spawning a task.

        Create a hook that gets called upon an exception being raised
        from spawning a background thread to do a task.

        :param _on_error_method: a callable object, it's first parameter
            should accept the Exception object that was raised.
        :param args: additional args passed to the callable object.
        :param kwargs: additional kwargs passed to the callable object.

        """
        self._on_error_method = _on_error_method
        self._on_error_args = args
        self._on_error_kwargs = kwargs

    def release_resources(self):
        """Unlock nodes and release resources.

        If an exclusive lock is held, unlock the nodes. Reset attributes
        to make it clear that this instance of TaskManager should no
        longer be accessed.
        """

        if not self.shared:
            try:
                if self.nodes:
                    objects.Node.release_nodes(self.context, CONF.host,
                                               self.node_names)
            except exception.NodeNotFound:
                # squelch the exception if the nodes was deleted
                # within the task's context.
                pass
        if self.nodes:
            LOG.debug("Successfully released %(type)s lock for %(purpose)s "
                      "on nodes %(names)s (lock was held %(time).2f sec)",
                      {'type': 'shared' if self.shared else 'exclusive',
                       'purpose': self._purpose, 'names': self.node_names,
                       'time': self._debug_timer.elapsed()})
        self.nodes = None

    def _write_exception(self, future):
        """Set node last_error if exception raised in thread."""
        nodes = self.nodes
        # do not rewrite existing error
        for node in nodes:
            if node.last_error is None:
                method = self._spawn_args[0].__name__
                try:
                    exc = future.exception()
                except futurist.CancelledError:
                    LOG.exception(_LE("Execution of %(method)s for node "
                                      "%(node)s was canceled."),
                                  {'method': method,
                                   'node': node.name})
                else:
                    if exc is not None:
                        msg = _("Async execution of %(method)s failed with "
                                "error: %(error)s") % {'method': method,
                                                       'error': six.text_type(
                                                           exc)}
                        node.last_error = msg
                        try:
                            node.save()
                        except exception.NodeNotFound:
                            pass

    def _thread_release_resources(self, fut):
        """Thread callback to release resources."""
        try:
            self._write_exception(fut)
        finally:
            self.release_resources()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and self._spawn_method is not None:
            # Spawn a worker to complete the task
            # The linked callback below will be called whenever:
            #   - background task finished with no errors.
            #   - background task has crashed with exception.
            #   - callback was added after the background task has
            #     finished or crashed. While eventlet currently doesn't
            #     schedule the new thread until the current thread blocks
            #     for some reason, this is true.
            # All of the above are asserted in tests such that we'll
            # catch if eventlet ever changes this behavior.
            fut = None
            try:
                fut = self._spawn_method(*self._spawn_args,
                                         **self._spawn_kwargs)

                # NOTE(comstud): Trying to use a lambda here causes
                # the callback to not occur for some reason. This
                # also makes it easier to test.
                fut.add_done_callback(self._thread_release_resources)
                # Don't unlock! The unlock will occur when the
                # thread finishes.
                # NOTE(yuriyz): A race condition with process_event()
                # in callback is possible here if eventlet changes behavior.
                # E.g., if the execution of the new thread (that handles the
                # event processing) finishes before we get here, that new
                # thread may emit the "end" notification before we emit the
                # following "start" notification.
                return
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    try:
                        # Execute the on_error hook if set
                        if self._on_error_method:
                            self._on_error_method(e, *self._on_error_args,
                                                  **self._on_error_kwargs)
                    except Exception:
                        LOG.warning(_LW("Task's on_error hook failed to "
                                        "call %(method)s on nodes %(names)s"),
                                    {'method': self._on_error_method.__name__,
                                     'names': self.names})

                    if fut is not None:
                        # This means the add_done_callback() failed for some
                        # reason. Nuke the thread.
                        fut.cancel()
                    self.release_resources()
        self.release_resources()
