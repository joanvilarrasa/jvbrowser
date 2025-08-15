from css.selectors import DescendantSelector, TagSelector, PseudoclassSelector, PseudoclassSelector
from htmltree.tag import Element

# Local frame duration to compute transition frames (approx 30fps)
REFRESH_RATE_SEC = 0.033

INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}

CSS_PROPERTIES = {
    "font-size": "inherit", "font-weight": "inherit",
    "font-style": "inherit", "color": "inherit",
    "opacity": "1.0", "transition": "",
    "transform": "none", "mix-blend-mode": None,
    "border-radius": "0px", "overflow": "visible",
    "outline": "none", "background-color": "transparent",
    "image-rendering": "auto",
}


class CSSParser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def parse(self):
        rules = []
        media = None
        while self.i < len(self.s):
            try:
                self.whitespace()
                if self.i < len(self.s) and self.s[self.i] == "@" and not media:
                    prop, val = self.media_query()
                    if prop == "prefers-color-scheme" and \
                        val in ["dark", "light"]:
                        media = val
                    self.whitespace()
                    self.literal("{")
                    self.whitespace()
                elif self.i < len(self.s) and self.s[self.i] == "}" and media:
                    self.literal("}")
                    media = None
                    self.whitespace()
                else:
                    selector = self.selector()
                    self.literal("{")
                    self.whitespace()
                    body = self.body()
                    self.literal("}")
                    rules.append((media, selector, body))
            except Exception:
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()
                else:
                    break
        return rules

    def media_query(self):
        self.literal("@")
        assert self.word() == "media"
        self.whitespace()
        self.literal("(")
        self.whitespace()
        prop, val = self.pair([")"])
        self.whitespace()
        self.literal(")")
        return prop, val

    def selector(self):
        out = self.simple_selector()
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != "{":
            descendant = self.simple_selector()
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out

    def simple_selector(self):
        out = TagSelector(self.word().casefold())
        if self.i < len(self.s) and self.s[self.i] == ":":
            self.literal(":")
            pseudoclass = self.word().casefold()
            out = PseudoclassSelector(pseudoclass, out)
        return out

    def body(self):
        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != "}":
            try:
                prop, val = self.pair([";", "}"])
                pairs[prop] = val
                self.whitespace()
                if self.i < len(self.s) and self.s[self.i] == ";":
                    self.literal(";")
                self.whitespace()
            except Exception:
                why = self.ignore_until([";", "}"])
                if why == ";":
                    self.literal(";")
                    self.whitespace()
                else:
                    break
        return pairs

    def pair(self, until=None):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        if until is None:
            val = self.word()
        else:
            val = self.until_chars(until)
        return prop.casefold(), val.strip()

    def until_chars(self, chars):
        start = self.i
        while self.i < len(self.s) and self.s[self.i] not in chars:
            self.i += 1
        return self.s[start:self.i]

    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def word(self):
        start = self.i
        while self.i < len(self.s):
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
                self.i += 1
            else:
                break
        if not (self.i > start):
            raise Exception("Parsing error")
        return self.s[start:self.i]

    def literal(self, literal):
        if not (self.i < len(self.s) and self.s[self.i] == literal):
            raise Exception("Parsing error")
        self.i += 1

    def ignore_until(self, chars):
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1
        return None

def parse_transition(value):
    properties = {}
    if not value:
        return properties
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        parts = item.split(" ", 1)
        if len(parts) != 2:
            continue
        property, duration = parts
        duration = duration.strip()
        try:
            # assume seconds unit 's'
            seconds = float(duration[:-1]) if duration.endswith('s') else float(duration)
            frames = int(seconds / REFRESH_RATE_SEC)
            properties[property] = max(frames, 1)
        except Exception:
            continue
    return properties

def diff_styles(old_style, new_style):
    transitions = {}
    transition_spec = parse_transition(new_style.get("transition"))
    for property, num_frames in transition_spec.items():
        if property not in old_style: continue
        if property not in new_style: continue
        old_value = old_style[property]
        new_value = new_style[property]
        if old_value == new_value: continue
        transitions[property] = (old_value, new_value, num_frames)
    return transitions

class NumericAnimation:
    def __init__(self, old_value, new_value, num_frames):
        self.old_value = float(old_value)
        self.new_value = float(new_value)
        self.num_frames = max(int(num_frames), 1)
        self.frame_count = 1
        total_change = self.new_value - self.old_value
        self.change_per_frame = total_change / self.num_frames

    def animate(self):
        self.frame_count += 1
        if self.frame_count >= self.num_frames:
            return None
        current_value = self.old_value + self.change_per_frame * self.frame_count
        return str(current_value)

def init_style(node):
    node.style = dict([
            (property, ProtectedField(node, property, None,
                [node.parent.style[property]] \
                    if node.parent and \
                        property in INHERITED_PROPERTIES \
                    else []))
            for property in CSS_PROPERTIES
        ])

def style(node, rules, tab=None):
    node.style = {}
    # Inhetited properties
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default_value

    # Properties from rules (the stylesheet)
    for rule in rules:
        if len(rule) == 2:
            selector, body = rule
            media = None
        else:
            media, selector, body = rule
        if media and tab is not None:
            if (media == "dark") != bool(getattr(tab, 'dark_mode', False)):
                continue
        if not selector.matches(node): continue
        for property, value in body.items():
            node.style[property] = value

    if isinstance(node, Element) and "style" in node.attributes:
        # Properties from the style attribute
        pairs = CSSParser(node.attributes["style"]).body()
        for property, value in pairs.items():
            node.style[property] = value

        
        # Inhetited properties
        for property, default_value in INHERITED_PROPERTIES.items():
            if node.parent:
                parent_field = node.parent.style[property]
                parent_value = parent_field.read(notify=node.style[property])
                new_style[property] = parent_value
            else:
                new_style[property] = default_value

        # Properties from rules (the stylesheet)
        for selector, body in rules:
            if not selector.matches(node): continue
            for property, value in body.items():
                new_style[property] = value

        if isinstance(node, Element) and "style" in node.attributes:
            # Properties from the style attribute
            pairs = CSSParser(node.attributes["style"]).body()
            for property, value in pairs.items():
                new_style[property] = value

        # Handle percentage font-size
        if new_style["font-size"].endswith("%"):
            if node.parent:
                parent_field = node.parent.style["font-size"]
                parent_font_size = parent_field.read(notify=node.style["font-size"])
            else:
                parent_font_size = INHERITED_PROPERTIES["font-size"]
            node_pct = float(new_style["font-size"][:-1]) / 100
            parent_px = float(parent_font_size[:-2])
            new_style["font-size"] = str(node_pct * parent_px) + "px"

        # CSS transitions
        if not hasattr(node, 'animations'):
            try:
                # Attach animations dict lazily; callers may not be Element/Text
                node.animations = {}
            except Exception:
                pass

        if 'style' in dir(node) and isinstance(node, Element):
            old_style = getattr(node, 'old_style', None)
            if old_style:
                transitions = diff_styles(old_style, new_style)
                for property, (old_value, new_value, num_frames) in transitions.items():
                    if property == 'opacity':
                        if tab is not None:
                            tab.set_needs_render()
                        animation = NumericAnimation(old_value, new_value, num_frames)
                        node.animations[property] = animation
                        value = animation.animate()
                        if value is not None:
                            new_style[property] = value
            node.old_style = dict(new_style)

        # Set each field individually
        for property, field in node.style.items():
            field.set(new_style[property])

    for child in node.children:
        style(child, rules, tab)

def dirty_style(node):
    for property, value in node.style.items():
        value.mark()