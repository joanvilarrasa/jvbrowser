from typing import Literal
from emoji import is_emoji
from font_cache import get_font
from tag import Tag
from text import Text

HSTEP, VSTEP = 13, 18

class Layout:
    def __init__(self, tokens, max_width, text_direction, text_align):
        self.display_list = []
        self.line = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight: Literal["normal", "bold"] = "normal"
        self.style: Literal["roman", "italic"] = "roman"
        self.size = 16
        self.max_width = max_width
        self.text_direction: Literal["ltr", "rtl"] = text_direction
        self.text_align: Literal["left", "right", "center"] = text_align
        self.sup = False
        self.sub = False
        self.abbr = False
        self.pre = False

        for tok in tokens:
            self.token(tok)
        self.flush()

    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
        actual_word = word
        if self.abbr:
            actual_word = actual_word.upper()
        if self.text_direction == "rtl":
            actual_word = get_reversed_word(word)

        if self.pre:
            actual_word = actual_word.replace("\n", " ")

        w = font.measure(actual_word)
        if (self.cursor_x + w > self.max_width - HSTEP or word == "\n") and not self.pre:
            i = len(actual_word) - 1
            found_good_soft_hyphen = False
            while i > 0 and found_good_soft_hyphen is False:
                if actual_word[i] == "\N{soft hyphen}":
                    partial_w = font.measure(actual_word[:i+1].replace("\N{soft hyphen}", ""))
                    if self.cursor_x + partial_w < self.max_width - HSTEP:
                        found_good_soft_hyphen = True
                        self.line.append((self.cursor_x, self.cursor_y, actual_word[:i+1].replace("\N{soft hyphen}", "")+"\N{soft hyphen}", font, partial_w, self.sup))
                        self.flush()
                        actual_word = actual_word[i+1:]
                i -= 1
            if found_good_soft_hyphen is False:
                self.flush()
                
        actual_word = actual_word.replace("\N{soft hyphen}", "")
        self.line.append((self.cursor_x, self.cursor_y, actual_word, font, w, self.sup))
        self.cursor_x += w + HSTEP
    
    def token(self, tok): 
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)
        elif isinstance(tok, Tag):
            if tok.tag == "i":
                style = "italic"
            elif tok.tag == "/i":
                style = "roman"
            elif tok.tag == "b":
                self.weight = "bold"
            elif tok.tag == "/b":
                self.weight = "normal"
            elif tok.tag == "abbr":
                self.size -= 4
                self.weight = "bold"
                self.abbr = True
            elif tok.tag == "/abbr":
                self.size += 4
                self.weight = "normal"
                self.abbr = False
            elif tok.tag == "pre":
                self.pre = True
            elif tok.tag == "/pre":
                self.pre = False
            elif tok.tag == "small":         
                self.size -= 2
            elif tok.tag == "/small":
                self.size += 2
            elif tok.tag == "big":
                self.size += 4
            elif tok.tag == "/big":
                self.size -= 4
            elif tok.tag == "br":
                self.flush()
            elif tok.tag == "/p":
                self.flush()
                self.cursor_y += VSTEP
            elif tok.tag == "sup":
                self.size = int(self.size / 2)
                self.sup = True
            elif tok.tag == "/sup":
                self.size *= 2
                self.sup = False
            elif tok.tag == "sub":
                self.size = int(self.size / 2)
                self.sub = True
            elif tok.tag == "/sub":
                self.size *= 2
                self.sub = False
            elif tok.tag == "h1":
                self.flush()
                self.size += 4
                self.weight = "bold"
                self.text_align = "center"
                self.cursor_y += VSTEP
            elif tok.tag == "/h1":
                self.flush()
                self.size -= 4
                self.weight = "normal"
                self.text_align = "left"
                self.cursor_y += VSTEP

    def flush(self):
        if not self.line: return
        final_line = []
        metrics = [font.metrics() for x, y, word, font, w, sup in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        max_descent = max([metric["descent"] for metric in metrics])
        baseline = self.cursor_y + 1.25 * max_ascent
        for i in range(len(self.line)):
            x, y, word, font, w, sup = self.line[i]
            if sup:
                y = baseline - max_ascent
            else:
                y = baseline - font.metrics("ascent")
            self.line[i] = (x, y, word, font, w, sup)

        # Move the cursor down accounting for the max descender of the current line
        self.cursor_y = baseline + 1.25 * max_descent

        # Manage text alignment and direction
        max_x = max([x + w for x, y, word, font, w, sup in self.line])
        eol_empty_space = self.max_width - max_x
        # If the text direction is right to left we need to reverse the order of the words in the line
        if self.text_direction == "rtl":
            for i in range(len(self.line)):
                x, y, word, font, w, sup = self.line[i]
                self.line[i] = (max_x - x - w + HSTEP, y, word, font, w, sup)

        if self.text_align == "right":
            for i in range(len(self.line)):
                x, y, word, font, w, sup = self.line[i]
                self.line[i] = (x + eol_empty_space, y, word, font, w, sup)
        elif self.text_align == "center":
            for i in range(len(self.line)):
                x, y, word, font, w, sup = self.line[i]
                self.line[i] = (x + eol_empty_space / 2, y, word, font, w, sup)
        
        for i in range(len(self.line)):
            x, y, word, font, w, sup = self.line[i]
            final_line.append((x, y, word, font))

        self.display_list.extend(final_line)
        self.cursor_x = HSTEP
        self.line = []



def lex(body):
    out = []
    buffer = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
            if buffer: 
                text_list = get_text_list_from_buffer(buffer)
                for text_part in text_list:
                    out.append(Text(text_part))

            buffer = ""
        elif c == ">":
            in_tag = False
            out.append(Tag(buffer))
            buffer = ""
        else:
            buffer += c
    if not in_tag and buffer:
        text_list = get_text_list_from_buffer(buffer)
        for text_part in text_list:
            out.append(Text(text_part))
    return out

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

def get_reversed_word(word):
    return "".join(reversed(word))