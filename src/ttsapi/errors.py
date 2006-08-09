
class Error(Exception):
    _detail = ""

    def __init__(self, detail = None):
        self._detail = detail
        
    def detail(self):
        return self._detail;

class ServerError(Error):
    """Server side error, problem on the server side or in the driver."""
    pass

class ClientError(Error):
    """Client error, invalid arguments or parameters received,
    invalid commands syntax, unparseable input."""
    pass

class UnknownError(Error):
    """Unknown error (possibly with helpful method detail())"""
    pass

class ErrorNotSupportedByDriver(ServerError):
    """Not supported by the driver."""
    pass

class ErrorNotSupportedByServer(ServerError):
    """Not supported by the server (implementation incomplete)."""
    pass

class ErrorAccessToDriverDenied(ServerError):
    """Cannot access driver."""
    pass

class ErrorInternal(ServerError):
    """Internal server error"""
    def __init():
        # TODO: Include traceback
        self._traceback = None
        
    def traceback(self):
        return self._traceback

class ErrorInvalidCommand(ClientError):
    """Invalid command, wrong formating of parameters etc."""
    pass

class ErrorInvalidArgument(ClientError):
    """Invalid command argument value given"""
    pass

class ErrorMissingArgument(ClientError):
    """Missing mandatory command argument."""
    pass

class ErrorInvalidParameter(ClientError):
    """Trying to set invalid parameter."""
    pass

class ErrorWrongEncoding(ClientError):
    """Invalid encoding from client."""
    pass

