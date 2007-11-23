# configuration.py - Configuration for TTS API Provider
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
# $Id: configuration.py,v 1.8 2007-11-23 09:20:59 hanke Exp $

import logging
import os
from optparse import OptionParser

MyDebug = True

class Configuration(object):
    """Configuration for TTS API"""

    _conf_options = \
        {
        'mode':
            {
                'descr' : "Mode of execution: single od daemon",
                'doc' : None,
                'type' : str,
                'default' : 'daemon',
                'command_line' : ('-m', '--mode')
            },
        'pidpath':
            {
                'descr' : "Path to the pid file",
                'doc' : None,
                'type' : str,
                'default' : '/var/run/tts-api-provider/',
                'command_line' : ('', '--pidpath')
            },
        'pidfile':
            {
                'descr' : "Name of pidfile inside pidpath",
                'doc' : None,
                'type' : str,
                'default' : 'tts-api-provider.pid',
                'command_line' : ('', '--pidfile')
            },
        'port' :  
            {
                'descr' : "Port for the server",
                'doc' : None,
                'type' : int,
                'default' : 6567, 
                'check' : lambda x: x>0,
                'command_line' : ('-p', '--port')
            },
        'max_simultaneous_connections':
            {
                'descr' : "Maximum number of simultaneous connections",
                'doc' : """Sets the maximum number of connections that can be accepted
                by the server in the situation that it is impossible to create new provider
                threads to serve them on time. Do not change until you know what you are
                doing.""",
                'type' : int,
                'default' : 5,
                'check' : lambda x: x>0
            },
        'log_dir':
            {
                'descr' : "Directory to store logfiles",
                'type' : str,
                'default' : "/var/log/tts-api-provider/",
                'command_line' : ('-L', '--log-dir')
            },
         'log_name':
            {
                'descr' : "Name of the main log file in log_dir",
                'type' : str,
                'default' : "provider.log",
                'command_line' : ('--log-name',)
            },
        'log_on_stdout':
            {
                'descr' : "Logging information on standard output",
                'doc' :  """If 'True', logging information are written to standard
                error output. If 'False', they are only written to the appropriate log file.""",
                'type' : bool,
                'command_line' : ('--log-on-stdout',),
                'default' : False
            },
         'log_format':
            {
                'descr' : "Format of log entries",
                'doc' : """See the Python logging package for more details""",
                'type' : str,
                'default' : "%(asctime)s %(threadName)s %(levelname)s %(message)s"
            },
        'log_level':
            {
                'descr' : "Logging level",
                'type' : int,
                'command_line': ('-l', '--log-level'),
                'default' : logging.DEBUG,
                'arg_map' : (str, {
                    'critical' : logging.CRITICAL,
                    'error':logging.ERROR,
                    'warning':logging.WARNING,
                    'info':logging.INFO,
                    'debug':logging.DEBUG
                })
            },
        'audio_host' :  
            {
                'descr' : "Audio host (sink) for the server",
                'doc' : None,
                'type' : str,
                'default' : "127.0.0.1",
                'command_line' : ("", '--audio-host')
            },
        'audio_port' :  
            {
                'descr' : "Audio port (sink) for the server",
                'doc' : None,
                'type' : int,
                'default' : 6576, 
                'check' : lambda x: x>0,
                'command_line' : ('-a', '--audio-port')
            },
        'available_drivers':
            {
                'descr': "List of driver names and their executables",
                'doc': None,
                'type': object,
                'default': [('espeak',
                             os.path.join (os.path.dirname (__file__), 'drivers/c/espeak'),                          
                             ),
                            ('festival',
                             os.path.join (os.path.dirname (__file__), 'drivers/festival.py'),                             
                             ),
                            ('sd_espeak',
                             os.path.join (os.path.dirname (__file__), 'drivers/sd_module.py'),
                             ["Espeak",
                              "/usr/lib/speech-dispatcher-modules/sd_espeak",
                              "/etc/speech-dispatcher/modules/espeak.conf"]
                             ),
                            ('sd_festival',
                             os.path.join (os.path.dirname (__file__), 'drivers/sd_module.py'),
                             ["Festival",
                              "/usr/lib/speech-dispatcher-modules/sd_festival",
                              "/etc/speech-dispatcher/modules/festival.conf"]
                             ),
                            ('sd_flite',
                             os.path.join (os.path.dirname (__file__), 'drivers/sd_module.py'),
                             ["Flite",
                              "/usr/lib/speech-dispatcher-modules/sd_flite",
                              "/etc/speech-dispatcher/modules/flite.conf"]
                             )
                            ]
            },
        'default_driver':
            {
                'descr': "Default driver",
                'doc': "Name of the default driver as specified in 'available_drivers'",
                'type':str,
                'default': "festival"
            }
        }
    
    def __init__(self, logger):
        global log
        log = logger
        self.cmdline_parser = OptionParser()
    
        for option, definition in self._conf_options.iteritems():
            # Set object attributes to default values
            def_val = definition.get('default', None)
            setattr(self, option, def_val)
            log.debug("Option %s set to value %s", option, def_val)
            
            # Fill in the cmdline_parser object
            if definition.has_key('command_line'):
                descr = definition.get('descr', None)                
                type = definition.get('type', None)
                
                if definition.has_key('arg_map'):
                    type, map = definition['arg_map']
                if type == str:
                    type_str = 'string'
                elif type == int:
                    type_str = 'int'
                elif type == float:
                    type_str = 'float'
                elif type == bool:
                    type_str = None
                else:
                    raise "Unknown type"
                
                if 'type' != bool:
                    self.cmdline_parser.add_option(type=type_str, dest=option, help=descr,
                                                                    *definition['command_line'])
                else: # type == bool
                    self.cmdline_parser.add_option(action="store_true", help=descr,
                                                                    *definition['command_line'])
            
        # Set options according to command line flags
        (cmdline_options, args) = self.cmdline_parser.parse_args()

        for option, definition in self._conf_options.iteritems():
                val = getattr(cmdline_options, option, None)
                if val != None:
                    if definition.has_key('arg_map'):
                        former_type, map = definition['arg_map']
                        try:
                            val = map[val]
                        except KeyError:
                            raise "Invalid option value: "  + str(val)
                        
                    setattr(self, option, val)
                    log.debug("Option %s overriden from command line to value %s", option, val)
        
        #if len(args) != 0:
           # raise "This command takes no positional arguments (without - or -- prefix)"

        self.log_path = os.path.join(self.log_dir, self.log_name)
