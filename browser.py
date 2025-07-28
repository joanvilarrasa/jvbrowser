from chrome import Chrome
from css.css_parser import CSSParser, style
from css.selectors import cascade_priority
from htmlparser import HTMLParser
from tag import Element
from text import Text
from url import URL
from layout.layout import HEIGHT, VSTEP, WIDTH, DocumentLayout, paint_tree
import tkinter

from utils import tree_to_list

SCROLL_STEP = 100
DEFAULT_STYLE_SHEET = CSSParser(open("css/default.css").read()).parse()

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
        self.chrome = Chrome(self)

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
        new_tab = Tab(HEIGHT - self.chrome.bottom)
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
            self.chrome.click(e.x, e.y)
        else:
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
        self.draw()
    def handle_key(self, e):
        if len(e.char) == 0: return
        if not (0x20 <= ord(e.char) < 0x7f): return
        self.chrome.keypress(e.char)
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

class Tab:
    def __init__(self, tab_height):
        # Setup content
        self.tab_height = tab_height
        self.url = None
        self.document = DocumentLayout(None)
        self.nodes = []
        self.display_list = []
        self.scroll = 0
        self.history = []

    def draw(self, canvas, offset):
        for cmd in self.display_list:
            if cmd.rect.top > self.scroll + self.tab_height:
                continue
            if cmd.rect.bottom < self.scroll: continue
            cmd.execute(self.scroll - offset, canvas)

    def load(self, url):
        self.url = url
        self.history.append(url)
        body = url.request()
        self.nodes = HTMLParser(body).parse()
        rules = DEFAULT_STYLE_SHEET.copy()
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
            rules.extend(CSSParser(body).parse())

        style(self.nodes, sorted(rules, key=cascade_priority))
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)

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
            elt = elt.parent



if __name__ == "__main__":
    import sys
    url = sys.argv[1]
    if url is None:
        print("Usage: python browser.py <url>")
        sys.exit(1)
    browser = Browser()
    browser.new_tab(URL(url))
    tkinter.mainloop()
