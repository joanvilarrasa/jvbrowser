import math
import skia
import urllib.parse
from css.css_parser import CSSParser, style, dirty_style
from css.selectors import cascade_priority
from draw import paint_tree, map_translation, parse_transform
from font_cache import get_font
from htmltree.htmlparser import HTMLParser
from htmltree.tag import Element
from htmltree.text import Text
from js.js_context import JSContext
from layout.block_layout import SCROLL_STEP, VSTEP, BlockLayout
from layout.document_layout import DocumentLayout
from layout.embed_layout import dpx
from task import Task
from utils import tree_to_list

def is_focusable(node):
    if isinstance(node, Text):
        return False
    elif node.tag == "input":
        return True
    elif node.tag == "button":
        return True
    elif node.tag == "a" and "href" in node.attributes:
        return True
    elif "contenteditable" in node.attributes:
        return True
    else:
        return False

DEFAULT_STYLE_SHEET = CSSParser(open("css/default.css").read()).parse()

class Frame:
    def __init__(self, tab, parent_frame, frame_element):
        self.tab = tab
        self.parent_frame = parent_frame
        self.frame_element = frame_element
        self.loaded = False
        self.window_id = len(self.tab.window_id_to_frame)
        self.tab.window_id_to_frame[self.window_id] = self
        
        # Content
        self.url = None
        self.document = DocumentLayout(None)
        self.nodes = []
        self.rules = DEFAULT_STYLE_SHEET.copy()
        self.display_list = []
        self.scroll = 0
        self.focus = None
        self.needs_style = False
        self.needs_layout = False
        self.needs_paint = False
        self.js = None
        self.composited_updates = []
        self.frame_width = 0
        self.frame_height = 0

    def set_needs_render(self):
        self.needs_style = True
        self.tab.set_needs_accessibility()
        self.tab.set_needs_paint()

    def set_needs_layout(self):
        self.needs_layout = True
        self.tab.set_needs_accessibility()
        self.tab.set_needs_paint()

    def set_needs_paint(self):
        self.needs_paint = True
        self.tab.set_needs_paint()

    def load(self, url, payload=None):
        self.loaded = False
        headers, body = url.request(self.url, payload)
        body = body.decode("utf8", "replace")
        self.url = url
        self.nodes = HTMLParser(body).parse()
        self.rules = DEFAULT_STYLE_SHEET.copy()
        if self.js: self.js.discarded = True
        self.js = self.tab.get_js(url)
        self.js.add_window(self)

        self.allowed_origins = None
        if "content-security-policy" in headers:
            csp = headers["content-security-policy"].split()
            if len(csp) > 0 and csp[0] == "default-src":
                self.allowed_origins = []
                for origin in csp[1:]:
                    self.allowed_origins.append(url.resolve(origin).origin())

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
                body = body.decode("utf8", "replace")
            except:
                continue
            task = Task(self.js.run, script_url, body, self.window_id)
            self.tab.task_runner.schedule_task(task)

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
                body = body.decode("utf8", "replace")
            except:
                continue
            self.rules.extend(CSSParser(body).parse())
        
        # Download images
        images = [node
            for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element)
            and node.tag == "img"]
        for img in images:
            src = img.attributes.get("src", "")
            image_url = url.resolve(src)
            assert self.allowed_request(image_url), \
                "Blocked load of " + str(image_url) + " due to CSP"
            try:
                header, body = image_url.request(url, binary=True)
                img.encoded_data = body
                data = skia.Data.MakeWithoutCopy(body)
                img.image = skia.Image.MakeFromEncoded(data)
            except Exception as e:
                print("Image", img.attributes.get("src", ""),
                    "crashed", e)
                img.image = self.tab.browser.BROKEN_IMAGE

        # Load iframes
        iframes = [node
                   for node in tree_to_list(self.nodes, [])
                   if isinstance(node, Element)
                   and node.tag == "iframe"
                   and "src" in node.attributes]
        for iframe in iframes:
            document_url = url.resolve(iframe.attributes["src"])
            if not self.allowed_request(document_url):
                print("Blocked iframe", document_url, "due to CSP")
                iframe.frame = None
                continue
            iframe.frame = Frame(self.tab, self, iframe)
            task = Task(iframe.frame.load, document_url)
            self.tab.task_runner.schedule_task(task)
        
        # Create the document layout once
        self.document = DocumentLayout(self.nodes, self)
        self.set_needs_render()
        self.render()
        self.loaded = True

    def allowed_request(self, url):
        return self.allowed_origins == None or url.origin() in self.allowed_origins

    def render(self):
        self.tab.browser.measure.time('render')

        style_ran = False
        layout_ran = False
        paint_ran = False

        if self.needs_style:
            style(self.nodes, sorted(self.rules, key=cascade_priority), self)
            self.needs_layout = True
            self.needs_style = False
            style_ran = True

        if self.needs_layout:
            self.document.layout(self.frame_width, self.tab.zoom)
            self.needs_paint = True
            self.needs_layout = False
            layout_ran = True

        if self.needs_paint:
            self.display_list = []
            paint_tree(self.document, self.display_list)
            self.needs_paint = False
            paint_ran = True

        # After render steps complete, set appropriate browser flags
        if style_ran:
            self.tab.browser.set_needs_composite()
        elif layout_ran:
            self.tab.browser.set_needs_raster()
        elif paint_ran:
            self.tab.browser.set_needs_draw()

        self.tab.browser.measure.stop('render')

    def click(self, x, y):
        self.render()
        if self.focus:
            self.focus.is_focused = False
        self.focus = None
        y += self.scroll
        # Hit testing with transforms: compute absolute bounds
        loc_rect = skia.Rect.MakeXYWH(x, y, 1, 1)
        def absolute_bounds_for_obj(obj):
            rect = skia.Rect.MakeXYWH(obj.x.get(), obj.y.get(), obj.width.get(), obj.height.get())
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
            elif elt.tag == "a" and "href" in elt.attributes:
                if self.js.dispatch_event("click", elt, self.window_id): return
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elif elt.tag == "input":
                if self.js.dispatch_event("click", elt, self.window_id): return
                elt.attributes["value"] = ""
                self.focus_element(elt)
                return self.render()
            elif "contenteditable" in elt.attributes:
                if self.js.dispatch_event("click", elt, self.window_id): return
                self.focus_element(elt)
                return self.render()
            elif elt.tag == "button":
                if self.js.dispatch_event("click", elt, self.window_id): return
                while elt:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent
            elif elt.tag == "iframe":
                abs_bounds = absolute_bounds_for_obj(elt.layout_object)
                border = dpx(1, elt.layout_object.zoom)
                new_x = x - abs_bounds.left() - border
                new_y = y - abs_bounds.top() - border
                elt.frame.click(new_x, new_y)
                return
            elt = elt.parent

    def keypress(self, char):
        if self.focus:
            if self.js.dispatch_event("keydown", self.focus, self.window_id): return
            if self.focus.tag == "input":
                self.focus.attributes["value"] += char
            elif "contenteditable" in self.focus.attributes:
                text_nodes = [
                   t for t in tree_to_list(self.focus, [])
                   if isinstance(t, Text)
                ]
                if text_nodes:
                    last_text = text_nodes[-1]
                else:
                    last_text = Text("", self.focus)
                    self.focus.children.append(last_text)
                last_text.text += char
                obj = self.focus.layout_object
                while not isinstance(obj, BlockLayout):
                    obj = obj.parent
                obj.children.mark()
            self.set_needs_render()
            self.render()

    def submit_form(self, elt):
        # Dispatch the submit event to the js runtime
        if self.js.dispatch_event("submit", elt, self.window_id): return
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

    def focus_element(self, node):
        if self.tab.focused_frame and self.tab.focused_frame != self:
            self.tab.focused_frame.set_needs_render()
        self.tab.focused_frame = self
        if self.focus:
            self.focus.is_focused = False
            dirty_style(self.focus)
        if node:
            node.is_focused = True
            dirty_style(node)
        self.focus = node
        self.set_needs_render()

    def advance_tab(self):
        # Find all focusable elements
        focusable = []
        for node in tree_to_list(self.nodes, []):
            if isinstance(node, Element):
                if node.tag == "input":
                    focusable.append(node)
                elif node.tag == "button":
                    focusable.append(node)
                elif node.tag == "a" and "href" in node.attributes:
                    focusable.append(node)
                elif "contenteditable" in node.attributes:
                    focusable.append(node)
        
        if not focusable:
            return
        
        # Find current focus index
        if self.focus in focusable:
            current_index = focusable.index(self.focus)
            next_index = (current_index + 1) % len(focusable)
        else:
            next_index = 0
        
        # Focus next element
        self.focus_element(focusable[next_index])

    def scrolldown(self):
        self.scroll = self.clamp_scroll(self.scroll + SCROLL_STEP)

    def scrollup(self):
        self.scroll = self.clamp_scroll(self.scroll - SCROLL_STEP)

    def clamp_scroll(self, scroll):
        height = math.ceil(self.document.height.get() + 2*VSTEP)
        maxscroll = height - self.frame_height
        return max(0, min(scroll, maxscroll))

    def scroll_to(self, elt):
        # Find the layout object for this element
        for obj in tree_to_list(self.document, []):
            if obj.node == elt:
                # Scroll to make this element visible
                new_scroll = obj.y - self.frame_height / 3
                self.scroll = self.clamp_scroll(new_scroll)
                break
