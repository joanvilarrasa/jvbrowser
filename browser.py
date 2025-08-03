import tkinter
from chrome.chrome import Chrome
from chrome.tab import Tab
from css.css_parser import CSSParser
from layout.block_layout import HEIGHT, WIDTH
import socket
import ssl
import gzip

COOKIE_JAR = {}
MAX_REDIRECTS = 10

class Browser:
    def __init__(self):
        self.tabs = []
        self.active_tab = None
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
            bg="white"
        )
        self.canvas.pack(fill=tkinter.BOTH, expand=True)
        self.chrome = Chrome(self, URL)

        # Setup bindings
        self.window.bind("<Down>", self.handle_scrolldown)
        self.window.bind("<Up>", self.handle_scrollup)
        self.window.bind("<Button-4>", self.handle_scrollup)
        self.window.bind("<Button-5>", self.handle_scrolldown)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Key>", self.handle_key)
        self.window.bind("<Return>", self.handle_enter)

    # Tab management
    def new_tab(self, url):
        new_tab = Tab(HEIGHT - self.chrome.bottom, URL)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
        self.draw()

    # Event handlers
    def handle_scrolldown(self, e):
        self.active_tab.scrolldown()
        self.draw() 
    def handle_scrollup(self, e):
        self.active_tab.scrollup()
        self.draw()
    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            self.focus = None
            self.chrome.click(e.x, e.y)
        else:
            self.focus = "content"
            self.chrome.blur()
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
        self.draw()
    def handle_key(self, e):
        if len(e.char) == 0: return
        if not (0x20 <= ord(e.char) < 0x7f): return
        if self.chrome.keypress(e.char):
            self.draw()
        elif self.focus == "content":
            self.active_tab.keypress(e.char)
            self.draw()
            
    def handle_enter(self, e):
        self.chrome.enter()
        self.draw()

    # Drawing
    def draw(self):
        self.canvas.delete("all")
        self.active_tab.draw(self.canvas, self.chrome.bottom)
        for cmd in self.chrome.paint():
            cmd.execute(0, self.canvas)

class URL:    
    def __init__(self, url):
        self.view_source = False
        self.scheme = None
        self.mediatype = None
        self.data = None
        self.host = None
        self.path = None
        self.port = None
        self.method = "GET"
        self.redirects = 0
        self.is_valid_url = True
        self.init_url(url)

    def __str__(self):
        port_part = ":" + str(self.port)
        if self.scheme == "https" and self.port == 443:
            port_part = ""
        if self.scheme == "http" and self.port == 80:
            port_part = ""
        return self.scheme + "://" + self.host + port_part + self.path

    def init_url(self, url):
        try:
            self.view_source = False

            # Split the URL into scheme, host, and path
            self.scheme, url = url.split("://", 1)
            assert self.scheme in ["http", "https", "file"]
            # Set the default port for the scheme
            if self.scheme == "http":
                self.port = 80
            elif self.scheme == "https":
                self.port = 443
            elif self.scheme == "file":
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
            
        except Exception as e:
            self.scheme = "about:blank"
            self.url = "about:blank"
            self.is_valid_url = False
    
    def request(self, referrer, payload=None):
        if not self.is_valid_url:
            return ""
        
        if self.host is None:
            raise ValueError("Invalid host: {}".format(self.host))

        # If the scheme is file, open the file specified by combining the host and path as a binary
        if self.scheme == "file":
            with open(self.host + self.path, encoding="utf8", newline="\r\n") as f:
                response = f.read()
                return response 

        self.method = "POST" if payload else "GET"

        # Send the request to the server
        length = len(payload.encode("utf8")) if payload else None
        request = "{} {} HTTP/1.1\r\n".format(self.method, self.path)
        request += "Host: {}\r\n".format(self.host)
        
        request += "User-Agent: jvbrowser/1.0\r\n"
        request += "Accept-Encoding: gzip\r\n"
        if self.host in COOKIE_JAR:
            cookie, params = COOKIE_JAR[self.host]
            allow_cookie = True
            if referrer and params.get("samesite", "none") == "lax":
                if self.method != "GET":
                    allow_cookie = self.host == referrer.host
            if allow_cookie:
                request += "Cookie: {}\r\n".format(cookie)
        if length:
            request += "Content-Length: {}\r\n".format(length)
        request += "\r\n"

        # Moved the socket after the cache check to avoid opening a connection if the request is cached
        s = self.get_open_socket()
        if payload: request += payload
        s.send(request.encode("utf8"))
        
        # Read the response from the server
        response = s.makefile("rb")
        version, status, explanation, response_headers = self.get_response_metadata(response)

        if "set-cookie" in response_headers:
            cookie = response_headers["set-cookie"]
            params = {}
            if ";" in cookie:
                cookie, rest = cookie.split(";", 1)
                for param in rest.split(";"):
                    if '=' in param:
                        param, value = param.split("=", 1)
                    else:
                        value = "true"
                    params[param.strip().casefold()] = value.casefold()
            COOKIE_JAR[self.host] = (cookie, params)

        # Handle redirects
        if int(status) >= 300 and int(status) < 400:
            content = self.handle_redirect(response_headers)
            self.redirects = 0
            return content

        # Get the content of the response
        content = self.get_response_content(response, response_headers)

        s.close()
        return response_headers, content

    def get_open_socket(self): 
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
        s.connect((self.host, self.port))
    
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        return s

    def get_response_metadata(self, response):
        statusline = response.readline().decode("utf8")
        version, status, explanation = statusline.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline().decode("utf8")
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        return version, status, explanation, response_headers

    def get_response_content(self, response, response_headers):
        # Handle transfer-encoding first
        if "transfer-encoding" in response_headers:
            transfer_encoding = response_headers["transfer-encoding"]
            if transfer_encoding == "chunked":
                raw_content = self.read_chunked_content(response)
            else:
                raise ValueError(f"Unsupported transfer encoding: {transfer_encoding}")
        elif "content-length" in response_headers:
            content_length = int(response_headers["content-length"])
            raw_content = response.read(content_length)
        else:
            print("No content length")
            raw_content = response.read()
        
        # Handle content-encoding after getting the raw content
        if "content-encoding" in response_headers:
            assert response_headers["content-encoding"] == "gzip"
            content = gzip.decompress(raw_content).decode("utf8")
        else:
            content = raw_content.decode("utf8")
        
        return content

    def read_chunked_content(self, response):
        chunks = []
        while True:
            # Read the chunk size line
            chunk_size_line = response.readline().decode("utf8").strip()
            if not chunk_size_line:
                continue
            
            # Parse the chunk size (hexadecimal)
            chunk_size = int(chunk_size_line.split(';')[0], 16)
            
            # If chunk size is 0, we've reached the end
            if chunk_size == 0:
                break
            
            # Read the chunk data
            chunk_data = response.read(chunk_size)
            chunks.append(chunk_data)
            
            # Read the CRLF after the chunk
            response.readline()
        
        # Combine all chunks and return as bytes
        content = b''.join(chunks)
        return content

    def handle_redirect(self, response_headers):
        if self.redirects > MAX_REDIRECTS:
            raise Exception("Too many redirects")
        self.redirects += 1
        assert "location" in response_headers
        assert self.scheme is not None
        assert self.host is not None
        
        redirect_url = response_headers["location"]
        # If the redirect URL is relative, make it absolute
        if redirect_url.startswith("/"):
            self.path = redirect_url
            return self.request()
        else:
            self.init_url(redirect_url)
            return self.request()
    
    def resolve(self, url):
        if "://" in url: return URL(url)
        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            while url.startswith("../"):
                _, url = url.split("/", 1)
                if "/" in dir:
                    dir, _ = dir.rsplit("/", 1)
            url = dir + "/" + url
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        else:
            return URL(self.scheme + "://" + self.host + \
                       ":" + str(self.port) + url)

    def origin(self):
        return self.scheme + "://" + self.host + ":" + str(self.port)

            
if __name__ == "__main__":
    import sys
    url = sys.argv[1]
    if url is None:
        print("Usage: python browser.py <url>")
        sys.exit(1)
    browser = Browser()
    browser.new_tab(URL(url))
    tkinter.mainloop()


