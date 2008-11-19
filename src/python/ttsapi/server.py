#
# server.py - Server side TTS API over text-protocol implementation
#   
# Copyright (C) 2006, 2007 Brailcom, o.p.s.
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

import traceback

class ClientGone(Exception):
    """Raised when connection with client is terminated"""

class TCPConnection(object):
    """TTS API on server side"""

    def _quit(self):
        self.logger.debug("Quitting in TCPConnection");

        # Terminate provider
        self.provider.quit()

        try:
            self.conn.close()
        except IOError:
            pass

    def __init__(self, provider, logger, method='socket', client_socket=None, memory_key=None,
                 read_semaphore_key=None, write_semaphore_key=None):
        """Init the server side object for a new connection
        
        Arguments:
        provider -- the TTS API Provider containing all
        functions defined bellow in commands_map
        client_socket -- socket for communication with client"""
        global log
        logger.debug("Going to create connection")
        self.provider = provider
        self.logger = logger
        log = logger
        if method == 'socket':
            self.conn = connection.SocketConnection(socket=client_socket,
                                                    logger=logger, side='server')
        elif method == 'pipe':
            self.conn = connection.PipeConnection(logger=logger, side='server')
        elif method == 'shm':
            self.conn = connection.SHMConnection(logger=logger, side='server',
                                                 memory_key=memory_key,
                                                 read_semaphore_key=read_semaphore_key,
                                                 write_semaphore_key=write_semaphore_key)
        else:
            raise "Unknown method of communication" + method
    
        self.logger.debug("Connection created")
    
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
            
            (('SAY', 'TEXT', ('format', str)),
             {
            'arg_data': True,
            'function': provider.say_text,
            'reply_hook':  self._say_text_reply,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),
            
            (('SAY', 'TEXT', ('format', str), 'FROM', 'POSITION',
              ('position', int), ('position_type', str)),
             {
             'arg_data': True,
            'function': provider.say_text,
            'reply_hook':  self._say_text_reply,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),
            
            (('SAY', 'TEXT', ('format', str), 'FROM', 'CHARACTER',
              ('character', int)),
             {
             'arg_data': True,
            'function': provider.say_text,
            'reply_hook':  self._say_text_reply,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),
            
            (('SAY', 'TEXT', ('format', str), 'FROM', 'INDEX MARK',
              ('index_mark', str)),
             {
             'arg_data': True,
            'function': provider.say_text,
            'reply_hook':  self._say_text_reply,
            'reply': (205, 'OK MESSAGE RECEIVED')
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
                'reply_hook':  self._say_text_reply,
                'reply': (205, 'OK MESSAGE RECEIVED')
              }),
            
            (('SAY', 'KEY', ('key', str)),
             {            
            'function': provider.say_key,
            'reply_hook':  self._say_text_reply,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),

            (('SAY', 'ICON', ('icon', str)),
             {
            'function': provider.say_icon,
            'reply_hook':  self._say_text_reply,
            'reply': (205, 'OK MESSAGE RECEIVED')
            }),
            
            (('CANCEL',),
             {
            'function': provider.cancel,
            'reply': (209, 'OK CANCELED')
            }),
            
            (('DEFER',), 
             {
            'function': provider.defer,
            'reply': (209, 'OK DEFERRED')
            }),      
            
            (('DISCARD', ('message_id', int)),
             {
            'function': provider.discard,
            'reply': (210, 'OK DISCARDED')
            }),

            (('SET', 'MESSAGE', 'ID', ('message_id', int)),
             {
            'function': provider.set_message_id,
            'reply': (211, 'OK PARAMETER SET')
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
            (ErrorDriverNotLoaded, (304, 'DRIVER NOT LOADED')),
            (ErrorRetrievalSocketNotInitialized, (305, 'RETRIEVAL SOCKET NOT INITIALIZED')),
            (ErrorDriverNotAvailable, (308, 'DRIVER NOT AVAILABLE')),
            (ErrorDriverBusy, (306, 'DRIVER BUSY')),
            (ErrorInitFailed, (307, 'INITIALIZATION FAILED')),
            (ErrorInternal, (399, 'INTERNAL ERROR')),
            (ErrorInvalidCommand, (400, 'INVALID COMMAND')),
            (ErrorInvalidArgument, (401, 'INVALID ARGUMENT')),
            (ErrorMissingArgument, (402, 'MISSING ARGUMENT')),
            (ErrorInvalidParameter, (403, 'INVALID PARAMETER')),
            (ErrorWrongEncoding, (404, 'ENCODING ERROR')),
            (DriverError, (500, 'UNKNOWN ERROR IN DRIVER'))
            )
        
    def _list_drivers_reply(self, result):
        """Reply for list of drivers"""
        reply = []
        if not isinstance(result, list):
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
    
    def _say_text_reply(self, result):
        """Reply with message id"""
        self.logger.debug("RESULT: "+str(result))
        return str(result)
    
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
        
        for i in range(0, min(len(command), len(template))):
            if isinstance (template[i], tuple):
                if command[i] != 'nil':
                    try:
                        template[i][1](command[i])
                    except:
                        raise ErrorInvalidArgument                    
            elif command[i] == template[i]:
                continue
            else:
                return False

        # TODO: This should be done better. When user specifies
        # more arguments than allowed for a valid command, he
        # will get back an InvalidCommand error.
        if len(command) < len(template):
            raise ErrorMissingArgument
        elif len(command) > len(template):
            return False
                       
        return True            

    def _report_error(self, error):
        """Report error on the connection according to self._errors_map.

        Arguments:
        error -- instance of TTSAPIError or an exception class"""
        
        if isinstance(error, TTSAPIError):
            err_code = error.code
            err_reply = error.msg
            err_detail = "Error data: " + str(error.data)
        elif error in self.errors_map:
            entry = self.errors_map[error]
            err_code = entry[0]
            err_reply = entry[1]
        else:
            for entry in self.errors_map:
                if isinstance(error, entry[0]):
                    err_code = entry[1][0]
                    err_reply = entry[1][1]
                    err_detail = error.detail()
                    break
                else:
                    self.logger.info("Unknown error received " + str(error) + " mapping to UnknownError.")
                    self.logger.info("Traceback: " + traceback.format_exc())
                    err_code = 300
                    err_reply = "UNKNOWN ERROR"
                    err_detail = None

        try:
            self.conn.send_reply(err_code, err_reply, [err_detail])
        except IOError:
            self._quit()
            
    def process_input(self):
        """Read one line of input and process it, calling the
        appropriate functions as defined in self."""
        try:
            cmd = self.conn.receive_line()
        except IOError:
            self._quit()
            raise ClientGone()

        # Check if we didn't get only data
        if cmd == None:
            return None
        
        #cmdl = [a.lower for a in cmd]

        log.debug("|"+cmd[0]+"|")
        
        if cmd[0] == 'SAY':
            if (len(cmd)>=2) and (cmd[1] == 'TEXT'):
                self.last_cmd = cmd
                self.conn.data_transfer_on()
                self.conn.send_reply(204, 'OK RECEIVING DATA')
                return
        elif cmd[0] == '.':
            # Try to switch of data mode and get the data. If we are
            # not in data mode, just continue with the invalid dot-starting
            # command, proper exception will be raised later as for other
            # invalid commands
            try:
                self.conn.data_transfer_off()
            except:
                cmd = '.'
                pass
            else:
                data = self.conn.get_data()
                # Say text with args from last_cmd and data
                #self.conn.send_reply(204, 'OK MESSAGE RECEIVED')
                cmd = self.last_cmd

        for pos in range(0, len(self.commands_map)):
            # print self.commands_map[pos]
            try:
                template, action = self.commands_map[pos]
                if self._cmd_matches(cmd, template):
                    break
            except Error, error: 
                self._report_error(error)
                return
        else:
            self._report_error(ErrorInvalidCommand())
            return

        arg_dict = {}
        for i in range(0, len(template)):
            atom = template[i]
            if isinstance(atom, tuple):
                arg_type = atom[1]
                arg_dict[atom[0]] = arg_type(cmd[i].rstrip('"').lstrip('"'))
                
        if not action.has_key('function'):
            self._report_error(ErrorInternal());
            return
        else:
            function = action['function']
    
        self.logger.debug(str(function) + str(arg_dict))
    
        if function == None:
            self.logger.warning("No associated function for this command, ignoring.");
            result = None
        else:
            try:
                if action.has_key('arg_data'):
                    result = function(text=data, **arg_dict)
                else:
                    result = function(**arg_dict)
            #TODO: Unify this
            except ClientGone:
                raise ClientGone
            except Error, err:
                if action['reply']:
                    self._report_error(err);
                return
            except TTSAPIError, err:
                self.logger.debug("TTS API ERROR with code " + str(err.code))
                if action['reply']: 
                    self._report_error(err);
                return
            
            except Exception, e:
                self.logger.info("ERROR: Can't execute function, following is the reason: " + traceback.format_exc())
                if action['reply']:
                    self.logger.debug("Reporting unknown error to client");
                    self._report_error(UnknownError)
                return

        if action.has_key('function_post_hook'):
            action['function_post_hook']()  
            
        if action.has_key('reply_hook'):
            result = action['reply_hook'](result)
        
        reply = action['reply']
            
        if reply != None:
            if (not isinstance(result, list)) and (not result == None):
                result = [result]
            self.conn.send_reply(reply[0], reply[1], result)
        
    def send_audio_event(self, event):
        """Send audio event on the connection.
        WARNING: This is intended to be called asynchronously,
        so the communication must be protected with mutexes."""

        code, event_line = tcp_format_event(event)
        try:
            self.conn.send_reply(code, "EVENT", [event_line,])
        except:
            self._quit()

    def close(self):
        self._quit()

def tcp_format_event(event):
        """Format event line according to text protocol specifications"""
        if event.pos_audio != None:
            pos_audio = int(event.pos_audio)
        else:
            pos_audio = None
        if event.type in ('message_start', 'message_end'):
            event_line = event.type + " " + str(event.message_id) \
                         +  " " + str(event.pos_text) + " " \
                       + str(pos_audio)
            code = 701
        elif event.type in ('word_start', 'word_end',
                            'sentence_start', 'sentence_end'):
            event_line = event.type + " " + str(event.message_id) \
                       + " " +str(event.n) + " " \
                       + str(event.pos_text)  + " " \
                       + str(pos_audio)
            code = 702
        elif event.type == 'index_mark':
            event_line = event.type + " " + str(event.message_id) \
                       + ' "' + event.name + '" ' \
                       + str(event.pos_text)  + " " \
                       + str(pos_audio)
            code = 703
        else:
            raise NotImplementedError

        return (code, event_line)
