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
# the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
# 
# $Id: ttsapi.py,v 1.3 2006/07/03 20:56:57 hanke Exp

import connection
from structures import *

class TCPConnection(object):
    """TTS API on server side"""

    def __init__(self, provider, client_socket):
        """Init the server side object for a new connection
        
        Arguments:
        provider -- the TTS API Provider containing all
        functions defined bellow in commands_map
        client_socket -- socket for communication with client"""

        self.conn = connection.SocketConnection(socket=client_socket)
        
        self.commands_map = [
            (('LIST', 'DRIVERS'),
             {
            'function' : provider.drivers
            }),

            (('DRIVER', 'CAPABILITIES', ('driver_id', str)),
             {
            'function': provider.driver_capabilities,
            'reply_hook': self._driver_capabilities_reply,
            'reply': (201, 'OK LIST OF DRIVERS SENT')
            }),

            (('LIST', 'VOICES', ('driver_id', str)),
             {
            'function_id': provider.voices,
            'reply': (203,'OK LIST OF VOICES SENT')
            }),
            
            (('SAY', 'DEFERRED', ('message_id', int)),
             {
            'function_id': provider.say_deferred,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),
            
            (('SAY', 'DEFERRED', ('message_id', int), 'FROM', 'POSITION',
              ('position', int), ('position_type', str)),
             {
            'function_id': provider.say_deferred,
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
            
            (('HELP'),
             {
            'function': None
            }),
            
            (('QUIT'),
             {
            'function': None
            })         
            ]
        self.provider = provider

    def _driver_capabilities_reply(self, result):

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

     
    def process_input(self):
        cmd = self.conn.receive_line()
        # Check if we didn't get only data
        if cmd == None:
            return None
        
        cmdl = [a.lower for a in cmd]
        
        if cmdl[0] == 'say':
            if cmdl[1] == 'text':
                self.last_cmd = cmd
                self.conn.data_transfer_on()
                self.conn.send_reply('204 OK RECEIVING DATA')
                return
        elif cmdl[0] == '.':
            self.conn.data_transfer_off()
            data = self.get_data()
            # Say text with args from last_cmd and data
            self.conn.send_reply('204 OK MESSAGE RECEIVED')

        for pos in range(0, len(self.commands_map)):
            template, action = self.commands_map[pos]
            if self._cmd_matches(cmd, template):
                break;
        else:
            # Raise exception
            print "ERROR, Unknown command"

        arg_dict = {}
        for i in range(0, len(template)):
            atom = template[i]
            if isinstance(atom, tuple):
                arg_type = atom[1]
                arg_dict[atom[0]] = arg_type(cmd[i])

        if not action.has_key('function'):
            raise NotImplementedError
        else:
            function = action['function']

        if function == None:
            self.conn.send_reply(301, "ERR UNKNOWN COMMAND")
        else:
            # TODO: try (exception handling)
            print arg_dict
            result = action['function'](self.provider, **arg_dict)
            # catch and print error reply on socket

        if action.has_key('reply_hook'):
            result = action['reply_hook'](result)
        else:
            reply = action['reply']
            if (not isinstance(result, list)) and (not result == None):
                result = [result]
        self.conn.send_reply(reply[0], reply[1], result)
        



         
    
