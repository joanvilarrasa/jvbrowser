from layout.block_layout import HSTEP, VSTEP, WIDTH, BlockLayout


class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []

        # Positioning
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        self.width = WIDTH - 2*HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height

    def paint(self):
        return []