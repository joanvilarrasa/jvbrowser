from url import URL, lex
import tkinter

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100

class Browser:
    def __init__(self):
        # Setup window
        # self.window_properties = {
        #     "width": WIDTH,
        #     "height": HEIGHT,
        # }
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
        )
        self.canvas.pack(fill=tkinter.BOTH, expand=True)

        # Setup content
        self.content = {
            "text": None,
            "display_list": [],
        }

        # Setup other state
        self.scroll = 0

        # Setup bindings
        self.window.bind("<Configure>", self.resize)
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<Button-4>", self.scrollup)
        self.window.bind("<Button-5>", self.scrolldown)

    def load(self, url):
        body = url.request()
        text = lex(body)
        self.content["text"] = text
        self.content["display_list"] = layout(self.content["text"], self.canvas.winfo_width())
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.content["display_list"]:
            if y > self.scroll + self.canvas.winfo_height(): continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)


    # Event handlers
    def scrolldown(self, e):
        self.scroll += SCROLL_STEP
        self.draw()

    def scrollup(self, e):
        if self.scroll > 0:
            self.scroll -= SCROLL_STEP
            self.draw()

    def resize(self, e):
        self.canvas.config(width=e.width, height=e.height)
        self.content["display_list"] = layout(self.content["text"], e.width)
        self.draw()


# Helpers
def layout(text, max_width):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if c == "\n":
            cursor_y += VSTEP * 1.5
            cursor_x = HSTEP
        elif cursor_x >= max_width - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP
    return display_list


if __name__ == "__main__":
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()
