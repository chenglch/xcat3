import os

os.environ['EVENTLET_NO_GREENDNS'] = 'yes'

import eventlet

eventlet.monkey_patch(os=False)