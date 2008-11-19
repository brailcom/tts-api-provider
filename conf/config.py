
import configuration
import logging
import os

class UserConfiguration(configuration.Configuration):
    """Configuration for TTS API"""

    _conf_options = \
        {
        'mode':
            {
                'descr' : "Mode of execution: single or daemon",
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
        'timestamp_priority':
            {
                'descr': "Logging priority for TIMESTAMP messages",
                'type': int,
                'default': logging.DEBUG-1,
                #'default': logging.ERROR+1,  //Use this and log_level=ERROR for performance testing
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
                'default': [{'driver': 'espeak',
                             'executable': os.path.join (os.path.dirname (__file__), 'drivers/c/espeak'),
                             'communication': 'pipe'
                             },
                            {'driver': 'festival',
                             'executable': os.path.join (os.path.dirname (__file__), 'drivers/festival.py'),
                             'communication': 'shm'
                             },
                            #{'driver': 'sd_espeak',
                            # 'executable': os.path.join (os.path.dirname (__file__), 'drivers/sd_module.py'),
                            # 'communication': 'shm',
                            # 'args': ["Espeak",
                            #  "/usr/lib/speech-dispatcher-modules/sd_espeak",
                            #  "/etc/speech-dispatcher/modules/espeak.conf"]
                            # },
                          #  {'driver': 'sd_festival',
                          #   'executable': os.path.join (os.path.dirname (__file__), 'drivers/sd_module.py'),
                          #   'args': ["Festival",
                          #    "/usr/lib/speech-dispatcher-modules/sd_festival",
                          #    "/etc/speech-dispatcher/modules/festival.conf"]
                          #   },
                          #  {'driver': 'sd_flite',
                          #   'executable': os.path.join (os.path.dirname (__file__), 'drivers/sd_module.py'),
                          #   'args': ["Flite",
                          #    "/usr/lib/speech-dispatcher-modules/sd_flite",
                          #    "/etc/speech-dispatcher/modules/flite.conf"]
                          #   }
                            ]
            },
        'default_driver':
            {
                'descr': "Default driver",
                'doc': "Name of the default driver as specified in 'available_drivers'",
                'type':str,
                'default': "espeak"
            }
        }

