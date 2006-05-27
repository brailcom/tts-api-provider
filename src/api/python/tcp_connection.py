#
# tts-api.py - Python implementation of TTS API
#   
# Copyright (C) 2001, 2002, 2003 Brailcom, o.p.s.
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
# $Id: tcp_connection.py,v 1.1 2006-05-27 21:14:51 hanke Exp $

# --------------- Connection handling ------------------------

import socket;
import string;

class _TCP_TTSAPI_Connection:

    NEWLINE = "\r\n"
    """New line delimiter """

    END_OF_DATA_SINGLE = "."
    """Data end marker single in a message"""

    END_OF_DATA_BEGIN = END_OF_DATA_SINGLE + NEWLINE
    """Data end marker on the beginning of a message"""

    END_OF_DATA = NEWLINE + END_OF_DATA + NEWLINE    
    """Data end marker (full)"""

    END_OF_DATA_ESCAPED_SINGLE = ".."
    "Escaping for END_OF_DATA_SINGLE"

    END_OF_DATA_ESCAPED_BEGIN = END_OF_DATA_ESCAPED_SINGLE + NEWLINE
    "Escaping for END_OF_DATA_BEGIN"

    END_OF_DATA_ESCAPED = NEWLINE + END_OF_DATA_ESCAPED_SINGLE + NEWLINE
    "Escaping for END_OF_DATA"

    def __init__ (self, host, port):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((socket.gethostbyname(host), port))

    
    def _readline (self):
        """Read one whole line from the socket.
        
        Read from the socket until the newline delimeter (given by the
        `NEWLINE' constant).  Blocks until the delimiter is read.
        """

        # TODO: This must be fixed. Character by character reading
        # is very slow.
        
        line = ''
        pointer = 0
        while 1:
            char = self._socket.recv(1)
            line += char
            if char == self.NEWLINE[pointer]:
                pointer += 1
            else:
                pointer = 0
            if pointer == len(self.NEWLINE):
                return line[:-pointer]
            
    def _recv_response (self):
        """Read server response and return the triplet (code, msg, data)."""
        data = []
        c = None
        while 1:
            line = self._readline()
            assert len(line) >= 4, "Malformed data received from server!"
            code, sep, text = line[:3], line[3], line[4:]
            assert code.isalnum() and (c is None or code == c) and \
                   sep in ('-', ' '), "Malformed data received from server!"
            if sep == ' ':
                msg = text
                return int(code), msg, tuple(data)
            data.append(text)

    def send_command (self, command, *args):
        """Send SSIP command with given arguments and read server response.

        Arguments can be of any data type -- they are all stringified before
        being sent to the server.

        Return a triplet (code, msg, data), where 'code' is a numeric 
        response code as an integer, 'msg' is a response message as string
        and 'data' is a tuple of strings (all lines of response data) when a
        response contains some data.
        
        Raise an exception in case of error response (non 2xx code).
        
        """
        cmd = ' '.join((command,) + tuple(map(str, args)))
        self._socket.send(cmd + self.NEWLINE)
        code, msg, data = self._recv_response()
        if code/100 != 2:
            raise TTSAPIError(code, msg, cmd)
        return code, msg, data

    def send_data (self, data):
        """Send multiline data and read server responsse.

        Returned value is the same as for 'send_command()' method.

        """

        # Escape the end-of-data sequence even if presented on the beginning
        if data[0:3] == self.END_OF_DATA_BEGIN:
            data = self.END_OF_DATA_ESCAPED_BEGIN + data[3:]

        if (len(data) == 1) and (data[0] == '.'):
            data = self.END_OF_DATA_ESCAPED_SINGLE
        
        data = string.replace(data, self.END_OF_DATA, self.END_OF_DATA_ESCAPED)
        self._socket.send(data + self.END_OF_DATA)
        code, msg, data = self._recv_response()
        if code/100 != 2:
            raise TTSAPIError(code, msg, data)
        return code, msg
        
    def close (self):
        """Close the connection."""
        self._socket.close()
