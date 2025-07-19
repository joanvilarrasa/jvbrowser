import os
import tkinter
import unicodedata

class EmojiProvider:

    def __init__(self):
        # Setup emoji support
        self.emoji_cache = {}
        self.emoji_dir = "assets/emojis"
        self.emoji_size = 16  # Size for emoji images

    def load_emoji_image(self, emoji):
        if emoji in self.emoji_cache:
            return self.emoji_cache[emoji]
        
        filename = emoji_to_filename(emoji)
        filepath = os.path.join(self.emoji_dir, filename)
        
        if os.path.exists(filepath):
            try:
                image = tkinter.PhotoImage(file=filepath)
                # TODO: Resize image to emoji_size
                self.emoji_cache[emoji] = image
                return image
            except Exception as e:
                print(f"Error loading emoji {emoji}: {e}")
                return None
        else:
            return None

def is_emoji(char):
    code_point = ord(char)
    # Basic emoji ranges (simplified)
    emoji_ranges = [
        (0x1F600, 0x1F64F),  # Emoticons
        (0x1F300, 0x1F5FF),  # Miscellaneous Symbols and Pictographs
        (0x1F680, 0x1F6FF),  # Transport and Map Symbols
        (0x1F1E0, 0x1F1FF),  # Regional Indicator Symbols
        (0x2600, 0x26FF),    # Miscellaneous Symbols
        (0x2700, 0x27BF),    # Dingbats
        (0xFE00, 0xFE0F),    # Variation Selectors
        (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
        (0x1F018, 0x1F270),  # Various symbols
    ]
    
    for start, end in emoji_ranges:
        if start <= code_point <= end:
            return True
    
    # Check Unicode category
    category = unicodedata.category(char)
    return category in ['So', 'Sk']  # Symbol, Other or Symbol, Modifier


def emoji_to_filename(emoji):
    code_points = []
    for char in emoji:
        code_points.append(f"{ord(char):X}")
    return f"{'-'.join(code_points)}.png"
