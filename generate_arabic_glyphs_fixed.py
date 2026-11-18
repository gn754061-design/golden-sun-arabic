#!/usr/bin/env python3
"""
Generate proper Arabic 8x8 4bpp font glyphs - FIXED POSITIONING
"""

from PIL import Image, ImageDraw, ImageFont

arabic_chars = [
    ('\u0627', 0xA0), ('\u0628', 0xA1), ('\u062A', 0xA2), ('\u062B', 0xA3),
    ('\u062C', 0xA4), ('\u062D', 0xA5), ('\u062E', 0xA6), ('\u062F', 0xA7),
    ('\u0630', 0xA8), ('\u0631', 0xA9), ('\u0632', 0xAA), ('\u0633', 0xAB),
    ('\u0634', 0xAC), ('\u0635', 0xAD), ('\u0636', 0xAE), ('\u0637', 0xAF),
    ('\u0638', 0xB0), ('\u0639', 0xB1), ('\u063A', 0xB2), ('\u0641', 0xB3),
    ('\u0642', 0xB4), ('\u0643', 0xB5), ('\u0644', 0xB6), ('\u0645', 0xB7),
    ('\u0646', 0xB8), ('\u0647', 0xB9), ('\u0648', 0xBA), ('\u0649', 0xBB),
    ('\u064A', 0xBC),
    ('\u0623', 0xBD), ('\u0625', 0xBE), ('\u0622', 0xBF), ('\u0621', 0xC0),
    ('\u0629', 0xC1), ('\u0624', 0xC2), ('\u0626', 0xC3),
    ('\u0640', 0xC4),
    ('.', 0xC5), (',', 0xC6), ('!', 0xC7), ('?', 0xC8), (':', 0xC9), (';', 0xCA),
    ('(', 0xCB), (')', 0xCC), ('[', 0xCD), (']', 0xCE), ('{', 0xCF), ('}', 0xD0),
    ('-', 0xD1), ('_', 0xD2), ('+', 0xD3), ('=', 0xD4), ('*', 0xD5), ('/', 0xD6),
    ('\\', 0xD7), ('|', 0xD8), ('<', 0xD9), ('>', 0xDA), ('@', 0xDB), ('#', 0xDC),
    ('$', 0xDD), ('%', 0xDE), ('^', 0xDF), ('&', 0xE0), ('~', 0xE1), ('`', 0xE2),
    ('"', 0xE3), ("'", 0xE4),
    ('0', 0xE5), ('1', 0xE6), ('2', 0xE7), ('3', 0xE8), ('4', 0xE9),
    ('5', 0xEA), ('6', 0xEB), ('7', 0xEC), ('8', 0xED), ('9', 0xEE),
    ('\u060C', 0xEF), ('\u061B', 0xF0), ('\u061F', 0xF1), ('\u066A', 0xF2),
    ('A', 0xF3), ('B', 0xF4), ('C', 0xF5), ('D', 0xF6), ('E', 0xF7),
]

def generate_glyph(char, font):
    """Generate 8x8 4bpp glyph - render directly at 8x8"""
    # Create 8x8 image directly
    img = Image.new('L', (8, 8), 0)
    draw = ImageDraw.Draw(img)
    
    # Get text size
    bbox = draw.textbbox((0, 0), char, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    
    # Center in 8x8
    x = (8 - w) // 2 - bbox[0]
    y = (8 - h) // 2 - bbox[1] - 1  # Slight upward adjustment
    
    draw.text((x, y), char, fill=255, font=font)
    
    # Convert to 4bpp (32 bytes)
    tile = bytearray(32)
    pixels = img.load()
    for row in range(8):
        for plane in range(4):
            byte_val = 0
            for col in range(8):
                bit = 7 - col
                val = pixels[col, row]
                pixel_val = min(3, val // 64)  # 4 levels
                if pixel_val & (1 << plane):
                    byte_val |= (1 << bit)
            tile[row * 4 + plane] = byte_val
    return bytes(tile)

# Load font
font_path = 'C:/Windows/Fonts/tradbdo.ttf'
try:
    font = ImageFont.truetype(font_path, 9)  # Slightly larger for 8x8
    print(f"Using: {font_path}")
except:
    font = ImageFont.truetype('C:/Windows/Fonts/andlso.ttf', 9)
    print("Using: andlso.ttf")

# Generate glyphs
glyphs = {}
for char, code in arabic_chars:
    glyphs[code] = generate_glyph(char, font)

# Fill remaining with fallback patterns
for code in range(0xF8, 0x100):
    if code not in glyphs:
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

# Verify coverage
print("Glyph coverage check:")
for code in range(0xA0, 0x100):
    tile = glyphs[code]
    non_zero = sum(1 for b in tile if b != 0)
    if non_zero == 0:
        print(f"  WARNING: 0x{code:02X} is EMPTY!")
    elif non_zero < 8:
        print(f"  0x{code:02X}: only {non_zero}/32 non-zero bytes")

# Save
with open("./"arabic_font_tiles.bin', 'wb') as f:
    for code in range(0xA0, 0x100):
        f.write(glyphs[code])

print(f"\nSaved {len(glyphs)} glyphs to arabic_font_tiles.bin")

# Preview
preview = Image.new('L', (16*8, 6*8), 0)
draw = ImageDraw.Draw(preview)
for idx, (char, code) in enumerate(arabic_chars):
    if code > 0xF7:
        continue
    x = (idx % 16) * 8
    y = (idx // 16) * 8
    draw.text((x, y), char, fill=255, font=font)
preview.save("./"arabic_font_preview.png')
print("Saved preview")