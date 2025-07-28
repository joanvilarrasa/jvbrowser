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
        max_ascent = max([word.font.metrics("ascent") for word in self.children])
        baseline = self.y + 1.25 * max_ascent

        # Set the y position of each word depending on the other words in the same line
        for word in self.children:
            word.y = baseline - word.font.metrics("ascent")

        max_descent = max([word.font.metrics("descent") for word in self.children])

        self.height = 1.25 * (max_ascent + max_descent)

    def paint(self):
        return []