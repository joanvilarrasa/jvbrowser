from emoji import is_emoji
from tag import Element
from text import Text

SELF_CLOSING_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
]
HEAD_TAGS = [
    "base", "basefont", "bgsound", "noscript",
    "link", "meta", "title", "style", "script",
]


class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []

    def parse(self):
        buffer = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if buffer: 
                    text_list = get_text_list_from_buffer(buffer)
                    for text_part in text_list:
                        self.add_text(text_part)
                buffer = ""
            elif c == ">":
                in_tag = False
                self.add_tag(buffer)
                buffer = ""
            else:
                buffer += c
        if not in_tag and buffer:
            text_list = get_text_list_from_buffer(buffer)
            for text_part in text_list:
                self.add_text(text_part)
        return self.finish()
    
    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
                attributes[key.casefold()] = value
            else:
                attributes[attrpair.casefold()] = ""
        return tag, attributes
    
    def add_text(self, text):
        if text.isspace(): return
        self.implicit_tags(None)
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)
    
    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return
        self.implicit_tags(tag)
        if tag.startswith("/"):
            if len(self.unfinished) == 1: return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and tag not in ["/head"] + HEAD_TAGS:
                self.add_tag("/head")
            else:
                break

    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()

    
def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)



def get_text_list_from_buffer(text):
    text_list = []
    text_parts = text.split("\n")
    for i in range(len(text_parts)):
        text_part = text_parts[i]
        in_entity = False
        final_text_part = ""
        entity = ""
        for i in range(len(text_part)):
            if is_emoji(text_part[i]):
                if len(final_text_part) > 0:
                    text_list.append(final_text_part)
                    final_text_part = ""
                text_list.append(text_part[i])
            elif text_part[i] == "&":
                entity = "&"
                in_entity = True
            elif text_part[i] == ";" and in_entity:
                entity += text_part[i]
                decoded_entity = decode_entity(entity)
                if decoded_entity is not None:
                    final_text_part += decoded_entity
                else:
                    final_text_part += entity
                entity = ""
                in_entity = False
            elif in_entity:
                entity += text_part[i]
                if len(entity) > 5:
                    final_text_part += entity
                    entity = ""
                    in_entity = False      
            elif not in_entity:
                final_text_part += text_part[i]
        if final_text_part != "":   
            text_list.append(final_text_part)
        if i < len(text_parts) - 1:
            text_list.append("\n")
    return text_list
    
def decode_entity(entity):
    if entity == "&lt;":
        return "<"
    elif entity == "&gt;":
        return ">"
    elif entity == "&shy;":
        return "\N{soft hyphen}"
    else:
        return None