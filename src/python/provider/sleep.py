
#
# sleep.py - Interruptible sleeper
#   
# Copyright (C) 2007 Brailcom, o.p.s.
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
# $Id: sleep.py,v 1.1 2007-09-29 11:18:08 hanke Exp $

"""Interruptible sleep implementation"""

import thread
import socket
import select
import os

class Sleeper(object):
    """Interruptible sleep implementation"""

    def __init__(self):
        """Initialize pipe for interruption requests"""
        self._interruption_pipe = os.pipe()
        self._lock = thread.allocate_lock()

    def __del__(self):
        """Clean up"""
        self._lock.acquire()
        os.close(self._interruption_pipe[0])
        os.close(self._interruption_pipe[1])
        self._lock.release()

    def sleep(self, seconds):
        """Do what a sleeper most likes. Sleep for the given amount of seconds
        (floating point number allowed), but stay reasonably alert so
        that we can quickly wake up on self.interrupt()"""
        
        sel = select.select([self._interruption_pipe[0]], [], [], seconds)
        self._lock.acquire()
        try:
            if len(sel[0]) != 0:
                os.read(self._interruption_pipe[0], 1)
        finally:
            self._lock.release()

    def interrupt(self):
        
        self._lock.acquire()
        try:
            os.write(self._interruption_pipe[1],"1")
        finally:
            self._lock.release()
