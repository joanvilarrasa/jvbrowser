from css.css_parser import CSSParser, style
from css.selectors import cascade_priority
from htmlparser import HTMLParser
from tag import Element
from url import URL
from layout import HEIGHT, VSTEP, WIDTH, DocumentLayout, paint_tree
import tkinter

from utils import tree_to_list

SCROLL_STEP = 100
DEFAULT_STYLE_SHEET = CSSParser(open("css/default.css").read()).parse()

class Browser:
    def __init__(self):
        # Setup window
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
            bg="white"
        )
        self.canvas.pack(fill=tkinter.BOTH, expand=True)

        # Setup content
        self.document = DocumentLayout(None)
        self.nodes = []
        self.display_list = []
        self.scroll_y = 0

        # Setup bindings
        self.window.bind("<Configure>", self.resize)
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<Button-4>", self.scrollup)
        self.window.bind("<Button-5>", self.scrolldown)

    def draw(self):
        self.canvas.delete("all")
        for cmd in self.display_list:
            if cmd.top > self.scroll_y + HEIGHT: continue
            if cmd.bottom < self.scroll_y: continue
            cmd.execute(self.scroll_y, self.canvas)

    def load(self, url):
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
        # paint_tree(self.document, self.display_list)
        self.draw()

    # Event handlers
    def scrolldown(self, e):
        max_y = max(self.document.height + 2*VSTEP - HEIGHT, 0)
        self.scroll_y = min(self.scroll_y + SCROLL_STEP, max_y)
        self.draw()

    def scrollup(self, e):
        if self.scroll_y > 0:
            self.scroll_y -= SCROLL_STEP
            self.draw()

    def resize(self, e):
        self.canvas.config(width=e.width, height=e.height)
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)
        self.draw()



if __name__ == "__main__":
    import sys
    url = sys.argv[1]
    if url is None:
        print("Usage: python browser.py <url>")
        sys.exit(1)
    browser = Browser()
    browser.load(URL(url))
    tkinter.mainloop()
