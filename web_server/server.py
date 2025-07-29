import socket
import urllib

ENTRIES = [ 'Pavel was here' ]

def add_entry(params):
    if 'guest' in params:
        ENTRIES.append(params['guest'])
    return show_comments()

def not_found(url, method):
    out = "<!doctype html>"
    out += "<h1>{} {} not found!</h1>".format(method, url)
    return out

def form_decode(body):
    params = {}
    for field in body.split("&"):
        name, value = field.split("=", 1)
        name = urllib.parse.unquote_plus(name)
        value = urllib.parse.unquote_plus(value)
        params[name] = value
    return params

def do_request(method, url, headers, body):
    if method == "GET" and url == "/":
        return "200 OK", show_comments()
    elif method == "POST" and url == "/add":
        params = form_decode(body)
        return "200 OK", add_entry(params)
    else:
        return "404 Not Found", not_found(url, method)

def show_comments():
    out = "<!doctype html>"
    out += "<html><head><title>Guest Book</title></head><body>"
    out += "<h1>Guest Book</h1>"
    for entry in ENTRIES:
        out += "<p>" + entry + "</p>"

    out += "<form action=/add method=post>"
    out +=   "<p><input name=guest placeholder='Enter your name'></p>"
    out +=   "<p><button>Sign the book!</button></p>"
    out += "</form>"
    out += "</body></html>"
    return out


def handle_connection(conx):
    req = conx.makefile("b")
    reqline = req.readline().decode('utf8')
    method, url, version = reqline.split(" ", 2)
    assert method in ["GET", "POST"]

    headers = {}
    while True:
        line = req.readline().decode('utf8')
        if line == '\r\n': break
        header, value = line.split(":", 1)
        headers[header.casefold()] = value.strip()

    if 'content-length' in headers:
        length = int(headers['content-length'])
        body = req.read(length).decode('utf8')
    else:
        body = ""

    status, body = do_request(method, url, headers, body)

    response = "HTTP/1.1 {}\r\n".format(status)
    response += "Content-Type: text/html; charset=utf-8\r\n"
    response += "Content-Length: {}\r\n".format(
        len(body.encode("utf8")))
    
    # Handle persistent connections
    connection_header = headers.get('connection', '').lower()
    if connection_header == 'keep-alive':
        response += "Connection: keep-alive\r\n"
        should_close = False
    else:
        response += "Connection: close\r\n"
        should_close = True
    
    response += "\r\n" + body
    conx.send(response.encode('utf8'))
    
    if should_close:
        conx.close()


s = socket.socket(
    family=socket.AF_INET,
    type=socket.SOCK_STREAM,
    proto=socket.IPPROTO_TCP)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

s.bind(('', 8000))
s.listen()

print("Server running on http://localhost:8000")

while True:
    conx, addr = s.accept()
    handle_connection(conx)