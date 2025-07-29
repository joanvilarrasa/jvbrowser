import tkinter
from chrome.chrome import Chrome
from chrome.tab import Tab
from css.css_parser import CSSParser
from layout.block_layout import HEIGHT, WIDTH
from url import URL

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
            
if __name__ == "__main__":
    import sys
    url = sys.argv[1]
    if url is None:
        print("Usage: python browser.py <url>")
        sys.exit(1)
    browser = Browser()
    browser.new_tab(URL(url))
    tkinter.mainloop()
