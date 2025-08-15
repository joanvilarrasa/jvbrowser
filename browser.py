import ctypes
import gzip
import math
import sdl2
import skia
import socket
import ssl
import threading
import urllib.parse
import time
import OpenGL.GL
import os
try:
    import gtts
    import playsound
    HAVE_TTS = True
except Exception:
    HAVE_TTS = False
from css.css_parser import CSSParser, style, INHERITED_PROPERTIES
from css.selectors import cascade_priority
from draw import DrawLine, DrawOutline, DrawRect, DrawText, contains_point, linespace, paint_tree, PaintCommand, VisualEffect, CompositedLayer, DrawCompositedLayer, local_to_absolute, Blend, parse_transform, map_translation
from font_cache import get_font
from htmltree.htmlparser import HTMLParser
from htmltree.tag import Element
from htmltree.text import Text
from accessibility import AccessibilityNode
from js.js_context import JSContext
from layout.block_layout import HEIGHT, VSTEP, WIDTH
from layout.document_layout import DocumentLayout
from task import Task, TaskRunner
<<<<<<< HEAD
from utils import tree_to_list, dpx
from accessibility import AccessibilityNode

SPEECH_FILE = "/tmp/speech-fragment.mp3"

def speak_text(text):
    print("SPEAK:", text)
    if not HAVE_TTS:
        return
    try:
        tts = gtts.gTTS(text)
        tts.save(SPEECH_FILE)
        playsound.playsound(SPEECH_FILE)
        os.remove(SPEECH_FILE)
    except Exception:
        pass
=======
from utils import tree_to_list
from frame import Frame
>>>>>>> 3e07826 (Done with the project, pretty good book)

SCROLL_STEP = 100
DEFAULT_STYLE_SHEET = CSSParser(open("css/default.css").read()).parse()
REFRESH_RATE_SEC = .033
COOKIE_JAR = {}
MAX_REDIRECTS = 10

# Create a simple broken image placeholder
BROKEN_IMAGE = None
try:
    BROKEN_IMAGE = skia.Image.open("Broken_Image.png")
except:
    # Create a simple broken image if file doesn't exist
    surface = skia.Surface(100, 100)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorWHITE)
    paint = skia.Paint(Color=skia.ColorGRAY)
    canvas.drawRect(skia.Rect.MakeLTRB(0, 0, 100, 100), paint)
    paint = skia.Paint(Color=skia.ColorRED, StrokeWidth=3, Style=skia.Paint.kStroke_Style)
    canvas.drawLine(20, 20, 80, 80, paint)
    canvas.drawLine(80, 20, 20, 80, paint)
    BROKEN_IMAGE = surface.makeImageSnapshot()

class MeasureTime:
    def __init__(self):
        self.file = open("browser.trace", "w")
        # Start traceEvents array
        self.file.write('{"traceEvents": [')
        ts = time.time() * 1000000
        self.file.write(
            '{ "name": "process_name",' +
            '"ph": "M",' +
            '"ts": ' + str(ts) + ',' +
            '"pid": 1, "cat": "__metadata",' +
            '"args": {"name": "Browser"}}')
        self.file.flush()

    def time(self, name):
        ts = time.time() * 1000000
        self.file.write(
            ', { "ph": "B", "cat": "_",' +
            '"name": "' + name + '",' +
            '"ts": ' + str(ts) + ',' +
            '"pid": 1, "tid": 1}')
        self.file.flush()

    def stop(self, name):
        ts = time.time() * 1000000
        self.file.write(
            ', { "ph": "E", "cat": "_",' +
            '"name": "' + name + '",' +
            '"ts": ' + str(ts) + ',' +
            '"pid": 1, "tid": 1}')
        self.file.flush()

    def finish(self):
        self.file.write(']}')
        self.file.close()

class Browser:
    def __init__(self):
        self.dark_mode = False
        self.tabs = []
        self.active_tab = None
        self.chrome = Chrome(self, URL)
        self.url = None
        self.scroll = 0
        self.display_list = []
        self.focus = None
        self.animation_timer = None
        # Dirty bits for pipeline
        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False
        self.needs_animation_frame = True
        self.measure = MeasureTime()
        self.composited_layers = []
        self.draw_list = []
        self.composited_updates = {}
<<<<<<< HEAD
        # Accessibility state
        self.needs_accessibility = False
        self.accessibility_is_on = False
        self.accessibility_tree = None
        self.has_spoken_document = False
        self.tab_focus = None
        self.last_tab_focus = None
        self.focus_a11y_node = None
        self.pending_hover = None
        self.hovered_a11y_node = None
        self.needs_speak_hovered_node = False
        self.active_alerts = []
        self.spoken_alerts = []
        
=======
        self.root_frame_focused = True
        self.accessibility_tree = None
        self.lock = threading.Lock()

>>>>>>> 3e07826 (Done with the project, pretty good book)
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

        # Try GPU path; fall back to CPU surfaces if unavailable
        self.use_gpu = True
        try:
            self.sdl_window = sdl2.SDL_CreateWindow(
                b"Browser",
                sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
                WIDTH, HEIGHT, sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_OPENGL)

            self.gl_context = sdl2.SDL_GL_CreateContext(self.sdl_window)
            print(("OpenGL initialized: vendor={}," + 
                   "renderer={}").format(
                OpenGL.GL.glGetString(OpenGL.GL.GL_VENDOR),
                OpenGL.GL.glGetString(OpenGL.GL.GL_RENDERER)))

            self.skia_context = skia.GrDirectContext.MakeGL()
            if self.skia_context is None:
                raise RuntimeError("Skia GL context not available")

            self.root_surface = skia.Surface.MakeFromBackendRenderTarget(
                self.skia_context,
                skia.GrBackendRenderTarget(
                    WIDTH, HEIGHT, 0, 0,
                    skia.GrGLFramebufferInfo(0, OpenGL.GL.GL_RGBA8)),
                skia.kBottomLeft_GrSurfaceOrigin,
                skia.kRGBA_8888_ColorType,
                skia.ColorSpace.MakeSRGB())
            if self.root_surface is None:
                raise RuntimeError("Failed to create GPU root surface")

            self.chrome_surface = skia.Surface.MakeRenderTarget(
                self.skia_context, skia.Budgeted.kNo,
                skia.ImageInfo.MakeN32Premul(
                    WIDTH, math.ceil(self.chrome.bottom)))
            if self.chrome_surface is None:
                raise RuntimeError("Failed to create GPU chrome surface")
            self.tab_surface = None
        except Exception:
            # Fallback to CPU raster surfaces and non-GL window
            self.use_gpu = False
            try:
                # Clean up GL resources if partially created
                if hasattr(self, 'gl_context') and self.gl_context:
                    sdl2.SDL_GL_DeleteContext(self.gl_context)
                if hasattr(self, 'sdl_window') and self.sdl_window:
                    sdl2.SDL_DestroyWindow(self.sdl_window)
            except Exception:
                pass

            self.sdl_window = sdl2.SDL_CreateWindow(
                b"Browser",
                sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
                WIDTH, HEIGHT, sdl2.SDL_WINDOW_SHOWN)

            self.root_surface = skia.Surface.MakeRaster(
                skia.ImageInfo.Make(
                    WIDTH, HEIGHT,
                    ct=skia.kRGBA_8888_ColorType,
                    at=skia.kUnpremul_AlphaType))
            self.chrome_surface = skia.Surface(WIDTH, math.ceil(self.chrome.bottom))
            self.tab_surface = None

    def set_active_tab(self, tab):
        self.active_tab = tab
        task = Task(self.active_tab.set_dark_mode, self.dark_mode)
        self.active_tab.task_runner.schedule_task(task)
        self.set_needs_raster()

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        # Update active tab to re-style and re-render content
        if self.active_tab is not None:
            task = Task(self.active_tab.set_dark_mode, self.dark_mode)
            self.active_tab.task_runner.schedule_task(task)
        # Ensure chrome repaints as well
        self.set_needs_raster()

    def set_needs_draw(self):
        self.needs_draw = True

    def set_needs_raster(self):
        self.needs_raster = True
        self.needs_draw = True

    def set_needs_composite(self):
        self.needs_composite = True
        self.needs_raster = True
        self.needs_draw = True

    def set_needs_accessibility(self):
        if not self.accessibility_is_on:
            return
        self.needs_accessibility = True
        self.needs_draw = True

    def toggle_accessibility(self):
        self.accessibility_is_on = not self.accessibility_is_on
        self.set_needs_accessibility()

    # Tab management
    def new_tab(self, url):
        new_tab = Tab(self, HEIGHT - self.chrome.bottom)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
        self.set_needs_raster()
        self.composite_raster_and_draw()

    # Zoom controls
    def increment_zoom(self, increment):
        task = Task(self.active_tab.zoom_by, increment)
        self.active_tab.task_runner.schedule_task(task)

    def reset_zoom(self):
        task = Task(self.active_tab.reset_zoom)
        self.active_tab.task_runner.schedule_task(task)

    # Event handlers
    def handle_scrolldown(self):
        if self.root_frame_focused:
            self.active_tab.scrolldown()
            self.set_needs_raster()
        else:
            task = Task(self.active_tab.scrolldown)
            self.active_tab.task_runner.schedule_task(task)

    def handle_scrollup(self):
        if self.root_frame_focused:
            self.active_tab.scrollup()
            self.set_needs_raster()
        else:
            task = Task(self.active_tab.scrollup)
            self.active_tab.task_runner.schedule_task(task)

    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            self.focus = None
            self.chrome.click(e.x, e.y)
            self.set_needs_raster()
        else:
            self.focus = "content"
            self.chrome.blur()
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
            url = self.active_tab.url
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
            if self.active_tab.url != url:
                self.set_needs_composite()

    def handle_key(self, e):
        if len(e) == 0: return
        if not (0x20 <= ord(e) < 0x7f): return
        if self.chrome.keypress(e):
            self.set_needs_draw()
        elif self.focus == "content":
            self.active_tab.keypress(e)
            self.set_needs_draw()
            
    def handle_enter(self):
        self.chrome.enter()
        self.set_needs_composite()

    # Drawing
    def composite_raster_and_draw(self):
        if not (self.needs_composite or self.needs_raster or self.needs_draw or self.needs_accessibility):
            return
        self.measure.time('raster_and_draw')
        if self.needs_composite:
            self.composite()
            # After compositing, rebuild draw list
            self.paint_draw_list()
        if self.needs_raster:
            self.raster_chrome()
            self.raster_tab()
        if self.needs_draw:
            # Ensure draw list reflects any updated effects
            if self.composited_updates:
                # Use provided updates to avoid recompositing/raster
                # get_latest() will route Blend effects
                pass
            else:
                self.paint_draw_list()
            self.draw()
        if self.needs_accessibility:
            self.update_accessibility()
        # Clear flags
        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False
        self.composited_updates = {}
        self.measure.stop('raster_and_draw')

    def schedule_animation_frame(self):
        def callback():
            active_tab = self.active_tab
            task = Task(active_tab.run_animation_frame)
            active_tab.task_runner.schedule_task(task)
            self.animation_timer = None
            self.needs_animation_frame = False
        if self.needs_animation_frame and not self.animation_timer:
            self.animation_timer = threading.Timer(REFRESH_RATE_SEC, callback)
            self.animation_timer.start()

    def set_needs_animation_frame(self, tab):
        if tab == self.active_tab:
            self.needs_animation_frame = True

    def commit(self, tab, data):
        self.lock.acquire(blocking=True)
        self.active_tab = tab
        self.url = data.url
        self.scroll = data.scroll
        self.root_frame_focused = data.root_frame_focused
        self.display_list = data.display_list
        self.composited_updates = data.composited_updates
        self.accessibility_tree = data.accessibility_tree
        self.focus = data.focus
        self.lock.release()

    def raster_tab(self):
        if self.use_gpu:
            # Raster all composited layers (no painting to root yet)
            for layer in self.composited_layers:
                layer.raster()
        else:
            # CPU raster path
            canvas = self.tab_surface.getCanvas()
            canvas.clear(skia.ColorWHITE)
            for cmd in self.display_list:
                cmd.execute(canvas)

    def raster_chrome(self):
        canvas = self.chrome_surface.getCanvas()
        if self.dark_mode:
            background_color = skia.ColorBLACK
        else:
            background_color = skia.ColorWHITE
        canvas.clear(background_color)
        for cmd in self.chrome.paint():
            cmd.execute(canvas)

    def draw(self):
        canvas = self.root_surface.getCanvas()
        if self.dark_mode:
            canvas.clear(skia.ColorBLACK)
        else:
            canvas.clear(skia.ColorWHITE)

        tab_rect = skia.Rect.MakeLTRB(0, self.chrome.bottom, WIDTH, HEIGHT)
        tab_offset = self.chrome.bottom - self.scroll
        canvas.save()
        canvas.clipRect(tab_rect)
        canvas.translate(0, tab_offset)
        for item in self.draw_list:
            item.execute(canvas)
        canvas.restore()

        chrome_rect = skia.Rect.MakeLTRB(0, 0, WIDTH, self.chrome.bottom)
        canvas.save()
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)
        canvas.restore()

        if self.use_gpu:
            self.root_surface.flushAndSubmit()
            sdl2.SDL_GL_SwapWindow(self.sdl_window)
        else:
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
            sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)
            sdl2.SDL_UpdateWindowSurface(self.sdl_window)

    def composite(self):
        # Walk display list, gather paint commands
        all_commands = []
        for cmd in self.display_list:
            all_commands = tree_to_list(cmd, all_commands)
        paint_commands = [cmd for cmd in all_commands if isinstance(cmd, PaintCommand)]

        self.composited_layers = []
        for cmd in paint_commands:
            # Try to merge into an existing compatible layer; otherwise create a new layer
            placed = False
            cmd_abs = local_to_absolute(cmd, cmd.rect)
            for layer in reversed(self.composited_layers):
                # If overlapping with existing layer, force new layer
                if skia.Rect.Intersects(layer.absolute_bounds(), cmd_abs):
                    continue
                if layer.can_merge(cmd):
                    layer.add(cmd)
                    placed = True
                    break
            if not placed:
                layer = CompositedLayer(self.skia_context, cmd)
                self.composited_layers.append(layer)

    def paint_draw_list(self):
        self.draw_list = []
        new_effects = {}
        for composited_layer in self.composited_layers:
            current_effect = DrawCompositedLayer(composited_layer)
            if not composited_layer.display_items:
                continue
            parent = getattr(composited_layer.display_items[0], 'parent', None)
            while parent:
                new_parent = self.get_latest(parent)
                if new_parent in new_effects:
                    # Attach current_effect under existing cloned effect
                    new_effects[new_parent].children.append(current_effect)
                    break
                else:
                    if isinstance(new_parent, VisualEffect):
                        current_effect = new_parent.clone(current_effect)
                        new_effects[new_parent] = current_effect
                    parent = getattr(parent, 'parent', None)
            if not getattr(parent, 'parent', None):
                self.draw_list.append(current_effect)
        # Handle hover highlighting via accessibility tree
        if self.pending_hover and self.accessibility_tree:
            (x, y) = self.pending_hover
            # Account for scroll in page content space
            y += self.active_tab.scroll
            a11y_node = self.accessibility_tree.hit_test(x, y)
            if a11y_node:
                if (not self.hovered_a11y_node) or (a11y_node.node != self.hovered_a11y_node.node):
                    self.needs_speak_hovered_node = True
                self.hovered_a11y_node = a11y_node
            self.pending_hover = None
        if self.hovered_a11y_node:
            color = "white" if self.dark_mode else "black"
            for bound in getattr(self.hovered_a11y_node, 'bounds', []):
                self.draw_list.append(DrawOutline(bound, color, 2))

    def get_latest(self, effect):
        node = getattr(effect, 'node', None)
        if node in self.composited_updates and isinstance(effect, Blend):
            return self.composited_updates[node]
        return effect

    def handle_quit(self):
        if getattr(self, 'use_gpu', False):
            sdl2.SDL_GL_DeleteContext(self.gl_context)
        sdl2.SDL_DestroyWindow(self.sdl_window)
        # Finish tracing
        self.measure.finish()

    def go_back(self):
        if self.active_tab:
            self.active_tab.go_back()
            self.set_needs_composite()

    def focus_addressbar(self):
        self.chrome.focus_addressbar()
        self.set_needs_raster()

    def cycle_tabs(self):
        if not self.tabs: return
        if self.active_tab not in self.tabs: return
        active_idx = self.tabs.index(self.active_tab)
        new_active_idx = (active_idx + 1) % len(self.tabs)
        self.set_active_tab(self.tabs[new_active_idx])

    def handle_tab(self):
        self.focus = "content"
        task = Task(self.active_tab.advance_tab)
        self.active_tab.task_runner.schedule_task(task)

    def update_accessibility(self):
        if not self.accessibility_tree:
            return
        if not self.has_spoken_document:
            self.speak_document()
            self.has_spoken_document = True
        # Alerts: refresh spoken mapping when tree rebuilt
        self.active_alerts = [node for node in tree_to_list(self.accessibility_tree, []) if getattr(node, 'role', None) == 'alert']
        new_spoken_alerts = []
        for old_node in getattr(self, 'spoken_alerts', []):
            new_nodes = [node for node in tree_to_list(self.accessibility_tree, []) if node.node == old_node.node and getattr(node, 'role', None) == 'alert']
            if new_nodes:
                new_spoken_alerts.append(new_nodes[0])
        self.spoken_alerts = new_spoken_alerts if hasattr(self, 'spoken_alerts') else []
        for alert in self.active_alerts:
            if alert not in self.spoken_alerts:
                self.speak_node(alert, "New alert ")
                self.spoken_alerts.append(alert)
        if self.tab_focus and self.tab_focus != self.last_tab_focus:
            nodes = [node for node in tree_to_list(self.accessibility_tree, []) if node.node == self.tab_focus]
            if nodes:
                self.focus_a11y_node = nodes[0]
                self.speak_node(self.focus_a11y_node, "element focused ")
            self.last_tab_focus = self.tab_focus
        if self.needs_speak_hovered_node and self.hovered_a11y_node:
            self.speak_node(self.hovered_a11y_node, "Hit test ")
        self.needs_speak_hovered_node = False
        # Reset flag
        self.needs_accessibility = False

    def speak_document(self):
        text = "Here are the document contents: "
        tree_list = tree_to_list(self.accessibility_tree, [])
        for accessibility_node in tree_list:
            new_text = getattr(accessibility_node, 'text', '')
            if new_text:
                text += "\n" + new_text
        speak_text(text)

    def speak_node(self, node, text):
        t = text + getattr(node, 'text', '')
        if t and node.children and node.children[0].role == "StaticText":
            t += " " + node.children[0].text
        if t:
            speak_text(t)

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
    
    def request(self, referrer, payload=None, binary=False):
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
        response = s.makefile("b")
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
        if binary:
            content = self.get_response_content_binary(response, response_headers)
        else:
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

    def get_response_content_binary(self, response, response_headers):
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
            content = gzip.decompress(raw_content)
        else:
            content = raw_content
        
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

        # Colors based on dark mode
        if self.browser.dark_mode:
            fg = "white"
            bg = "black"
        else:
            fg = "black"
            bg = "white"

        # Paint background
        cmds.append(DrawRect(
            skia.Rect.MakeXYWH(0, 0, WIDTH, self.bottom),
            bg))
        cmds.append(DrawLine(
            0, self.bottom, WIDTH,
            self.bottom, fg, 1))

        cmds.append(DrawOutline(self.newtab_rect, fg, 1))

        # Paint tabs bar new tab button
        cmds.append(DrawText(
            self.newtab_rect.left() + self.padding,
            self.newtab_rect.top(),
            "+", self.font, fg))

        # Paint tabs bar tabs
        for i, tab in enumerate(self.browser.tabs):
            bounds = self.tab_rect(i)
            cmds.append(DrawLine(
                bounds.left(), 0, bounds.left(), bounds.bottom(),
                fg, 1))
            cmds.append(DrawLine(
                bounds.right(), 0, bounds.right(), bounds.bottom(),
                fg, 1))
            cmds.append(DrawText(
                bounds.left() + self.padding, bounds.top() + self.padding,
                "Tab {}".format(i), self.font, fg))

            if tab == self.browser.active_tab:
                cmds.append(DrawLine(
                    0, bounds.bottom(), bounds.left(), bounds.bottom(),
                    fg, 1))
                cmds.append(DrawLine(
                    bounds.right(), bounds.bottom(), WIDTH, bounds.bottom(),
                    fg, 1))

        # Paint url bar back button
        cmds.append(DrawOutline(self.back_rect, fg, 1))
        cmds.append(DrawText(
            self.back_rect.left() + self.padding,
            self.back_rect.top(),
            "<", self.font, fg))

        # Paint url bar address
        cmds.append(DrawOutline(self.address_rect, fg, 1))
        url = str(self.browser.active_tab.url)
        if self.focus == "address bar":
            cmds.append(DrawText(
                self.address_rect.left() + self.padding,
                self.address_rect.top(),
                self.address_bar, self.font, fg))
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
                url, self.font, fg))

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
                    self.browser.set_active_tab(tab)
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

<<<<<<< HEAD
    def focus_addressbar(self):
        self.focus = "address bar"
        self.address_bar = ""
=======
class CommitData:
    def __init__(self, url, scroll, root_frame_focused, height,
        display_list, composited_updates, accessibility_tree, focus):
        self.url = url
        self.scroll = scroll
        self.root_frame_focused = root_frame_focused
        self.height = height
        self.display_list = display_list
        self.composited_updates = composited_updates
        self.accessibility_tree = accessibility_tree
        self.focus = focus
>>>>>>> 3e07826 (Done with the project, pretty good book)

class Tab:
    def __init__(self, browser, tab_height):
        # Setup content
        self.browser = browser
        self.task_runner = TaskRunner(self)
        self.tab_height = tab_height
        self.history = []
        self.root_frame = None
        self.window_id_to_frame = {}
        self.focus = None
        self.focused_frame = None
        self.needs_accessibility = False
        self.needs_paint = False
<<<<<<< HEAD
        self.browser = browser
        self.js = None
        self.composited_updates = []
        self.zoom = 1
        self.dark_mode = browser.dark_mode
        self.needs_focus_scroll = False
        # Accessibility state
        self.accessibility_tree = None
=======
        self.display_list = []
        self.origin_to_js = {}
        self.accessibility_tree = None
        self.zoom = 1.0
>>>>>>> 3e07826 (Done with the project, pretty good book)

    def set_needs_render(self):
        if self.root_frame:
            self.root_frame.set_needs_render()

    def set_needs_layout(self):
        if self.root_frame:
            self.root_frame.set_needs_layout()

    def set_needs_paint(self):
        if self.root_frame:
            self.root_frame.set_needs_paint()

    def set_needs_accessibility(self):
        self.needs_accessibility = True
        self.browser.set_needs_animation_frame(self)

<<<<<<< HEAD
    def load(self, url, payload=None):
        self.focus = None
        self.zoom = 1
        headers, body = url.request(self.url, payload)
        self.url = url
        self.history.append(url)
        self.nodes = HTMLParser(body).parse()
        self.rules = DEFAULT_STYLE_SHEET.copy()
        if self.js: self.js.discarded = True
        self.js = JSContext(self)
=======
    def set_needs_render_all_frames(self):
        for id, frame in self.window_id_to_frame.items():
            frame.set_needs_render()
>>>>>>> 3e07826 (Done with the project, pretty good book)

    def get_js(self, url):
        origin = url.origin()
        if origin not in self.origin_to_js:
            self.origin_to_js[origin] = JSContext(self, origin)
        return self.origin_to_js[origin]

    def zoom_by(self, increment):
        self.zoom = max(0.1, min(5.0, self.zoom + increment))
        for id, frame in self.window_id_to_frame.items():
            frame.document.zoom.mark()
        self.set_needs_render()

    def reset_zoom(self):
        self.zoom = 1.0
        for id, frame in self.window_id_to_frame.items():
            frame.document.zoom.mark()
        self.set_needs_render()

    def post_message(self, message, target_window_id):
        frame = self.window_id_to_frame[target_window_id]
        frame.js.dispatch_post_message(message, target_window_id)

    def load(self, url, payload=None):
        self.history.append(url)
        self.root_frame = Frame(self, None, None)
        self.root_frame.frame_width = WIDTH
        self.root_frame.frame_height = self.tab_height
        self.root_frame.load(url, payload)

    def allowed_request(self, url):
        if self.root_frame:
            return self.root_frame.allowed_request(url)
        return True

    def render(self):
        self.browser.measure.time('render')

        for id, frame in self.window_id_to_frame.items():
            if frame.loaded:
                frame.render()

<<<<<<< HEAD
        if self.needs_style:
            # Adjust default color based on dark mode
            if self.dark_mode:
                INHERITED_PROPERTIES["color"] = "white"
            else:
                INHERITED_PROPERTIES["color"] = "black"
            style(self.nodes, sorted(self.rules, key=cascade_priority), self)
            self.needs_layout = True
            self.needs_style = False
            style_ran = True

        if self.needs_layout:
            self.document = DocumentLayout(self.nodes)
            self.document.layout(self.zoom)
            self.needs_accessibility = True
            self.needs_paint = True
            self.needs_layout = False
            layout_ran = True
=======
        if self.needs_accessibility:
            self.accessibility_tree = AccessibilityNode(self.root_frame.nodes)
            self.needs_accessibility = False
>>>>>>> 3e07826 (Done with the project, pretty good book)

        if self.needs_accessibility:
            self.accessibility_tree = AccessibilityNode(self.nodes)
            self.accessibility_tree.build()
            self.needs_accessibility = False

        if self.needs_paint:
            self.display_list = []
            paint_tree(self.root_frame.document, self.display_list)
            self.needs_paint = False

        self.browser.measure.stop('render')

    def run_animation_frame(self, scroll):
        # Run RAF handlers first
        for (window_id, frame) in self.window_id_to_frame.items():
            if not frame.loaded:
                continue
            frame.js.dispatch_RAF(frame.window_id)

        # Drive CSS transitions: update active animations and request layout-only
        updated = False
        for (window_id, frame) in self.window_id_to_frame.items():
            if not frame.loaded:
                continue
            for node in tree_to_list(frame.nodes, []):
                animations = getattr(node, 'animations', {})
                for (prop, animation) in list(animations.items()):
                    value = animation.animate()
                    if value is not None:
                        node.style[prop].set(value)
                        updated = True
                        frame.composited_updates.append(node)
                    else:
                        # Animation finished
                        del animations[prop]
        
        # If we updated only composited properties (like opacity), avoid layout
        needs_composite = any(frame.needs_style or frame.needs_layout 
                             for frame in self.window_id_to_frame.values() if frame.loaded)
        if updated:
            self.set_needs_paint()
        
        for id, frame in self.window_id_to_frame.items():
            if frame.loaded:
                frame.render()
        
        if updated and not needs_composite:
            # Provide updated effects to the browser to skip composite/raster
            updates = {}
            for frame in self.window_id_to_frame.values():
                if frame.loaded:
                    for node in frame.composited_updates:
                        if hasattr(node, 'blend_op'):
                            updates[node] = node.blend_op
            self.browser.composited_updates = updates
            for frame in self.window_id_to_frame.values():
                if frame.loaded:
                    frame.composited_updates = []
            self.browser.set_needs_draw()
        
        # Create commit data for browser thread
        root_frame_focused = not self.focused_frame or \
                self.focused_frame == self.root_frame
        commit_data = CommitData(
            self.root_frame.url if self.root_frame else None,
            self.root_frame.scroll if self.root_frame else 0,
            root_frame_focused,
            self.tab_height,
            self.display_list,
            self.browser.composited_updates,
            self.accessibility_tree,
            self.focus
        )
        self.browser.commit(self, commit_data)

        if getattr(self, 'needs_focus_scroll', False) and self.focus:
            self.scroll_to(self.focus)
        self.needs_focus_scroll = False
        # Send accessibility tree and focus to browser
        if getattr(self, 'accessibility_tree', None) is not None:
            self.browser.accessibility_tree = self.accessibility_tree
            self.browser.tab_focus = self.focus
            # trigger accessibility update
            self.browser.set_needs_accessibility()
            # clear to avoid races; will be rebuilt if needed
            self.accessibility_tree = None

    def raster(self, canvas):
        for cmd in self.display_list:
            cmd.execute(canvas)

    def submit_form(self, elt):
        if self.root_frame:
            self.root_frame.submit_form(elt)

    # Event handlers
    def scrolldown(self):
<<<<<<< HEAD
        max_y = max(self.document.height + 2*dpx(VSTEP, self.zoom) - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
=======
        frame = self.focused_frame or self.root_frame
        frame.scrolldown()
        self.set_needs_paint()
>>>>>>> 3e07826 (Done with the project, pretty good book)

    def scrollup(self):
        frame = self.focused_frame or self.root_frame
        frame.scrollup()
        self.set_needs_paint()

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def click(self, x, y): 
        self.render()
<<<<<<< HEAD
        if self.focus:
            self.focus.is_focused = False
        self.focus = None
        y += self.scroll
        # Hit testing with transforms: compute absolute bounds
        loc_rect = skia.Rect.MakeXYWH(x, y, 1, 1)
        def absolute_bounds_for_obj(obj):
            rect = skia.Rect.MakeXYWH(obj.x, obj.y, obj.width, obj.height)
            cur = obj.node
            while cur:
                rect = map_translation(rect, parse_transform(cur.style.get("transform", "")))
                cur = getattr(cur, 'parent', None)
            return rect
        objs = [obj for obj in tree_to_list(self.document, [])
                if absolute_bounds_for_obj(obj).intersects(loc_rect)]
        if not objs: return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif isinstance(elt, Element) and is_focusable(elt):
                self.focus_element(elt)
                if self.js and self.js.dispatch_event("click", elt): return
                self.activate_element(elt)
                return
            elt = elt.parent 

    def keypress(self, char):
        if self.focus and getattr(self.focus, 'tag', None) == "input":
            if "value" not in self.focus.attributes:
                self.activate_element(self.focus)
            if self.js and self.js.dispatch_event("keydown", self.focus): return
            self.focus.attributes["value"] += char
            self.set_needs_render()
            self.render()
=======
        self.root_frame.click(x, y)

    def keypress(self, char):
        frame = self.focused_frame or self.root_frame
        frame.keypress(char)

    def advance_tab(self):
        frame = self.focused_frame or self.root_frame
        frame.advance_tab()
>>>>>>> 3e07826 (Done with the project, pretty good book)

    # Zoom operations
    def zoom_by(self, increment):
        if increment:
            self.zoom *= 1.1
            self.scroll *= 1.1
        else:
            self.zoom *= 1/1.1
            self.scroll *= 1/1.1
        self.set_needs_render()

    def reset_zoom(self):
        if self.zoom != 1:
            self.scroll /= self.zoom
            self.zoom = 1
            self.set_needs_render()

    # Dark mode operations
    def set_dark_mode(self, val):
        self.dark_mode = val
        self.set_needs_render()

    def focus_element(self, node):
        if self.focus:
            self.focus.is_focused = False
        self.focus = node
        if node:
            node.is_focused = True
            # mark to scroll into view
            self.needs_focus_scroll = True

    def enter(self):
        if not self.focus: return
        if self.js and self.js.dispatch_event("click", self.focus): return
        self.activate_element(self.focus)

    def activate_element(self, elt):
        if isinstance(elt, Text):
            return
        if elt.tag == "input":
            elt.attributes["value"] = ""
            self.set_needs_render()
        elif elt.tag == "a" and "href" in elt.attributes:
            url = self.url.resolve(elt.attributes["href"])
            self.load(url)
        elif elt.tag == "button":
            cur = elt
            while cur:
                if cur.tag == "form" and "action" in cur.attributes:
                    self.submit_form(cur)
                    break
                cur = cur.parent

    def advance_tab(self):
        focusable_nodes = [node for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element) and is_focusable(node)]
        focusable_nodes.sort(key=get_tabindex)
        if self.focus in focusable_nodes:
            idx = focusable_nodes.index(self.focus) + 1
        else:
            idx = 0
        if idx < len(focusable_nodes):
            self.focus_element(focusable_nodes[idx])
        else:
            self.focus_element(None)
            self.browser.focus_addressbar()
        self.set_needs_render()

    def scroll_to(self, elt):
        objs = [obj for obj in tree_to_list(self.document, []) if getattr(obj, 'node', None) == self.focus]
        if not objs: return
        obj = objs[0]
        # If already in view, do nothing
        if self.scroll < obj.y < self.scroll + self.tab_height:
            return
        max_y = max(self.document.height + 2*dpx(VSTEP, self.zoom) - self.tab_height, 0)
        new_scroll = obj.y - SCROLL_STEP
        self.scroll = self.clamp_scroll(new_scroll, max_y)

    def clamp_scroll(self, val, max_y=None):
        if max_y is None:
            max_y = max(self.document.height + 2*dpx(VSTEP, self.zoom) - self.tab_height, 0)
        if val < 0:
            return 0
        if val > max_y:
            return max_y
        return val

def mainloop(browser):
    event = sdl2.SDL_Event()
    ctrl_down = False
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
            elif event.type == sdl2.SDL_MOUSEMOTION:
                browser.handle_hover(event.motion)
            elif event.type == sdl2.SDL_KEYDOWN:
                if ctrl_down:
                    if event.key.keysym.sym == sdl2.SDLK_EQUALS:
                        browser.increment_zoom(True)
                    elif event.key.keysym.sym == sdl2.SDLK_MINUS:
                        browser.increment_zoom(False)
                    elif event.key.keysym.sym == sdl2.SDLK_0:
                        browser.reset_zoom()
                    elif event.key.keysym.sym == sdl2.SDLK_d:
                        browser.toggle_dark_mode()
                    elif event.key.keysym.sym == sdl2.SDLK_a:
                        browser.toggle_accessibility()
                    elif event.key.keysym.sym == sdl2.SDLK_LEFT:
                        browser.go_back()
                    elif event.key.keysym.sym == sdl2.SDLK_l:
                        browser.focus_addressbar()
                    elif event.key.keysym.sym == sdl2.SDLK_t:
                        browser.new_tab(URL("https://browser.engineering/"))
                    elif event.key.keysym.sym == sdl2.SDLK_TAB:
                        browser.cycle_tabs()
                    elif event.key.keysym.sym == sdl2.SDLK_q:
                        browser.handle_quit()
                        sdl2.SDL_Quit()
                        sys.exit()
                        break
                if event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    browser.handle_scrolldown()
                elif event.key.keysym.sym == sdl2.SDLK_UP:
                    browser.handle_scrollup()
                elif event.key.keysym.sym == sdl2.SDLK_TAB:
                    browser.handle_tab()
                elif event.key.keysym.sym == sdl2.SDLK_RCTRL or \
                    event.key.keysym.sym == sdl2.SDLK_LCTRL:
                    ctrl_down = True
            elif event.type == sdl2.SDL_KEYUP:
                if event.key.keysym.sym == sdl2.SDLK_RCTRL or \
                    event.key.keysym.sym == sdl2.SDLK_LCTRL:
                    ctrl_down = False
            elif event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode('utf8'))
        
        # Run the task runner
        browser.active_tab.task_runner.run()
        browser.composite_raster_and_draw()
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



