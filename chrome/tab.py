import urllib
from css.css_parser import CSSParser, style
from css.selectors import cascade_priority
from htmlparser import HTMLParser
from layout.block_layout import VSTEP, paint_tree
from layout.document_layout import DocumentLayout
from tag import Element
from text import Text
from utils import tree_to_list

SCROLL_STEP = 100
DEFAULT_STYLE_SHEET = CSSParser(open("css/default.css").read()).parse()

class Tab:
    def __init__(self, tab_height):
        # Setup content
        self.tab_height = tab_height
        self.url = None
        self.document = DocumentLayout(None)
        self.nodes = []
        self.rules = DEFAULT_STYLE_SHEET.copy()
        self.display_list = []
        self.scroll = 0
        self.history = []
        self.focus = None

    def load(self, url, payload=None):
        self.url = url
        self.history.append(url)
        body = url.request(payload)
        self.nodes = HTMLParser(body).parse()
        self.rules = DEFAULT_STYLE_SHEET.copy()
        links = [node.attributes["href"] for node in tree_to_list(self.nodes, [])
            if isinstance(node, Element)
            and node.tag == "link"
            and node.attributes.get("rel") == "stylesheet"
            and "href" in node.attributes]

        for link in links:
            style_url = url.resolve(link)
            try:
                body = style_url.request()
            except:
                continue
            self.rules.extend(CSSParser(body).parse())
        self.render()
    
    def render(self):
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)

    def draw(self, canvas, offset):
        for cmd in self.display_list:
            if cmd.rect.top > self.scroll + self.tab_height:
                continue
            if cmd.rect.bottom < self.scroll: continue
            cmd.execute(self.scroll - offset, canvas)

    def submit_form(self, elt):
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
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            elif elt.tag == "input":
                elt.attributes["value"] = ""
                self.focus = elt
                elt.is_focused = True
                return self.render()
            elif elt.tag == "button":
                while elt:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    elt = elt.parent
            elt = elt.parent 

    def keypress(self, char):
        if self.focus:
            self.focus.attributes["value"] += char
            self.render()