#
# logs.py - Logging
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
# $Id: logs.py,v 1.3 2007-06-16 18:02:09 hanke Exp $

import logging
import sys

class Logging(logging.Logger):
    """Class for logging of TTS API Provider core. Initialization happens in
    two stages.  First the object is constructed and the output is redirected
    to stderr. As soon as configuration is loaded, Logging.init_stage2() should
    be called to setup the logging with the desired parameters."""
    
    def __init__(self):
        # TODO: Remove DEBUG once this early stage is stable enough
        logging.Logger.__init__(self, 'tts-api-provider', level=logging.DEBUG)
        self.stdout_handler = logging.StreamHandler(sys.stdout)
        self.addHandler(self.stdout_handler)
        
    def init_stage2(self, conf):
        """Close stderr logging output and initialize logging with all config
        options
        
        Important options:
            conf.log_path -- full path of the central logging file
            conf.log_format -- desired format of the logging output
            conf.log_level -- logging level (see logging.Logger constants
            for more information)
        """
        
        # TODO: First write to log file all the information gathered at stage 1

        # Save reference to the configuration object for later use
        if not conf.log_on_stdout:
            self.removeHandler(self.stdout_handler)
        self.file_handler = logging.FileHandler(conf.log_path)
        formatter = logging.Formatter(conf.log_format)
        self.file_handler.setFormatter(formatter)
        self.addHandler(self.file_handler)
        self.setLevel(conf.log_level)
