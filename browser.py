import socket
import ssl

class URL:
    def __init__(self, url):
        if url.startswith("data:"):
            self.scheme = "data"
            self.mediatype, self.data = url.split(",", 1)
            self.host = None
            self.path = None
            return

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
            return self.data
        if self.host is None:
            raise ValueError("Invalid host: {}".format(self.host))

        # Create a socket for the connection
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )

        # If the scheme is file, open the file specified by combining the host and path as a binary
        if self.scheme == "file":
            with open(self.host + self.path, encoding="utf8", newline="\r\n") as f:
                response = f.read()
                return response

        # Otherwise, connect to the server
        s.connect((self.host, self.port))
        # Wrap the socket in an SSL context if the scheme is https
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        # Send the request to the server
        request = "GET {} HTTP/1.1\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        request += "Connection: close\r\n"
        request += "User-Agent: jvbrowser/1.0\r\n"
        request += "\r\n"
        s.send(request.encode("utf8"))
        # Read the response from the server
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        # Read the content from the response
        content = response.read()
        s.close()
        return content

def show(body):
    if not body.startswith("<"):
        print(body)
        return

    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")

def load(url):
    body = url.request()
    show(body)

if __name__ == "__main__":
    import sys
    load(URL(sys.argv[1]))