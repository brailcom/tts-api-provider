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
# $Id: connection.py,v 1.1 2006-07-03 20:52:29 hanke Exp $

# --------------- Connection handling ------------------------

import socket;
import string;
import sys;

class Connection(object):

#    NEWLINE = "\r\n"
    NEWLINE = "\n"
    """New line delimiter """

    END_OF_DATA_SINGLE = "."
    """Data end marker single in a message"""

    END_OF_DATA_BEGIN = END_OF_DATA_SINGLE + NEWLINE
    """Data end marker on the beginning of a message"""

    END_OF_DATA = NEWLINE + END_OF_DATA_SINGLE + NEWLINE    
    """Data end marker (full)"""

    END_OF_DATA_ESCAPED_SINGLE = ".."
    "Escaping for END_OF_DATA_SINGLE"

    END_OF_DATA_ESCAPED_BEGIN = END_OF_DATA_ESCAPED_SINGLE + NEWLINE
    "Escaping for END_OF_DATA_BEGIN"

    END_OF_DATA_ESCAPED = NEWLINE + END_OF_DATA_ESCAPED_SINGLE + NEWLINE
    "Escaping for END_OF_DATA"    

    def __init__ (self):
        pass

    def _read_line(self):
        """Read one whole line from the communication channel.

        Read from the socket until the newline delimeter (given by the
        `NEWLINE' constant).  Blocks until the delimiter is read.
        
        """
        raise NotImplementedError

    def _nil_to_None(self, str):
        if str == 'nil':
            return None
        else:
            return str
        

    def _write(self, data):
        """Write data to output.

        data -- contains the data to be written including the
        necessary newlines and carriage return characters."""
        
        raise NotImplementedError
    
    def _recv_response (self):
        """Read server response and return the triplet (code, msg, data)
        where data is a tuple of unparsed strings found on each line."""
        data = []
        c = None
        while 1:
            line = self._read_line()
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
        def arg_to_str(arg):
            if arg == None:
                return 'nil'
            else:
                return str(arg)
    
        cmd = ' '.join((command,) + tuple(map(arg_to_str, args))) \
              + self.NEWLINE
        self._write(cmd)
        code, msg, data = self._recv_response()
        if code/100 != 2:
            raise TTSAPIError(code, msg, cmd)
        return code, msg, data

    def parse_list (self, data):
        """Sends a command which expects reply in the form of a list and
        returns the parsed reply.

        Returns a nested list. Each atom in the main list corresponds with one
        line of the reply and contains a list of constants on that line.
        """        
        result = []
        for line in data:
            j = 0
            constr, quotes = False, False
            result_line = []
            for i in range(0, len(line)-1):
                if constr == True:
                    if (line[i] == ' ' and quotes == False):
                        result_line.append(self._nil_to_None(line[j:i]))
                        constr = False
                    elif (line[i] == '"' and quotes == True):
                        result_line.append(line[j:i])
                        constr, quotes = False, False
                elif constr == False:
                    if line[i] == '"':
                        j = i+1
                        constr, quotes = True, True
                    elif line[i] != ' ':
                        j = i
                        constr, quotes = True, False
            result_line.append(line[j:].rstrip('"'))
            result.append(result_line)
        return result


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
        self._write(data + self.END_OF_DATA)
        code, msg, rep_data = self._recv_response()
        if code/100 != 2:
            raise TTSAPIError(code, msg, data)
        return code, msg, rep_data
        
    def close (self):
        """Close the connection."""
        pass

class SocketConnection(Connection):

    def __init__(self, host="127.0.0.1", port=6570):
        """Init a connection to the server"""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((socket.gethostbyname(host), port))

    def _read_line(self):
        """Read one whole line from the socket.
        
        Read from the socket until the newline delimeter (given by the
        `NEWLINE' constant).  Blocks until the delimiter is read.
        
        """
        pointer = self._buffer.find(self.NEWLINE)
        while pointer == -1:
            self._buffer += self._socket.recv(1024)
            pointer = self._buffer.find(self.NEWLINE)
        line = self._buffer[:pointer]
        self._buffer = self._buffer[pointer+len(self.NEWLINE):]
        return line

    def _write(self, data):
        """Write data to output.

        data -- contains the data to be written including the
        necessary newlines and carriage return characters."""
        
        self._socket.send(data)

    def close (self):
        """Close the connection."""
        self._socket.close()

class PipeConnection(Connection):

    def __init__(self, pipe_in=sys.stdin, pipe_out=sys.stdout):
        """Setup pipes for communication

        pipe_in -- pipe for incomming communication (replies)
        pipe_out -- pipe for outcomming communication (commands, data)
        """
        self.pipe_in=pipe_in
        self.pipe_out=pipe_out

    def _read_line(self):
        """Read one whole line from the socket.
        
        Read from the socket until the newline delimeter (given by the
        `NEWLINE' constant).  Blocks until the delimiter is read.
        
        """
        return self.pipe_in.readline().rstrip(self.NEWLINE)

    def _write(self, data):
        """Write data to output.

        data -- contains the data to be written including the
        necessary newlines and carriage return characters."""
        
        self.pipe_out.write(data)

    def close (self):
        """Close the connection."""
        pass
