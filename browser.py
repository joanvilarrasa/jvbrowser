from emoji import EmojiProvider, is_emoji
from url import URL, lex
import tkinter

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

    def load(self, url):
        body = url.request()
        text = lex(body)
        self.content["text"] = text
        self.content["display_list"] = layout(
            self.content["text"], 
            self.canvas.winfo_width() - self.scroll["bar_width"],
            self.layout_config["text_direction"],
            self.layout_config["text_align"]
        )
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
        self.content["display_list"] = layout(
            self.content["text"], 
            e.width - self.scroll["bar_width"],
            self.layout_config["text_direction"],
            self.layout_config["text_align"]
        )
        if len(self.content["display_list"]) > 0:
            self.scroll["max"] = self.content["display_list"][-1][1] - self.canvas.winfo_height()
        else:
            self.scroll["max"] = 0
        self.scroll["show"] = self.scroll["max"] > 0
        self.draw()



# Helpers
def layout(text, max_width, text_direction="ltr", text_align="left"):
    display_list = []

    if text_direction == "rtl":
        cursor_x_initial_value = max_width - HSTEP
        cursor_x_increment = -HSTEP
        cursor_x_max_value = HSTEP
    else:
        cursor_x_initial_value = HSTEP
        cursor_x_increment = HSTEP
        cursor_x_max_value = max_width - HSTEP

    cursor_x = cursor_x_initial_value
    cursor_y = VSTEP

    current_line = []
    for c in text: 
        current_line.append((cursor_x, cursor_y, c))
        cursor_x += cursor_x_increment
        if c == "\n":
            if text_direction == "rtl" and text_align == "left":
                offset_line_x(current_line, -cursor_x)
            elif text_direction == "ltr" and text_align == "right":
                offset_line_x(current_line, max_width - cursor_x)

            display_list.extend(current_line)
            current_line = []
            cursor_y += VSTEP * 1.5
            cursor_x = cursor_x_initial_value
        elif cursor_x_overflow(cursor_x, cursor_x_max_value, text_direction):
            display_list.extend(current_line)
            current_line = []
            cursor_y += VSTEP
            cursor_x = cursor_x_initial_value
    return display_list

def cursor_x_overflow(cursor_x, cursor_x_max_value, text_direction):
    if text_direction == "ltr":
        return cursor_x >= cursor_x_max_value
    else:
        return cursor_x <= cursor_x_max_value

def offset_line_x(line, offset):
    for i in range(len(line)):
        cursor_x, cursor_y, c = line[i]
        line[i] = (cursor_x + offset, cursor_y, c)


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
