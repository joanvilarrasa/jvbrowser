import ctypes
import gzip
import math
import sdl2
import skia
import socket
import ssl
import threading
import urllib.parse
from css.css_parser import CSSParser, style
from css.selectors import cascade_priority
from draw import DrawLine, DrawOutline, DrawRect, DrawText, contains_point, linespace, paint_tree
from font_cache import get_font
from htmltree.htmlparser import HTMLParser
from htmltree.tag import Element
from htmltree.text import Text
from js.js_context import JSContext
from layout.block_layout import HEIGHT, VSTEP, WIDTH
from layout.document_layout import DocumentLayout
from task import Task, TaskRunner
from utils import tree_to_list

SCROLL_STEP = 100
DEFAULT_STYLE_SHEET = CSSParser(open("css/default.css").read()).parse()
REFRESH_RATE_SEC = .033
COOKIE_JAR = {}
MAX_REDIRECTS = 10

class Browser:
    def __init__(self):
        self.tabs = []
        self.active_tab = None
        self.chrome = Chrome(self, URL)
        self.animation_timer = None
        self.needs_raster_and_draw = False
        self.needs_animation_frame = True

        if sdl2.SDL_BYTEORDER == sdl2.SDL_BIG_ENDIAN:
            self.RED_MASK = 0xff000000
            self.GREEN_MASK = 0x00ff0000
            self.BLUE_MASK = 0x0000ff00
            self.ALPHA_MASK = 0x000000ff
        else:
            self.RED_MASK = 0x000000ff
            self.GREEN_MASK = 0x0000ff00
            self.BLUE_MASK = 0x00ff0000
            self.ALPHA_MASK = 0xff000000

        self.sdl_window = sdl2.SDL_CreateWindow(b"Browser",
            sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
            WIDTH, HEIGHT, sdl2.SDL_WINDOW_SHOWN)

        self.root_surface = skia.Surface.MakeRaster(
            skia.ImageInfo.Make(
                WIDTH, HEIGHT,
                ct=skia.kRGBA_8888_ColorType,
                at=skia.kUnpremul_AlphaType))

        self.chrome_surface = skia.Surface(WIDTH, math.ceil(self.chrome.bottom))
        self.tab_surface = None

    def set_needs_raster_and_draw(self):
        self.needs_raster_and_draw = True

    # Tab management
    def new_tab(self, url):
        new_tab = Tab(self, HEIGHT - self.chrome.bottom)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
        self.set_needs_raster_and_draw()
        self.raster_and_draw()

    # Event handlers
    def handle_scrolldown(self):
        self.active_tab.scrolldown()
        self.set_needs_raster_and_draw()

    def handle_scrollup(self):
        self.active_tab.scrollup()
        self.set_needs_raster_and_draw()

    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            self.focus = None
            self.chrome.click(e.x, e.y)
            self.set_needs_raster_and_draw()
        else:
            self.focus = "content"
            self.chrome.blur()
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
            url = self.active_tab.url
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
            if self.active_tab.url != url:
                self.set_needs_raster_and_draw()

    def handle_key(self, e):
        if len(e) == 0: return
        if not (0x20 <= ord(e) < 0x7f): return
        if self.chrome.keypress(e):
            self.set_needs_raster_and_draw()
        elif self.focus == "content":
            self.active_tab.keypress(e)
            self.set_needs_raster_and_draw()
            
    def handle_enter(self):
        self.chrome.enter()
        self.set_needs_raster_and_draw()

    # Drawing
    def raster_and_draw(self):
        if not self.needs_raster_and_draw: return
        self.raster_chrome()
        self.raster_tab()
        self.draw()
        self.needs_raster_and_draw = False

    def schedule_animation_frame(self):
        def callback():
            active_tab = self.active_tab
            task = Task(active_tab.render)
            active_tab.task_runner.schedule_task(task)
            self.animation_timer = None
            self.needs_animation_frame = False
        if self.needs_animation_frame and not self.animation_timer:
            self.animation_timer = threading.Timer(REFRESH_RATE_SEC, callback)
            self.animation_timer.start()

    def set_needs_animation_frame(self, tab):
        if tab == self.active_tab:
            self.needs_animation_frame = True

    def raster_tab(self):
        tab_height = math.ceil(self.active_tab.document.height)
        if not self.tab_surface or tab_height != self.tab_surface.height():
            self.tab_surface = skia.Surface(WIDTH, tab_height)
        canvas = self.tab_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        self.active_tab.raster(canvas)

    def raster_chrome(self):
        canvas = self.chrome_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        for cmd in self.chrome.paint():
            cmd.execute(canvas)

    def draw(self):
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        tab_rect = skia.Rect.MakeLTRB(0, self.chrome.bottom, WIDTH, HEIGHT)
        tab_offset = self.chrome.bottom - self.active_tab.scroll
        canvas.save()
        canvas.clipRect(tab_rect)
        canvas.translate(0, tab_offset)
        self.tab_surface.draw(canvas, 0, 0)
        canvas.restore()

        chrome_rect = skia.Rect.MakeLTRB(0, 0, WIDTH, self.chrome.bottom)
        canvas.save()
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)
        canvas.restore()

        skia_image = self.root_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()
        depth = 32 # Bits per pixel
        pitch = 4 * WIDTH # Bytes per row
        sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
            skia_bytes, WIDTH, HEIGHT, depth, pitch,
            self.RED_MASK, self.GREEN_MASK,
            self.BLUE_MASK, self.ALPHA_MASK)

        rect = sdl2.SDL_Rect(0, 0, WIDTH, HEIGHT)
        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window)
        # SDL_BlitSurface is what actually does the copy.
        sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)
        sdl2.SDL_UpdateWindowSurface(self.sdl_window)

    def handle_quit(self):
        sdl2.SDL_DestroyWindow(self.sdl_window)

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

class Chrome:
    def __init__(self, browser, url_class):
        self.url_class = url_class
        self.browser = browser
        # Setup font
        self.font = get_font(20, "normal", "roman")
        self.font_height = linespace(self.font)

        # Setup tabbar
        self.padding = 5
        self.tabbar_top = 0
        self.tabbar_bottom = self.font_height + 2*self.padding
        plus_width = self.font.measureText("+") + 2*self.padding
        # New tab button
        self.newtab_rect = skia.Rect.MakeLTRB(
           self.padding, self.padding,
           self.padding + plus_width,
           self.padding + self.font_height)

        # Setup urlbar
        self.focus = None
        self.address_bar = ""

        self.urlbar_top = self.tabbar_bottom
        self.urlbar_bottom = self.urlbar_top + self.font_height + 2*self.padding
        back_width = self.font.measureText("<") + 2*self.padding
        self.back_rect = skia.Rect.MakeLTRB(
            self.padding,
            self.urlbar_top + self.padding,
            self.padding + back_width,
            self.urlbar_bottom - self.padding)

        self.address_rect = skia.Rect.MakeLTRB(
            self.back_rect.top() + self.padding,
            self.urlbar_top + self.padding,
            WIDTH - self.padding,
            self.urlbar_bottom - self.padding)

        self.bottom = self.urlbar_bottom

    def paint(self):
        cmds = []

        # Paint background as white
        cmds.append(DrawRect(
            skia.Rect.MakeXYWH(0, 0, WIDTH, self.bottom),
            "white"))
        cmds.append(DrawLine(
            0, self.bottom, WIDTH,
            self.bottom, "black", 1))

        cmds.append(DrawOutline(self.newtab_rect, "black", 1))

        # Paint tabs bar new tab button
        cmds.append(DrawText(
            self.newtab_rect.left() + self.padding,
            self.newtab_rect.top(),
            "+", self.font, "black"))

        # Paint tabs bar tabs
        for i, tab in enumerate(self.browser.tabs):
            bounds = self.tab_rect(i)
            cmds.append(DrawLine(
                bounds.left(), 0, bounds.left(), bounds.bottom(),
                "black", 1))
            cmds.append(DrawLine(
                bounds.right(), 0, bounds.right(), bounds.bottom(),
                "black", 1))
            cmds.append(DrawText(
                bounds.left() + self.padding, bounds.top() + self.padding,
                "Tab {}".format(i), self.font, "black"))

            if tab == self.browser.active_tab:
                cmds.append(DrawLine(
                    0, bounds.bottom(), bounds.left(), bounds.bottom(),
                    "black", 1))
                cmds.append(DrawLine(
                    bounds.right(), bounds.bottom(), WIDTH, bounds.bottom(),
                    "black", 1))

        # Paint url bar back button
        cmds.append(DrawOutline(self.back_rect, "black", 1))
        cmds.append(DrawText(
            self.back_rect.left() + self.padding,
            self.back_rect.top(),
            "<", self.font, "black"))

        # Paint url bar address
        cmds.append(DrawOutline(self.address_rect, "black", 1))
        url = str(self.browser.active_tab.url)
        if self.focus == "address bar":
            cmds.append(DrawText(
                self.address_rect.left() + self.padding,
                self.address_rect.top(),
                self.address_bar, self.font, "black"))
            w = self.font.measureText(self.address_bar)
            cmds.append(DrawLine(
                self.address_rect.left() + self.padding + w,
                self.address_rect.top(),
                self.address_rect.left() + self.padding + w,
                self.address_rect.bottom(),
                "red", 1))
        else:
            url = str(self.browser.active_tab.url)
            cmds.append(DrawText(
                self.address_rect.left() + self.padding,
                self.address_rect.top(),
                url, self.font, "black"))

        return cmds

    def tab_rect(self, i):
        tabs_start = self.newtab_rect.right() + self.padding
        tab_width = self.font.measureText("Tab X") + 2*self.padding
        return skia.Rect.MakeLTRB(
            tabs_start + tab_width * i, self.tabbar_top,
            tabs_start + tab_width * (i + 1), self.tabbar_bottom)

    def click(self, x, y):
        self.focus = None
        if contains_point(self.newtab_rect, x, y):
            self.browser.new_tab(self.url_class("https://browser.engineering/"))
        elif contains_point(self.back_rect, x, y):
            self.browser.active_tab.go_back()
        elif contains_point(self.address_rect, x, y):
            self.focus = "address bar"
            self.address_bar = ""
        else:
            for i, tab in enumerate(self.browser.tabs):
                if contains_point(self.tab_rect(i), x, y):
                    self.browser.active_tab = tab
                    break

    def keypress(self, char):
        if self.focus == "address bar":
            self.address_bar += char
            return True
        return False

    def enter(self):
        if self.focus == "address bar":
            self.browser.active_tab.load(URL(self.address_bar))
            self.focus = None
            return True
        return False

    def blur(self):
        self.focus = None

class Tab:
    def __init__(self, browser, tab_height):
        # Setup content
        self.browser = browser
        self.task_runner = TaskRunner(self)
        self.tab_height = tab_height
        self.url = None
        self.document = DocumentLayout(None)
        self.nodes = []
        self.rules = DEFAULT_STYLE_SHEET.copy()
        self.display_list = []
        self.scroll = 0
        self.history = []
        self.focus = None
        self.needs_render = False
        self.browser = browser
        self.js = None

    def set_needs_render(self):
        self.needs_render = True
        self.browser.set_needs_animation_frame(self)

    def load(self, url, payload=None):
        headers, body = url.request(self.url, payload)
        self.url = url
        self.history.append(url)
        self.nodes = HTMLParser(body).parse()
        self.rules = DEFAULT_STYLE_SHEET.copy()
        if self.js: self.js.discarded = True
        self.js = JSContext(self)

        self.allowed_origins = None
        if "content-security-policy" in headers:
            csp = headers["content-security-policy"].split()
            if len(csp) > 0 and csp[0] == "default-src":
                self.allowed_origins = []
                for origin in csp[1:]:
                    self.allowed_origins.append(URL(origin).origin())

        # Get all the scripts and execute them in order
        scripts = [node.attributes["src"] for node
                   in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "script"
                   and "src" in node.attributes]
        for script in scripts:
            script_url = url.resolve(script)
            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP")
                continue
            try:
                header, body = script_url.request(url)
            except:
                continue
            task = Task(self.js.run, script_url, body)
            self.task_runner.schedule_task(task)

        # Get all the stylesheets and add them to the rules in order
        links = [node.attributes["href"] for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element)
            and node.tag == "link"
            and node.attributes.get("rel") == "stylesheet"
            and "href" in node.attributes]
        for link in links:
            style_url = url.resolve(link)
            if not self.allowed_request(style_url):
                print("Blocked stylesheet", link, "due to CSP")
                continue
            try:
                headers, body = style_url.request(url)
            except:
                continue
            self.rules.extend(CSSParser(body).parse())
        self.set_needs_render()
        self.render()

    def allowed_request(self, url):
        return self.allowed_origins == None or url.origin() in self.allowed_origins
    
    def render(self):
        if not self.needs_render: return
        if self.js and not self.js.discarded:
            self.js.interp.evaljs("__runRAFHandlers()")
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)
        self.needs_render = False
        self.browser.set_needs_raster_and_draw()

    def raster(self, canvas):
        for cmd in self.display_list:
            cmd.execute(canvas)

    def submit_form(self, elt):
        # Dispatch the submit event to the js runtime
        if self.js.dispatch_event("submit", elt): return
        # Find all the input elements of the form
        inputs = [node for node in tree_to_list(elt, [])
                  if isinstance(node, Element)
                  and node.tag == "input"
                  and "name" in node.attributes]
        
        # Encode the form data for the http request
        body = ""
        for input in inputs:
            name = input.attributes["name"]
            value = input.attributes.get("value", "")
            name = urllib.parse.quote(name)
            value = urllib.parse.quote(value)
            body += "&" + name + "=" + value
        body = body[1:]
        url = self.url.resolve(elt.attributes["action"])
        self.load(url, body)

    # Event handlers
    def scrolldown(self):
        max_y = max(self.document.height + 2*VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)

    def scrollup(self):
        if self.scroll > 0:
            self.scroll -= SCROLL_STEP

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def click(self, x, y): 
        self.render()
        if self.focus:
            self.focus.is_focused = False
        self.focus = None
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.document, [])
        if obj.x <= x < obj.x + obj.width
        and obj.y <= y < obj.y + obj.height]
        if not objs: return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                if self.js.dispatch_event("click", elt): return
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elif elt.tag == "input":
                if self.js.dispatch_event("click", elt): return
                elt.attributes["value"] = ""
                self.focus = elt
                elt.is_focused = True
                self.set_needs_render()
                return self.render()
            elif elt.tag == "button":
                if self.js.dispatch_event("click", elt): return
                while elt:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent
            elt = elt.parent 

    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event("keydown", self.focus): return
            self.focus.attributes["value"] += char
            self.set_needs_render()
            self.render()

def mainloop(browser):
    event = sdl2.SDL_Event()
    while True:
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                browser.handle_quit()
                sdl2.SDL_Quit()
                sys.exit()
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                if event.button.button == sdl2.SDL_BUTTON_LEFT:
                    browser.handle_click(event.button)
                elif event.button.button == sdl2.SDL_BUTTON_WHEELUP:
                    browser.handle_scrollup()
                elif event.button.button == sdl2.SDL_BUTTON_WHEELDOWN:
                    browser.handle_scrolldown()
            elif event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    browser.handle_scrolldown()
                elif event.key.keysym.sym == sdl2.SDLK_UP:
                    browser.handle_scrollup()
            elif event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode('utf8'))
        
        # Run the task runner
        browser.active_tab.task_runner.run()
        browser.raster_and_draw()
        browser.schedule_animation_frame()

if __name__ == "__main__":
    import sys
    url = sys.argv[1]
    if url is None:
        print("Usage: python browser.py <url>")
        sys.exit(1)

    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    browser.new_tab(URL(sys.argv[1]))
    mainloop(browser)



