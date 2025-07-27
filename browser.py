from emoji import EmojiProvider, is_emoji
from htmlparser import HTMLParser, print_tree
from url import URL
from layout import VSTEP, DocumentLayout, BlockLayout, paint_tree
import tkinter

WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100

class Browser:
    def __init__(self):
        # Setup window
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
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
        # print_tree(self.nodes)
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
