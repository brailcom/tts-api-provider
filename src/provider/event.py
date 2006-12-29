
import threading
from copy import copy

#TODO: Rewrite. Separate the event structure from the data carried.

class Event(object):
    """Class for passing events between the Core and the Controller thread."""
    
    attributes = {
        'type': ("Type of the event",
            ("say_text", "say_deferred", "say_char","say_key", "say_icon",
             "cancel", "defer", "discard")),
        'text': ("Text of message",  ("say_text","say_key", "say_char", "say_icon")),
        'format': ("Format of the message (event say_text)", ("say_text",)),
        'position': ("Position in text", ("say_text", "say_deferred")),
        'position_type': ("Type of position", ("say_text", "say_deferred")),
        'index_mark': ("Index mark position", ("say_text", "say_deferred")),
        'character': ("Character position", ("say_text", "say_deferred")),
        'message_id': ("ID of the message", ("say_text", "say_deferred", "say_char",
                                             "say_key", "say_icon", "cancel", "defer",
                                             "discard"))
    }
    
    def __init__(self):
        """Init the event, create locks etc."""
        self.lock = threading.Lock()
        self.clear()
    
    def safe_read(self):
        """Get the current value of the event"""
        self.lock.acquire()
        ret = copy(self)
        self.lock.release()
        return ret
        
    def clear(self):
        """Clear all information about the event"""
        for a in self.attributes:
            setattr(self, a[0], None)
    
    def set(self, **args):
        """Set a value of the event"""
        self.lock.acquire()
        self.clear()
        if not args.has_key('type'):
            raise UnknownError
        type_arg = args['type']
        for name, value in args.iteritems():
            if not self.attributes.has_key(name):
                raise "Invalid attribute"
            if type_arg not in self.attributes[name][1]:
                raise "The "+name+" argument is not allowed for this message type "+str(type_arg)+" or invalid message type, " + str(self.attributes[name][1])
            setattr(self, name, value)
        self.lock.release()
