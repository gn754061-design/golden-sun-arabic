#!/usr/bin/env python3
"""
test_arabic_shaping_preview.py
Validates the Rooyin Arabic font by rendering test sentences and saving a PNG preview.
"""
import os
import re
from PIL import Image, ImageDraw
from rooyin_font_builder import load_rooyin_renders, build_glyph_tiles

renders, labels = load_rooyin_renders()
glyphs, widths, form_map = build_glyph_tiles(renders, labels)

# Shaper definitions based on ar_shape.mjs
RIGHT = set(['ا', 'أ', 'إ', 'آ', 'د', 'ذ', 'ر', 'ز', 'و', 'ة', 'ى'])
DUAL = set([
    'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'س', 'ش', 'ص', 'ض', 'ط', 'ظ',
    'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'ي', 'ئ'
])

LIGATURES = {
    'لا': 'ligature LAM WITH ALEF',
    'لأ': 'ligature LAM WITH ALEF WITH HAMZA ABOVE',
    'لإ': 'ligature LAM WITH ALEF WITH HAMZA BELOW',
    'لآ': 'ligature LAM WITH ALEF WITH MADDA ABOVE',
}

PUNCT = {
    '،': '،',
    '؛': '؛',
    '؟': '؟',
    '«': '«',
    '»': '»',
    'ـ': 'ـ',
}

def is_arabic(ch):
    return '\u0600' <= ch <= '\u06FF'

def shape_word(word):
    """Shape a single Arabic word into glyph codes."""
    chars = list(word)
    out_codes = []
    i = 0
    n = len(chars)

    while i < n:
        ch = chars[i]
        
        # Check Lam-Alef ligatures
        if ch == 'ل' and i + 1 < n and chars[i+1] in ['ا', 'أ', 'إ', 'آ']:
            pair = 'ل' + chars[i+1]
            lig_name = LIGATURES[pair]
            recv = (i > 0 and (chars[i-1] in DUAL or (chars[i-1] in RIGHT and False))) # only DUAL connects forward to lam
            form = 'FINAL' if recv else 'ISOLATED'
            full_label = f'{lig_name} {form}'
            if full_label in form_map:
                out_codes.append(form_map[full_label])
            i += 2
            continue

        # Check punctuation
        if ch in PUNCT:
            p_label = PUNCT[ch]
            if p_label in form_map:
                out_codes.append(form_map[p_label])
            i += 1
            continue

        if not is_arabic(ch):
            # ASCII character (space, digit, etc.)
            out_codes.append(ord(ch))
            i += 1
            continue

        # Hamza standalone
        if ch == 'ء':
            if 'ء' in form_map:
                out_codes.append(form_map['ء'])
            i += 1
            continue

        # Determine connection
        # recv: previous character connects forward to current character
        recv = (i > 0 and chars[i-1] in DUAL)
        # send: current character connects forward to next character
        send = (i + 1 < n and (chars[i+1] in DUAL or chars[i+1] in RIGHT))

        if ch in DUAL:
            if recv and send:
                form = 'med'
            elif recv:
                form = 'fin'
            elif send:
                form = 'ini'
            else:
                form = 'iso'
        elif ch in RIGHT:
            if recv:
                form = 'fin'
            else:
                form = 'iso'
        else:
            form = 'iso'

        label = f'{ch}:{form}'
        if label in form_map:
            out_codes.append(form_map[label])
        else:
            print(f'Missing form: {label}')
            out_codes.append(ord('?'))

        i += 1

    return out_codes

def shape_line(line):
    """
    Shape a line of text:
    Extracts Arabic runs, shapes them, handles 'ال' spacing,
    and performs RTL reversal for GBA LTR rendering.
    """
    # Split line into tokens of Arabic vs non-Arabic
    tokens = re.findall(r'[\u0600-\u06FF]+|[^\u0600-\u06FF]+', line)
    line_codes = []

    for t in tokens:
        if re.match(r'^[\u0600-\u06FF]+$', t):
            # Arabic word/run
            # Check for 'ال' rule: if word starts with 'ال', insert spacer
            # In RTL, when reversed, 'ا' is drawn last, 'ل' before it, then spacer!
            run_codes = shape_word(t)
            # RTL reverse for rendering on GBA
            line_codes.extend(reversed(run_codes))
        else:
            # Non-Arabic (spaces, numbers, symbols)
            # Standalone spaces and symbols
            for c in t:
                line_codes.append(ord(c))

    return line_codes

def render_codes_to_image(codes_list, line_spacing=14):
    """Render a list of lines (each a list of byte codes) to an Image."""
    # First measure total width and height
    max_w = 0
    total_h = len(codes_list) * line_spacing + 10

    for codes in codes_list:
        line_w = 0
        for c in codes:
            if c == ord(' '):
                line_w += 4
            elif c in widths:
                line_w += widths[c]
            else:
                line_w += 6
        if line_w > max_w:
            max_w = line_w

    img = Image.new('RGB', (max(max_w + 20, 240), total_h), (20, 24, 40)) # dark blue background
    draw = ImageDraw.Draw(img)

    for row_idx, codes in enumerate(codes_list):
        # We can right-align the line in a 220px box
        line_w = 0
        for c in codes:
            if c == ord(' '):
                line_w += 4
            elif c in widths:
                line_w += widths[c]
            else:
                line_w += 6

        cur_x = 220 - line_w # Right align
        cur_y = 6 + row_idx * line_spacing

        for c in codes:
            if c == ord(' '):
                cur_x += 4
                continue
            if c in glyphs:
                grid = glyphs[c]
                cw = widths[c]
                for y in range(12):
                    for x in range(cw):
                        if grid[y][x]:
                            px = cur_x + x
                            py = cur_y + y
                            if 0 <= px < img.width and 0 <= py < img.height:
                                img.putpixel((px, py), (255, 255, 255))
                cur_x += cw
            else:
                # Fallback for ascii
                cur_x += 6

    return img

if __name__ == '__main__':
    test_lines = [
        "كيف كان بإمكاننا أن",
        "نتوقع أن ملاذ شمسية",
        "سيبث مثل هذا الغضب؟",
        "",
        "حـ-حـ-حالة طارئة!",
        "تهاجماني وظهري مستدير؟",
        "اقتربا يا أخوي الجبن الخارقين!",
        "",
        "بدء اللعبة  |  لعبة جديدة",
        "الأدوات  |  العتاد  |  خريطة بينبين"
    ]

    all_line_codes = [shape_line(l) for l in test_lines]
    img = render_codes_to_image(all_line_codes, line_spacing=16)

    # Save 1:1 and 4x scaled
    out_1x = 'C:/Users/user/Desktop/game/rooyin_test_preview_1x.png'
    out_4x = 'C:/Users/user/Desktop/game/rooyin_test_preview_4x.png'
    img.save(out_1x)

    img_4x = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
    img_4x.save(out_4x)

    # Copy to artifact directory for presentation
    art_path = 'C:/Users/user/.gemini/antigravity/brain/bb742f28-9080-409b-82bd-6fe93eab7c66/rooyin_test_preview_4x.png'
    img_4x.save(art_path)
    print(f'Saved preview image to {out_4x} and {art_path}')
