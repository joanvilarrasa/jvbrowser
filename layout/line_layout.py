from draw import linespace, paint_visual_effects
import skia

class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []

    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        # Layout the words in the line so that we have information about their font, width, and height
        for word in self.children:
            word.layout()
        max_ascent = min([word.font.getMetrics().fAscent for word in self.children])
        baseline = self.y + 1.25 * max_ascent

        # Set the y position of each word depending on the other words in the same line
        for word in self.children:
            word.y = baseline - word.font.getMetrics().fAscent

        max_descent = max([word.font.getMetrics().fDescent for word in self.children])

        self.height = max_descent - max_ascent

    def paint(self):
        return []

    def should_paint(self):
        return False

    def self_rect(self):
        return skia.Rect.MakeLTRB(
            self.x, self.y,
            self.x + self.width,
            self.y + self.height)

    def paint_effects(self, cmds):
        cmds = paint_visual_effects(
            self.node, cmds, self.self_rect())
        return cmds