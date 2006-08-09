#
# server.py - Server side TTS API over text-protocol implementation
#   
# Copyright (C) 2006 Brailcom, o.p.s.
# 
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this package; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA 02110-1301, USA.
# 
# $Id: ttsapi.py,v 1.3 2006/07/03 20:56:57 hanke Exp

import connection
from structures import *
from errors import *

class ClientGone(Exception):
    """Raised when connection with client is terminated"""

class TCPConnection(object):
    """TTS API on server side"""

    def _quit(self):
            #TODO: self.provider.quit()
            self.conn.close()
            raise ClientGone()

    def __init__(self, provider, client_socket, logger):
        """Init the server side object for a new connection
        
        Arguments:
        provider -- the TTS API Provider containing all
        functions defined bellow in commands_map
        client_socket -- socket for communication with client"""

        self.provider = provider
        self.conn = connection.SocketConnection(socket=client_socket, logger=logger)
        self.logger = logger
    
        self.commands_map = [
            (('LIST', 'DRIVERS'),
             {
            'function'  :  provider.drivers,
            'reply' :  (201, 'OK LIST OF DRIVERS SENT')
            }),

            (('DRIVER', 'CAPABILITIES', ('driver_id', str)),
             {
            'function': provider.driver_capabilities,
            'reply_hook': self._driver_capabilities_reply,
            'reply': (201, 'OK LIST OF DRIVERS SENT')
            }),

            (('LIST', 'VOICES', ('driver_id', str)),
             {
            'function': provider.voices,
            'reply': (203,'OK LIST OF VOICES SENT')
            }),
            
            (('SAY', 'DEFERRED', ('message_id', int)),
             {
            'function': provider.say_deferred,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),
            
            (('SAY', 'DEFERRED', ('message_id', int), 'FROM', 'POSITION',
              ('position', int), ('position_type', str)),
             {
            'function': provider.say_deferred,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),
            
            (('SAY', 'DEFERRED', ('message_id', int), 'FROM', 'CHARACTER',
              ('character', int)),
             {
            'function': provider.say_deferred,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),
            
            (('SAY', 'DEFERRED', ('message_id', int), 'FROM', 'INDEX MARK',
              ('index_mark', str)),
             {
            'function': provider.say_deferred
            }),

            (('SAY', 'CHAR', ('character', str)),
             {'function': provider.say_char
              }),
            
            (('SAY', 'KEY', ('key', str)),
             {            
            'function': provider.say_key
            }),

            (('SAY', 'ICON', ('icon', str)),
             {
            'function': provider.say_icon
            }),
            
            (('CANCEL'),
             {
            'function': provider.cancel
            }),
            
            (('DEFER'), 
             {
            'function': provider.defer
            }),      
            
            (('DISCARD', ('message_id', int)),
             {
            'function': provider.discard
            }),

            (('SET', 'DRIVER', ('driver_id', str)),
             {
            'function': provider.set_driver
            }),
            
            (('SET', 'VOICE', 'BY', 'NAME', ('voice_name', str)),
             {
            'function': provider.set_voice_by_name
            }),

            (('SET', 'VOICE', 'BY', 'PROPERTIES', ('language', str),
              ('dialect', str), ('gender', str), ('age', int), ('variant', int)),
             {
            'function': provider.set_voice_by_properties
            }),
            
            (('GET', 'CURRENT', 'VOICE'),
             {
            'function': provider.current_voice
            }),
            
            (('SET', ('method', str), 'RATE', ('rate', int)),
             {
            'function': provider.set_rate
            }),

            (('GET', 'DEFAULT', 'ABSOLUTE', 'RATE'),
             {
            'function': provider.default_absolute_rate
            }),
            
            (('SET', ('method', str), 'PITCH', ('pitch', int)),
             {
            'function': provider.set_pitch
            }),
            
            (('GET', 'DEFAULT', 'ABSOLUTE', 'PITCH'),
             {
            'function': provider.default_absolute_pitch
            }),
            
            (('SET', ('method', str), 'PITCH_RANGE', ('range', int)),
             {
            'function': provider.set_pitch_range
            }),

            (('SET', ('method', str), 'VOLUME', ('volume', int)),
             {
            'function': provider.set_volume
            }),

            (('GET', 'DEFAULT', 'ABSOLUTE', 'VOLUME'),
             {
            'function': provider.default_absolute_volume
            }),

            (('SET', 'PUNCTUATION', 'MODE', ('mode', str)),
             {
            'function': provider.set_punctuation_mode
            }),

            (('SET', 'PUNCTUATION', 'DETAIL', ('detail', str)),
             {
            'function': provider.set_punctuation_detail
            }),

            (('SET', 'CAPITAL', 'LETTERS', 'MODE', ('mode', str)),
             {
            'function': provider.set_capital_letters_mode
            }),

            (('SET', 'NUMBER', 'GROUPING', ('grouping', int)),
             {
            'function': provider.set_number_grouping
            }),
            
            (('SET', 'AUDIO', 'OUTPUT', ('method',  str)),
             {
            'function': provider.set_audio_output
            }),
            
            (('SET', 'AUDIO', 'RETRIEVAL', ('host', str), ('port', int)),
             {
            'function': provider.set_audio_retrieval_destination
            }),
            
            (('HELP',),
             {
            'function': None
            }),
            (('QUIT',),
             {
            'function':  self._quit,
            'reply': None
            }) 
            ]
        
        self.errors_map = (
            (UnknownError, (300, 'UNKNOWN ERROR')),
            (ErrorNotSupportedByDriver, (301, 'NOT SUPPORTED BY DRIVER')),
            (ErrorNotSupportedByServer, (302, 'NOT SUPPORTED BY SERVER')),
            (ErrorAccessToDriverDenied, (303, 'DRIVER ACCESS DENIED')),
            (ErrorInternal, (304, 'INTERNAL ERROR')),
            (ErrorInvalidCommand, (400, 'INVALID COMMAND')),
            (ErrorInvalidArgument, (401, 'INVALID ARGUMENT')),
            (ErrorMissingArgument, (402, 'MISSING ARGUMENT')),
            (ErrorInvalidParameter, (403, 'INVALID PARAMETER')),
            (ErrorWrongEncoding, (404, 'ENCODING ERROR'))
            )
        
    def _driver_capabilities_reply(self, result):
        """Driver capabilities reply hook"""

        capabilities = result.attributes_dict()

        reply = []
        for key, value in capabilities.iteritems():
            if isinstance(value, list):
                reply += [key] + value
            elif isinstance(value, bool):
                reply += [key, value.lower()]
            else:
                reply += [key, str(value)]
        return reply
        
    def _cmd_matches(self, command, template):
        """Compare command and template, return
        True if they match, otherwise False""" 
        
        if len(command) != len(template):
            return False
        
        for i in range(0, len(command)):
            if isinstance (template[i], tuple):                
                # Check if the parameter is of correct type
                continue
            elif command[i] == template[i]:
                continue
            else:
                return False
                       
        return True            

    def _report_error(self, error):
        """Report error on the connection according to
        self.errors_map"""
        for entry in self.errors_map:
            if isinstance(error, entry[0]):
                err_code = entry[1][0]
                err_reply = entry[1][1]
                err_detail = error.detail()
                break
        else:
            err_code = 300
            err_reply = "UNKNOWN ERROR"
            err_detail = None

        self.conn.send_reply(err_code, err_reply, err_detail)
            
    def process_input(self):
        """Read one line of input and process it, calling the
        appropriate functions as defined in self."""
        cmd = self.conn.receive_line()
        # Check if we didn't get only data
        if cmd == None:
            return None
        
        cmdl = [a.lower for a in cmd]
        
        if cmdl[0] == 'say':
            if cmdl[1] == 'text':
                self.last_cmd = cmd
                self.conn.data_transfer_on()
                self.conn.send_reply(204, 'OK RECEIVING DATA')
                return
        elif cmdl[0] == '.':
            self.conn.data_transfer_off()
            data = self.get_data()
            # Say text with args from last_cmd and data
            self.conn.send_reply('204 OK MESSAGE RECEIVED')

        for pos in range(0, len(self.commands_map)):
            # print self.commands_map[pos]
            template, action = self.commands_map[pos]
            if self._cmd_matches(cmd, template):
                break
        else:
            self._report_error(ErrorInvalidCommand())
            return

        arg_dict = {}
        for i in range(0, len(template)):
            atom = template[i]
            if isinstance(atom, tuple):
                arg_type = atom[1]
                arg_dict[atom[0]] = arg_type(cmd[i])

        if not action.has_key('function'):
            self._report_error(ErrorInternal());
        else:
            function = action['function']

        if function == None:
            pass
        else:
            try:
                result = function(**arg_dict)
            except Error, err:
                self._report_error(err);
                return
    
        if action.has_key('function_post_hook'):
            action['function_post_hook']()  
            
        if action.has_key('reply_hook'):
            result = action['reply_hook'](result)
        else:
            reply = action['reply']
            if reply != None:
                if (not isinstance(result, list)) and (not result == None):
                    result = [result]
                self.conn.send_reply(reply[0], reply[1], result)
