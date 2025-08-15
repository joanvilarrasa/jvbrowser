from protected_field import ProtectedField

class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
<<<<<<< HEAD
        self.layout_object = None
=======
        self.style = None
>>>>>>> 3e07826 (Done with the project, pretty good book)

    def __repr__(self):
        return repr(self.text)
