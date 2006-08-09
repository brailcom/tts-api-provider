# configuration.py - Configuration for TTS API Provider
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
# $Id: configuration.py,v 1.1 2006-08-09 12:06:24 hanke Exp $

import logging
from logs import log
from optparse import OptionParser

MyDebug = True

class Configuration(object):
    """Configuration for TTS API"""

    _conf_options = \
        {
        'port' :  
            {
                'descr' : "Port for the server",
                'doc' : None,
                'type' : int,
                'default' : 6562, 
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
                'default' : "%(asctime)s %(levelname)s %(message)s"
            },
        'log_level':
            {
                'descr' : "Logging level",
                'type' : int,
                'command_line': ('-l', '--log-level'),
                'default' : logging.INFO,
                'arg_map' : (str, {
                    'critical' : logging.CRITICAL,
                    'error':logging.ERROR,
                    'warning':logging.WARNING,
                    'info':logging.INFO,
                    'debug':logging.DEBUG
                })
            }
        }
    
    def __init__(self):
    
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
        
        if len(args) != 0:
            raise "This command takes no positional arguments (without - or -- prefix)"

        self.log_path = self.log_dir + self.log_name

# Create the conf object
conf = Configuration()
