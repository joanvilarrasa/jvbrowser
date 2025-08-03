import socket
import urllib.parse
import random
import html

ENTRIES = [ ('Someone was here', 'god') ]
SESSIONS = {}
LOGINS = {
    "johndoe": "hello",
    "jv": "hi"
}

def add_entry(session, params):
    if "user" not in session: return
    if "nonce" not in session or "nonce" not in params: return
    if session["nonce"] != params["nonce"]: return
    if 'guest' in params and len(params['guest']) <= 100:
        ENTRIES.append((params['guest'], session["user"]))
    return

def not_found(url, method):
    out = "<html>"
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

def do_request(session, method, url, headers, body):
    if method == "GET" and url == "/":
        return "200 OK", show_comments(session)
    elif method == "POST" and url == "/":
        params = form_decode(body)
        return do_login(session, params)

    # Login form
    elif method == "GET" and url == "/login":
        return "200 OK", login_form(session)

    # Comment things 
    elif method == "GET" and url == "/comment.js":
        with open("web_server/comment.js") as f:
            return "200 OK", f.read()
    elif method == "GET" and url == "/comment.css":
        with open("web_server/comment.css") as f:
            return "200 OK", f.read()

    # Add comment post
    elif method == "POST" and url == "/add":
        params = form_decode(body)
        add_entry(session, params)
        return "200 OK", show_comments(session)

    # Fallback to 404
    else:
        return "404 Not Found", not_found(url, method)

def login_form(session):
    body = "<!doctype html>"
    body += "<form action=/ method=post>"
    body += "<p>Username: <input name=username></p>"
    body += "<p>Password: <input name=password type=password></p>"
    body += "<p><button>Log in</button></p>"
    body += "</form>"
    return body 

def do_login(session, params):
    username = params.get("username")
    password = params.get("password")
    if username in LOGINS and LOGINS[username] == password:
        session["user"] = username
        return "200 OK", show_comments(session)
    else:
        out = "<!doctype html>"
        out += "<h1>Invalid password for {}</h1>".format(username)
        return "401 Unauthorized", out

def show_comments(session):
    out = "<html>"
    out += "<script src=/comment.js></script>"
    out += "<script src=https://example.com/evil.js></script>"
    out += "<link rel=stylesheet href=/comment.css>"
    if "user" in session:
        nonce = str(random.random())[2:]
        session["nonce"] = nonce
        out += "<h1>Hello, " + session["user"] + "</h1>"
        out += "<form action=add method=post>"
        out +=   "<p><input name=guest></p>"
        out +=   "<p><button>Sign the book!</button></p>"
        out +=   "<input name=nonce type=hidden value=" + nonce + ">"
        out += "</form>"
    else:
        out += "<a href=/login>Sign in to write in the guest book</a>"
    out += "<strong></strong>"
    for entry, who in ENTRIES:
        out += "<p>" + html.escape(entry) + "\n"
        out += "<i>by " + html.escape(who) + "</i></p>"
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
        body = None

    # Generate a random token for the user
    if "cookie" in headers:
        token = headers["cookie"][len("token="):]
    else:
        token = str(random.random())[2:]

    session = SESSIONS.setdefault(token, {})
    status, body = do_request(session, method, url, headers, body)

    response = "HTTP/1.1 {}\r\n".format(status)
    response += "Content-Type: text/html; charset=utf-8\r\n"
    response += "Content-Length: {}\r\n".format(
        len(body.encode("utf8")))
    # Security (cookies, CSP)
    if "cookie" not in headers:
        template = "Set-Cookie: token={}; SameSite=Lax\r\n"
        response += template.format(token)
    csp = "default-src http://localhost:8000"
    response += "Content-Security-Policy: {}\r\n".format(csp)
    print(response)
    response += "\r\n" + body
    conx.send(response.encode('utf8'))
    
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