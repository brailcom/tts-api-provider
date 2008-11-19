
import threading
from copy import copy

class EventQueue(object):

    def __init__(self):
        self._data_lock = threading.Lock()
        self._events = []
        self._sem = threading.Semaphore(0)

    def push(self, event):
        self._data_lock.acquire()
        self._events.insert(0, event)
        self._data_lock.release()

        self._sem.release()
        
    def pop(self):
        self._sem.acquire()

        self._data_lock.acquire()
        event = self._events.pop()
        self._data_lock.release()

        return event

class EventPot(object):

    def __init__(self):
        self._data_lock = threading.Lock()
        self._events = []
        self._t_event = threading.Event()
        self._t_event.clear()

    def push(self, event):
        self._data_lock.acquire()
        self._events.insert(0, event)
        self._data_lock.release()

        self._t_event.set()

    def pop(self):
        self._t_event.wait()
        self._t_event.clear()

        self._data_lock.acquire()
        event = self._events.pop()
        self._data_lock.release()

        return event

class Event(object):

    _attributes = {}
        
    def __init__(self, **args):
        if not args.has_key('type'):
            raise "No 'type' key"
        type_arg = args['type']
        for name, value in args.iteritems():
            if not self._attributes.has_key(name):
                raise "Invalid attribute"
            if type_arg not in self._attributes[name][1]:
                raise "The "+name+" argument is not allowed for this message type " \
                      +str(type_arg)+" or invalid message type, " \
                      + str(self._attributes[name][1])
            setattr(self, name, value)
