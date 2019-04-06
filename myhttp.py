#!/usr/bin/python3

"""Class for parsing and representing a Uniform Resource Indicator (URI)"""
class URI:
    """Create and parse a URI"""
    def __init__(self, string):
        self._uri = string

        # Parse URI
        self._absolute = string.startswith('http://')
        string = string.replace('http://', '')
        abs_path_start = string.find('/')
        if abs_path_start == -1:
            self._host = string
            self._abs_path = '/'
        elif abs_path_start == 0:
            self._host = None
            self._port = None
            self._abs_path = string
        else:
            self._host = string[:abs_path_start]
            self._abs_path = string[abs_path_start:]
        if self._host is not None:
            port_start = self._host.find(':')
            if port_start == -1:
                self._port = 80
            else:
                self._port = int(self._host[port_start+1:])
                self._host = self._host[:port_start]
    
    """Get the full URI"""
    @property
    def uri(self):
        return self._uri

    """Determine whether the URI is absolute (True) or relative (False)"""
    @property
    def absolute(self):
        return self._absolute

    """Get the host from the URI; returns None if the URI is relative"""
    @property
    def host(self):
        return self._host

    """Get the port from the URI; returns None if the URI is relative; returns
    80 if the URI is absolute and no port was specified"""
    @property
    def port(self):
        return self._port

    """Get the path from the URI"""
    @property
    def abs_path(self):
        return self._abs_path

    """Get a string representation of the URI"""
    def __str__(self):
        return self._uri

"""Class for parsing and representing a HTTP request"""
class HTTPRequest:
    """Create a HTTP request"""
    def __init__(self, method, uri, version='HTTP/1.1', headers={}):
        self._method = method
        self._uri = uri
        self._version = version
        self._headers = headers
    
    """Get the method from the HTTP request"""
    @property
    def method(self):
        return self._method

    """Get the URI from the HTTP request; returns a URI object"""
    @property
    def uri(self):
        return self._uri

    """Set the URI in the HTTP request"""
    def set_uri(self, uri):
        if type(uri) is str:
            self._uri = URI(uri)
        elif type(uri) is URI:
            self._uri = uri
        else:
            raise ValueError('Must provide a string or URI object')

    """Get the version from the HTTP response"""
    @property
    def version(self):
        return self._version

    """Get the headers from the HTTP request; returns a dictionary of 
    field-name, field-value pairs"""
    @property
    def headers(self):
        return self._headers

    """Set the value for a specific header field"""
    def set_header(self, name, value):
        self._headers[name] = value

    """Remove a specific header field from the HTTP request"""
    def remove_header(self, name):
        if name in self._headers:
            del self._headers[name]

    """Create a new HTTPRequest object by parsing a string containing an HTTP 
    request"""
    @classmethod
    def parse(cls, string):
        # Split into lines
        lines = string.split('\r\n')
        if len(lines) < 3:
            raise ValueError('HTTP request must contain at least a request-line and a blank line')

        # Find blank line
        blank_index = -1
        for i, line in enumerate(lines): 
            if lines[i] == '':
                blank_index = i
                break
        if blank_index == -1:
            raise ValueError('HTTP response must end with a blank line')

        # Parse request line
        request_line = lines[0].split(' ')
        if len(request_line) != 3:
            raise ValueError('HTTP request-line must contain a method, request-URI, and HTTP-version separated by spaces')
        method = request_line[0]
        uri = URI(request_line[1])
        version = request_line[2]
        
        # Parse message-header(s)
        headers = {} 
        for line in lines[1:blank_index]:
            colon_index = line.find(':')
            if colon_index == -1:
                raise ValueError('HTTP message-header must contain a field-name and a field-value separated by a colon (:)')
            headers[line[:colon_index]] = line[colon_index+1:].strip()

        return HTTPRequest(method, uri, version, headers)

    """Convert an HTTPRequest object into a string that is a properly formatted
    HTTP request"""
    def deparse(self):
        lines = [self._method + ' ' + str(self._uri) + ' ' + self._version]
        lines.extend([name + ': ' + value 
                for name, value in self._headers.items()])
        return '\r\n'.join(lines) + '\r\n\r\n'

    """Create an exact copy of the HTTP request; returns an HTTPRequest 
    object"""
    def clone(self):
        return HTTPRequest(self._method, self._uri, self._version, 
                self._headers)

    """Get a string representation of the HTTP request; note, this string does
    not conform to the format specified for HTTP requests sent across a network;
    use the deparse method to obtain such a represetnation of the request"""
    def __str__(self):
        return '\n'.join([
                'Method: ' + self._method,
                'URI: ' + str(self._uri),
                'Version: ' + self._version,
                'Headers:\n' + '\n'.join(['\t' + name + ': ' + value 
                        for name, value in self._headers.items()])
                ])

"""Class for parsing and representing a HTTP response"""
class HTTPResponse:
    def __init__(self, status_code, reason_phrase, version='HTTP/1.1', 
            headers={}):
        self._status_code = status_code
        self._reason_phrase = reason_phrase
        self._version = version
        self._headers = headers

    """Get the status code from the HTTP response"""
    @property
    def status_code(self):
        return self._status_code

    """Get the reason phrase from the HTTP response"""
    @property
    def reason_phrase(self):
        return self._reason_phrase

    """Get the version from the HTTP response"""
    @property
    def version(self):
        return self._version

    """Get the headers from the HTTP response; returns a dictionary of 
    field-name, field-value pairs"""
    @property
    def headers(self):
        return self._headers

    """Get the value for a specific header field"""
    def get_header(self, name):
        if name not in self._headers:
            return None
        return self._headers[name]

    """Set the value for a specific header field"""
    def set_header(self, name, value):
        self._headers[name] = value

    """Remove a specific header field from the HTTP response"""
    def remove_header(self, name):
        if name in self._headers:
            del self._headers[name]

    """Create a new HTTPResponse object by parsing a string containing an HTTP 
    response"""
    @classmethod
    def parse(cls, string):
        # Split into lines
        lines = string.split('\r\n')
        if len(lines) < 3:
            raise ValueError('HTTP response must contain at least a status-line and a blank line')

        # Find blank line
        blank_index = -1
        for i, line in enumerate(lines): 
            if lines[i] == '':
                blank_index = i
                break
        if blank_index == -1:
            raise ValueError('HTTP response must end with a blank line')

        # Parse status line
        status_line = lines[0].split(' ')
        if len(status_line) < 3:
            raise ValueError('HTTP status-line must contain a HTTP-version, status-code, and reason-phrase separated by spaces')
        version = status_line[0]
        status_code = int(status_line[1])
        reason_phrase = ' '.join(status_line[2:])
        
        # Parse message-header(s)
        headers = {} 
        for line in lines[1:blank_index]:
            colon_index = line.find(':')
            if colon_index == -1:
                raise ValueError('HTTP response-header must contain a field-name and a field-value separated by a colon (:)')
            headers[line[:colon_index]] = line[colon_index+1:].strip()

        return HTTPResponse(status_code, reason_phrase, version, headers)

    """Convert an HTTPResponse object into a string that is a properly formatted
    HTTP response"""
    def deparse(self):
        lines = [self._version + ' ' + str(self._status_code) + ' ' + self._reason_phrase]
        lines.extend([name + ': ' + value 
                for name, value in self._headers.items()])
        return '\r\n'.join(lines) + '\r\n\r\n'

    """Create an exact copy of the HTTP response; returns an HTTPResponse 
    object"""
    def clone(self):
        return HTTPResponse(self._status_code, self._reason_phrase, 
                self._version, self._headers)

    """Get a string representation of the HTTP response; note, this string does
    not conform to the format specified for HTTP responses sent across a 
    network; use the deparse method to obtain such a represetnation of the 
    response"""
    def __str__(self):
        return '\n'.join([
                'Version: ' + self._version,
                'Status code: ' + str(self._status_code),
                'Reason phrase: ' + self._reason_phrase,
                'Headers:\n' + '\n'.join(['\t' + name + ': ' + value 
                        for name, value in self._headers.items()])
                ])

