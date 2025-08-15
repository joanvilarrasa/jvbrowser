from protected_field import ProtectedField

class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
        self.style = {}
        self.is_focused = False
        self.layout_object = None

    def __repr__(self):
        if self.tag == "input":
            return ("<" + self.tag + ">")
        else:
            return ("<" + self.tag + ">")