from emoji import EmojiProvider, is_emoji
from url import URL, lex
import tkinter
import os
import unicodedata

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
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
        self.emoji_provider = EmojiProvider()

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
        self.content["display_list"] = layout(self.content["text"], self.canvas.winfo_width() - self.scroll["bar_width"])
        if len(self.content["display_list"]) > 0:
            self.scroll["max"] = self.content["display_list"][-1][1]
        else:
            self.scroll["max"] = 0
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.content["display_list"]:
            if y > self.scroll["value"] + self.canvas.winfo_height(): continue
            if y + VSTEP < self.scroll["value"]: continue

            # Check if character is an emoji
            if is_emoji(c):
                emoji_image = self.emoji_provider.load_emoji_image(c)
                if emoji_image:
                    # Display emoji as image
                    self.canvas.create_image(x, y - self.scroll["value"], image=emoji_image)
                else:
                    # Fallback to text if image not found
                    self.canvas.create_text(x, y - self.scroll["value"], text=c)
            else:
                # Display regular text
                self.canvas.create_text(x, y - self.scroll["value"], text=c)

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
        self.content["display_list"] = layout(self.content["text"], e.width - self.scroll["bar_width"])
        if len(self.content["display_list"]) > 0:
            self.scroll["max"] = self.content["display_list"][-1][1] - self.canvas.winfo_height()
        else:
            self.scroll["max"] = 0
        self.scroll["show"] = self.scroll["max"] > 0
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
