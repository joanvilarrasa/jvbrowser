import skia
from draw import DrawImage, linespace
from layout.embed_layout import EmbedLayout, dpx
from protected_field import ProtectedField

class ImageLayout(EmbedLayout):
    def __init__(self, node, parent, previous):
        super().__init__(node, parent, previous, None)

    def layout(self):
        super().layout()
        zoom = self.zoom.read(notify=self.width)
        width_attr = self.node.attributes.get("width")
        height_attr = self.node.attributes.get("height")
        image_width = self.node.image.width()
        image_height = self.node.image.height()

        aspect_ratio = image_width / image_height

        if width_attr and height_attr:
            self.width.set(dpx(int(width_attr), zoom))
            self.img_height = dpx(int(height_attr), zoom)
        elif width_attr:
            self.width.set(dpx(int(width_attr), zoom))
            self.img_height = self.width.get() / aspect_ratio
        elif height_attr:
            self.img_height = dpx(int(height_attr), zoom)
            self.width.set(self.img_height * aspect_ratio)
        else:
            self.width.set(dpx(image_width, zoom))
            self.img_height = dpx(image_height, zoom)
        
        font = self.font.read(notify=self.height)
        self.height.set(max(self.img_height, linespace(font)))

        height = self.height.read(notify=self.ascent)
        self.ascent.set(-height)
        self.descent.set(0)

    def paint(self):
        cmds = []
        rect = skia.Rect.MakeLTRB(
            self.x, self.y + self.height - self.img_height,
            self.x + self.width, self.y + self.height)
        quality = self.node.style.get("image-rendering", "auto")
        cmds.append(DrawImage(self.node.image, rect, quality))
        return cmds
