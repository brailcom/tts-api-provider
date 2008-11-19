
import ttsapi
import time
import logging
import sys
import optparse
import string

log = None

def init_logging():
    "Initialize logging"
    global log

    log = logging.Logger('Test', level=logging.DEBUG)
    stdout_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s %(message)s")
    stdout_handler.setFormatter(formatter)
    log.addHandler(stdout_handler)

options_definition = {
    'host' : {'short': 'H',
              'long': 'host',
              'help': "Server host",
              'type': "string"},
    'port' : {'short': 'P',
              'long': 'port',
              'help': "Server port",
              'type': "int"},
    'absolute_rate' : {'short': None,
                       'long': 'rate',
                       'help': "Speech rate (absolute)",
                       'type': 'int'},
    'relative_rate' : {'short': 'r',
                       'long': 'relative-rate',
                       'help': "Speech rate (relative)",
                       'type': 'int'},
    'absolute_pitch' : {'short': None,
                        'long': 'pitch',
                        'help': "Speech pitch (absolute)",
                        'type': 'int'},
    'relative_pitch' : {'short': 'p',
                        'long': 'relative-pitch',
                        'help': "Speech pitch (relative)",
                        'type': 'int'},
    'volume' : {'short': 'v',
                'long': 'volume',
                'help': "Speech volume",
                'type': 'int'},
    'driver' : {'short': 'o',
                'long': 'driver',
                'help': 'Driver to use',
                'type': 'string'},
    'punctuation_mode' : {'short': None,
                          'long': 'punctuation-mode',
                          'help': "Punctuation mode",
                          'type': 'string'},
    'list_voices' : {'short': None,
                     'long': 'list-voices',
                     'help': "List available voices",
                     'action': 'store_true'},
    }

options = None

def parse_args():

    global options
    parser = optparse.OptionParser()

    for key, opt in options_definition.items():
        if opt['short'] and opt['long']:
            parser.add_option("-" + opt['short'],
                              "--" + opt['long'],
                              dest=key, help=opt['help'])
        elif opt['long']:
            parser.add_option("--" + opt['long'],
                              dest=key, help=opt['help'])
    
    # Set options according to command line flags
    (options, args) = parser.parse_args()

    return (options, args)

def set_options(conn, options):

    # Set voice attributes
    if options.absolute_rate:
        conn.set_rate(int(options.absolute_rate), method='absolute')
    if options.relative_rate:
        conn.set_rate(int(options.relative_rate), method='relative')
    if options.absolute_pitch:
        conn.set_pitch(int(options.absolute_pitch), method='absolute')
    if options.relative_pitch:
        conn.set_pitch(int(options.relative_pitch), method='relative')
    if options.driver:
        conn.set_driver(options.driver)

init_logging()
log.debug("Parsing arguments")
options, args = parse_args()

if len(args) == 0:
    log.error("Missing arguments (no text to speak), try '--help'")
    sys.exit(1)

log.debug("Initializing connection")
speech_client = ttsapi.client.TCPConnection()

log.debug("Setting options")
set_options(speech_client, options)


if options.list_voices:
    print speech_client.voices()

log.debug("Speaking")
speech_client.say_text(string.join(args, ' '))

sys.exit(0)


