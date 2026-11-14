#!/usr/bin/env python3
"""
Generate proper Arabic 8x8 4bpp font glyphs using TTF font
"""

from PIL import Image, ImageDraw, ImageFont

# Arabic characters mapped to 0xA0-0xFF
arabic_chars = [
    # 0xA0-0xBC: Basic isolated forms
    ('\u0627', 0xA0),  # ا
    ('\u0628', 0xA1),  # ب
    ('\u062A', 0xA2),  # ت
    ('\u062B', 0xA3),  # ث
    ('\u062C', 0xA4),  # ج
    ('\u062D', 0xA5),  # ح
    ('\u062E', 0xA6),  # خ
    ('\u062F', 0xA7),  # د
    ('\u0630', 0xA8),  # ذ
    ('\u0631', 0xA9),  # ر
    ('\u0632', 0xAA),  # ز
    ('\u0633', 0xAB),  # س
    ('\u0634', 0xAC),  # ش
    ('\u0635', 0xAD),  # ص
    ('\u0636', 0xAE),  # ض
    ('\u0637', 0xAF),  # ط
    ('\u0638', 0xB0),  # ظ
    ('\u0639', 0xB1),  # ع
    ('\u063A', 0xB2),  # غ
    ('\u0641', 0xB3),  # ف
    ('\u0642', 0xB4),  # ق
    ('\u0643', 0xB5),  # ك
    ('\u0644', 0xB6),  # ل
    ('\u0645', 0xB7),  # م
    ('\u0646', 0xB8),  # ن
    ('\u0647', 0xB9),  # ه
    ('\u0648', 0xBA),  # و
    ('\u0649', 0xBB),  # ى
    ('\u064A', 0xBC),  # ي
    # 0xBD-0xC3: Hamza variants
    ('\u0623', 0xBD),  # أ
    ('\u0625', 0xBE),  # إ
    ('\u0622', 0xBF),  # آ
    ('\u0621', 0xC0),  # ء
    ('\u0629', 0xC1),  # ة
    ('\u0624', 0xC2),  # ؤ
    ('\u0626', 0xC3),  # ئ
    # 0xC4: Tatweel
    ('\u0640', 0xC4),  # ـ
    # Punctuation
    ('.', 0xC5), (',', 0xC6), ('!', 0xC7), ('?', 0xC8), (':', 0xC9), (';', 0xCA),
    ('(', 0xCB), (')', 0xCC), ('[', 0xCD), (']', 0xCE), ('{', 0xCF), ('}', 0xD0),
    ('-', 0xD1), ('_', 0xD2), ('+', 0xD3), ('=', 0xD4), ('*', 0xD5), ('/', 0xD6),
    ('\\', 0xD7), ('|', 0xD8), ('<', 0xD9), ('>', 0xDA), ('@', 0xDB), ('#', 0xDC),
    ('$', 0xDD), ('%', 0xDE), ('^', 0xDF), ('&', 0xE0), ('~', 0xE1), ('`', 0xE2),
    ('"', 0xE3), ("'", 0xE4),
    # Digits
    ('0', 0xE5), ('1', 0xE6), ('2', 0xE7), ('3', 0xE8), ('4', 0xE9),
    ('5', 0xEA), ('6', 0xEB), ('7', 0xEC), ('8', 0xED), ('9', 0xEE),
    # Arabic punctuation
    ('\u060C', 0xEF),  # ،
    ('\u061B', 0xF0),  # ؛
    ('\u061F', 0xF1),  # ؟
    ('\u066A', 0xF2),  # ٪
    # Latin letters for control codes
    ('A', 0xF3), ('B', 0xF4), ('C', 0xF5), ('D', 0xF6), ('E', 0xF7),
]

def generate_glyph(char, font, size=8):
    """Generate 8x8 4bpp glyph for a character"""
    # Create image with extra space for positioning
    img = Image.new('L', (16, 16), 0)
    draw = ImageDraw.Draw(img)
    
    # Draw character centered
    bbox = draw.textbbox((0, 0), char, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (16 - w) // 2
    y = (16 - h) // 2 - 1
    draw.text((x, y), char, fill=255, font=font)
    
    # Crop to 8x8 and convert to 4bpp
    img = img.crop((4, 4, 12, 12))  # Center 8x8
    
    # Convert to 4bpp tile (32 bytes)
    tile = bytearray(32)
    pixels = img.load()
    for row in range(8):
        for plane in range(4):
            byte_val = 0
            for col in range(8):
                bit = 7 - col
                val = pixels[col, row]
                # Convert to 4 levels (0-3)
                pixel_val = min(3, val // 64)
                if pixel_val & (1 << plane):
                    byte_val |= (1 << bit)
            tile[row * 4 + plane] = byte_val
    return bytes(tile)

# Try Arabic fonts
font_path = 'C:/Windows/Fonts/tradbdo.ttf'  # Arabic Typesetting
try:
    font = ImageFont.truetype(font_path, 10)
    print(f"Using font: {font_path}")
except:
    try:
        font = ImageFont.truetype('C:/Windows/Fonts/andlso.ttf', 10)  # Andalus
        print("Using font: andlso.ttf")
    except:
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 10)
            print("Using font: arial.ttf (fallback)")
        except:
            font = ImageFont.load_default()
            print("Using default font")

# Generate all glyphs
glyphs = {}
for char, code in arabic_chars:
    glyphs[code] = generate_glyph(char, font)

# Fill remaining codes (0xF8-0xFF) with placeholder
for code in range(0xF8, 0x100):
    if code not in glyphs:
        # Simple pattern
        tile = bytearray(32)
        for row in range(8):
            for plane in range(4):
                byte_val = 0
                for col in range(8):
                    bit = 7 - col
                    seed = (code * 13 + row * 7 + col * 11) % 16
                    pixel_val = seed % 4
                    if pixel_val & (1 << plane):
                        byte_val |= (1 << bit)
                tile[row * 4 + plane] = byte_val
        glyphs[code] = bytes(tile)

# Save to binary file
with open(r'C:\Users\user\Desktop\game\arabic_font_tiles.bin', 'wb') as f:
    for code in range(0xA0, 0x100):
        f.write(glyphs[code])

print(f"Generated {len(glyphs)} glyphs (0xA0-0xFF)")
print(f"Saved to arabic_font_tiles.bin ({0x60 * 32} bytes)")

# Also create a preview image
preview = Image.new('P', (16*8, 6*8))
palette = []
for i in range(16):
    v = i * 17
    palette.extend([v, v, v])
preview.putpalette(palette)

for idx, (char, code) in enumerate(arabic_chars):
    if code > 0xF7:
        continue
    tile = glyphs[code]
    # Convert tile back to pixels for preview
    pixels = []
    for row in range(8):
        row_pixels = []
        for plane in range(4):
            pass
    # Just draw the character directly for preview
    x = (idx % 16) * 8
    y = (idx // 16) * 8
    draw = ImageDraw.Draw(preview)
    draw.text((x, y), char, fill=15, font=font)

preview.save(r'C:\Users\user\Desktop\game\arabic_font_preview.png')
print("Saved preview to arabic_font_preview.png")