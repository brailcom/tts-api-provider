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

    def __init__(self, provider, logger, method='socket', client_socket=None):
        """Init the server side object for a new connection
        
        Arguments:
        provider -- the TTS API Provider containing all
        functions defined bellow in commands_map
        client_socket -- socket for communication with client"""

        self.provider = provider
        self.logger = logger
        if method == 'socket':
            self.conn = connection.SocketConnection(socket=client_socket,
                                                    logger=logger)
        elif method == 'pipe':
            self.conn = connection.PipeConnection(logger=logger)
        else:
            raise "Unknown method of communication" + method
    
        self.commands_map = [
            (('INIT',),
             {
            'function' : provider.init,
            'reply' : (200, 'OK INITIALIZED SUCCESFULLY')
            }),
            (('LIST', 'DRIVERS'),
             {
            'function'  :  provider.drivers,
            'reply_hook':  self._list_drivers_reply,
            'reply' :  (201, 'OK LIST OF DRIVERS SENT')
            }),

            (('DRIVER', 'CAPABILITIES'),
             {
            'function': provider.driver_capabilities,
            'reply_hook': self._driver_capabilities_reply,
            'reply': (201, 'OK LIST OF DRIVERS SENT')
            }),

            (('LIST', 'VOICES'),
             {
            'function': provider.voices,
            'reply_hook':  self._list_voices_reply,
            'reply': (203,'OK LIST OF VOICES SENT')
            }),
            
            (('SAY', 'TEXT'),
             {
            'arg_data': True,
            'function': provider.say_text,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),
            
            (('SAY', 'TEXT', 'FROM', 'POSITION',
              ('position', int), ('position_type', str)),
             {
             'arg_data': True,
            'function': provider.say_text,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),
            
            (('SAY', 'TEXT', 'FROM', 'CHARACTER',
              ('character', int)),
             {
             'arg_data': True,
            'function': provider.say_text,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),
            
            (('SAY', 'TEXT', 'FROM', 'INDEX MARK',
              ('index_mark', str)),
             {
             'arg_data': True,
            'function': provider.say_text
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
             {'function': provider.say_char,
                'reply': (205, 'OK MESSAGE RECEIVED')
              }),
            
            (('SAY', 'KEY', ('key', str)),
             {            
            'function': provider.say_key,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),

            (('SAY', 'ICON', ('icon', str)),
             {
            'function': provider.say_icon,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),
            
            (('CANCEL'),
             {
            'function': provider.cancel,
            'reply': (209, 'OK CANCELED')
            }),
            
            (('DEFER'), 
             {
            'function': provider.defer,
            'reply': (209, 'OK DEFERRED')
            }),      
            
            (('DISCARD', ('message_id', int)),
             {
            'function': provider.discard,
            'reply': (210, 'OK DISCARDED')
            }),

            (('SET', 'DRIVER', ('driver_id', str)),
             {
            'function': provider.set_driver,
            'reply': (211, 'OK PARAMETER SET')
            }),
            
            (('SET', 'VOICE', 'BY', 'NAME', ('voice_name', str)),
             {
            'function': provider.set_voice_by_name,
            'reply': (211, 'OK PARAMETER SET')
            }),

            (('SET', 'VOICE', 'BY', 'PROPERTIES', ('language', str),
              ('dialect', str), ('gender', str), ('age', int), ('variant', int)),
             {
            'function': provider.set_voice_by_properties,
            'reply': (211, 'OK PARAMETER SET')
            }),
            
            (('GET', 'CURRENT', 'VOICE'),
             {
            'function': provider.current_voice
            }),
            
            (('SET', ('method', str), 'RATE', ('rate', int)),
             {
            'function': provider.set_rate,
            'reply': (211, 'OK PARAMETER SET')
            }),

            (('GET', 'DEFAULT', 'ABSOLUTE', 'RATE'),
             {
            'function': provider.default_absolute_rate
            }),
            
            (('SET', ('method', str), 'PITCH', ('pitch', int)),
             {
            'function': provider.set_pitch,
            'reply': (211, 'OK PARAMETER SET')
            }),
            
            (('GET', 'DEFAULT', 'ABSOLUTE', 'PITCH'),
             {
            'function': provider.default_absolute_pitch
            }),
            
            (('SET', ('method', str), 'PITCH_RANGE', ('range', int)),
             {
            'function': provider.set_pitch_range,
            'reply': (211, 'OK PARAMETER SET')
            }),

            (('SET', ('method', str), 'VOLUME', ('volume', int)),
             {
            'function': provider.set_volume,
            'reply': (211, 'OK PARAMETER SET')
            }),

            (('GET', 'DEFAULT', 'ABSOLUTE', 'VOLUME'),
             {
            'function': provider.default_absolute_volume
            }),

            (('SET', 'PUNCTUATION', 'MODE', ('mode', str)),
             {
            'function': provider.set_punctuation_mode,
            'reply': (211, 'OK PARAMETER SET')
            }),

            (('SET', 'PUNCTUATION', 'DETAIL', ('detail', str)),
             {
            'function': provider.set_punctuation_detail,
            'reply': (211, 'OK PARAMETER SET')
            }),

            (('SET', 'CAPITAL', 'LETTERS', 'MODE', ('mode', str)),
             {
            'function': provider.set_capital_letters_mode,
            'reply': (211, 'OK PARAMETER SET')
            }),

            (('SET', 'NUMBER', 'GROUPING', ('grouping', int)),
             {
            'function': provider.set_number_grouping,
            'reply': (211, 'OK PARAMETER SET')
            }),
            
            (('SET', 'AUDIO', 'OUTPUT', ('method',  str)),
             {
            'function': provider.set_audio_output,
            'reply': (211, 'OK PARAMETER SET')
            }),
            
            (('SET', 'AUDIO', 'RETRIEVAL', ('host', str), ('port', int)),
             {
            'function': provider.set_audio_retrieval_destination,
            'reply': (211, 'OK PARAMETER SET')
            }),
            
            (('HELP',),
             {
            'function': None,
             'reply': (800, 'HELP SENT')
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
        
    def _list_drivers_reply(self, result):
        """Reply for list of drivers"""
        reply = []
        if result is not list:
            result = [result]
        
        for driver in result:
            reply += [[driver.driver_id, driver.synthesizer_name, driver.driver_version,
            driver.synthesizer_version]]
        return reply
        
    def _list_voices_reply(self, result):
        """Reply for list of voices"""
        reply = []
        if not isinstance(result, list):
            result = [result]
        for voice in result:
            reply += [[voice.name, voice.language, voice.dialect, voice.gender, voice.age]]
        return reply
        
    def _driver_capabilities_reply(self, result):
        """Driver capabilities reply hook"""
        capabilities = result.attributes_dictionary()

        reply = []
        for key, value in capabilities.iteritems():
            if isinstance(value, list):
                if value == []:
                    reply += [[key] + ["nil"]]
                else:
                    reply += [[key] + value]
            elif isinstance(value, bool):
                reply += [[key, str(value).lower()]]
            else:
                reply += [[key, str(value)]]
        reply.sort() # just that it is more beautiful when inspected manually
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
        
        #cmdl = [a.lower for a in cmd]
        
        print cmd
        if cmd[0] == 'SAY':
            if cmd[1] == 'TEXT':
                self.last_cmd = cmd
                self.conn.data_transfer_on()
                self.conn.send_reply(204, 'OK RECEIVING DATA')
                return
        elif cmd[0] == '.':
            self.conn.data_transfer_off()
            data = self.conn.get_data()
            # Say text with args from last_cmd and data
            self.conn.send_reply(204, 'OK MESSAGE RECEIVED')
            cmd = self.last_cmd

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
                if action.has_key('arg_data'):
                    result = function(text=data, **arg_dict)
                else:
                    result = function(**arg_dict)
            except Error, err:
                self._report_error(err);
                return;
    
        if action.has_key('function_post_hook'):
            action['function_post_hook']()  
            
        if action.has_key('reply_hook'):
            result = action['reply_hook'](result)
        
        reply = action['reply']
            
        if reply != None:
            if (not isinstance(result, list)) and (not result == None):
                result = [result]
            self.conn.send_reply(reply[0], reply[1], result)
