import socket
import ssl

connections = {}
MAX_REDIRECTS = 10

class URL:    
    def __init__(self, url):
        self.view_source = False
        self.scheme = None
        self.mediatype = None
        self.data = None
        self.host = None
        self.path = None
        self.port = None

        # If the URL starts with view-source: set the flag and remove the scheme
        if url.startswith("data:"):
            self.scheme = "data"
            self.mediatype, self.data = url.split(",", 1)
            return

        if url.startswith("view-source:"):
            # If the URL starts with view-source: set the flag and remove the scheme
            self.view_source = True
            url = url[12:]
        else:
            self.view_source = False

        # Split the URL into scheme, host, and path
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https", "file", "data"]
        # Set the default port for the scheme
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443
        elif self.scheme == "file":
            self.port = None
        elif self.scheme == "data":
            self.port = None

        # Parse the hoset and the path
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url
        # If the host contains a port, use it instead of the default port
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)

    def request(self):
        if self.scheme == "data":
            return self.return_request(self.data)
        if self.host is None:
            raise ValueError("Invalid host: {}".format(self.host))

        # If the scheme is file, open the file specified by combining the host and path as a binary
        if self.scheme == "file":
            with open(self.host + self.path, encoding="utf8", newline="\r\n") as f:
                response = f.read()
                return self.return_request(response)

        # Create connection key for pooling
        connection_key = (self.host, self.port, self.scheme)
        # See if the connection exists
        s = connections.get(connection_key)
        if s is None:
            s = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )
            s.connect((self.host, self.port))
            # Wrap the socket in an SSL context if the scheme is https
            if self.scheme == "https":
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=self.host)
            # Store the connection
            connections[connection_key] = s

        # Send the request to the server
        request = "GET {} HTTP/1.1\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        request += "Connection: keep-alive\r\n"
        request += "User-Agent: jvbrowser/1.0\r\n"
        request += "\r\n"
        s.send(request.encode("utf8"))
        
        # Read the response from the server
        response = s.makefile("rb")
        statusline = response.readline().decode("utf8")
        version, status, explanation = statusline.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline().decode("utf8")
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        # If the status is a redirect, return the redirect URL
        if int(status) >= 300 and int(status) < 400:
            assert "location" in response_headers
            redirect_url = response_headers["location"]
            # If the redirect URL is relative, make it absolute
            if redirect_url.startswith("/") and self.scheme is not None:
                redirect_url = self.scheme + "://" + self.host + redirect_url
            return self.return_request(redirect_url = redirect_url)
        elif int(status) >= 400:
            raise Exception("Error: {} {}".format(status, explanation))
        
        # Read only up to content length
        if "content-length" in response_headers:
            content_length = int(response_headers["content-length"])
            content = response.read(content_length).decode("utf8")
        else:
            # If we did not find content length, read all the content
            print("No content length")
            content = response.read().decode("utf8")
        return self.return_request(content)

    def return_request(self, content = None, view_source = None, redirect_url = None):
        return content, view_source, redirect_url

def show(body, view_source):
    if not body.startswith("<"):
        print(body)
        return

    # If the view source flag is set, do not parse the body as HTML. Just print it as is.
    if view_source:
        print(body)
        return

    in_tag = False
    in_entity = False
    entity = ""
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif c == "&":
            entity = "&"
            in_entity = True
        elif c == ";":
            entity += c
            decoded_entity = decode_entity(entity)
            if decoded_entity is not None:
                print(decoded_entity, end="")
            else:
                print(entity, end="")
            entity = ""
            in_entity = False
        elif in_entity:
            entity += c
            if len(entity) > 5:
                print(entity, end="")
                entity = ""
                in_entity = False      
        elif not in_tag and not in_entity:
            print(c, end="")

def decode_entity(entity):
    if entity == "&lt;":
        return "<"
    elif entity == "&gt;":
        return ">"
    else:
        return None

def load(url):
    body, view_source, redirect_url = url.request()

    redirects = 0
    while redirect_url is not None:
        body, view_source, redirect_url = URL(redirect_url).request()
        redirects += 1
        if redirects > MAX_REDIRECTS:
            raise Exception("Too many redirects")
    show(body, view_source)

if __name__ == "__main__":
    import sys
    load(URL(sys.argv[1]))