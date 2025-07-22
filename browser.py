from emoji import EmojiProvider, is_emoji
from htmlparser import HTMLParser, print_tree
from url import URL
from layout import Layout
import tkinter

WIDTH, HEIGHT = 800, 600
SCROLL_STEP = 100

class Browser:
    def __init__(self):
        # Setup window
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
        self.scroll = {
            "value": 0,
            "max": 0,
            "show": False,
            "bar_width": 10,
        }
        self.layout_config = {
            "text_direction": "ltr",    # ltr, rtl
            "text_align": "left",       # left, right
        }

        # Setup providers
        self.emoji_provider = EmojiProvider()

        # Setup bindings
        self.window.bind("<Configure>", self.resize)
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<Button-4>", self.scrollup)
        self.window.bind("<Button-5>", self.scrolldown)

    def draw(self):
        self.canvas.delete("all")
        for x, y, text, font in self.content["display_list"]:
            if y > self.scroll["value"] + self.canvas.winfo_height(): continue
            if y + font.metrics("linespace") * 1.25 < self.scroll["value"]: continue

            # Check if character is an emoji
            if len(text) == 1:
                if is_emoji(text[0]):
                    emoji_image = self.emoji_provider.load_emoji_image(text[0])
                    if emoji_image:
                        self.canvas.create_image(x, y - self.scroll["value"], image=emoji_image, anchor='nw')
                    else:
                        self.canvas.create_text(x, y - self.scroll["value"], text=text, font=font, anchor='nw')
                else:
                    self.canvas.create_text(x, y - self.scroll["value"], text=text, font=font, anchor='nw')
            else:
                self.canvas.create_text(x, y - self.scroll["value"], text=text, font=font, anchor='nw')

        if self.scroll["show"]:
            bar_height = self.canvas.winfo_height() * self.canvas.winfo_height() / self.scroll["max"]
            bar_y = self.scroll["value"] * (self.canvas.winfo_height() - bar_height) / self.scroll["max"]
            self.canvas.create_rectangle(
                self.canvas.winfo_width() - self.scroll["bar_width"],
                bar_y,
                self.canvas.winfo_width(),
                bar_y + bar_height,
                fill="#f6c198",
                outline="#f6c198",
            )

    def load(self, url):
        body = url.request()
        self.content["nodes"] = HTMLParser(body).parse()
        print_tree(self.content["nodes"])
        self.content["display_list"] = Layout(
            self.content["nodes"], 
            self.canvas.winfo_width() - self.scroll["bar_width"],
            self.layout_config["text_direction"],
            self.layout_config["text_align"]
        ).display_list
        if len(self.content["display_list"]) > 0:
            self.scroll["max"] = self.content["display_list"][-1][1]
        else:
            self.scroll["max"] = 0
        self.draw()

    # Event handlers
    def scrolldown(self, e):
        if self.scroll["value"] < self.scroll["max"]:
            self.scroll["value"] += SCROLL_STEP
            self.draw()

    def scrollup(self, e):
        if self.scroll["value"] > 0:
            self.scroll["value"] -= SCROLL_STEP
            self.draw()

    def resize(self, e):
        self.canvas.config(width=e.width, height=e.height)
        self.content["display_list"] = Layout(
            self.content["nodes"], 
            e.width - self.scroll["bar_width"],
            self.layout_config["text_direction"],
            self.layout_config["text_align"]
        ).display_list
        if len(self.content["display_list"]) > 0:
            self.scroll["max"] = self.content["display_list"][-1][1] - self.canvas.winfo_height()
        else:
            self.scroll["max"] = 0
        self.scroll["show"] = self.scroll["max"] > 0
        self.draw()



if __name__ == "__main__":
    import sys

    # Default values
    text_direction = "ltr"
    text_align = "left"
    url = None

    # Parse command line arguments
    args = sys.argv[1:]
    url = None
    for arg in args:
        if arg.startswith("--text_direction="):
            text_direction = arg.split("=", 1)[1]
        elif arg.startswith("--text_align="):
            text_align = arg.split("=", 1)[1]
        elif not arg.startswith("--"):
            url = arg

    if url is None:
        print("Usage: python browser.py [--text_direction=ltr|rtl] [--text_align=left|right] <url>")
        sys.exit(1)

    browser = Browser()
    browser.layout_config["text_direction"] = text_direction
    browser.layout_config["text_align"] = text_align
    browser.load(URL(url))
    tkinter.mainloop()
