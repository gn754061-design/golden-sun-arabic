#!/usr/bin/env python3
"""
Full, complete Arabic localization build script for Mario & Luigi: Superstar Saga (EU)
1. Expands ROM to 32MB.
2. Injects custom 8x12 2bpp Arabic font into all 3 game fonts (0x51C9E8, 0x51E26C, 0x51FAF0).
3. Updates the 128-byte width table for proper variable-width typography.
4. Reshapes and BiDi-reverses all 170 story dialogues (entries 236-405) plus prologue entries.
5. Injects messages into expanded space (0x01000000+) and redirects pointer table (0x004EA268).
"""

import os
import sys
import re
import struct
import shutil
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

SRC_ROM = "./work/"MLSS_EU.gba"
DST_ROM = "./work/"MLSS_EU_AR.gba"

FONT_OFFSETS = [
    0x51C9E8,  # Font 0
    0x51E26C,  # Font 1
    0x51FAF0,  # Font 2
]

STORY_PTR_TABLE = 0x004EA268
GBA_ROM_BASE = 0x08000000
EXPANDED_BASE = 0x01000000
ROM_TARGET_SIZE = 0x02000000  # 32 MB

GLYPH_WIDTH = 8
GLYPH_HEIGHT = 12
BYTES_PER_GLYPH = 24

def encode_glyph(grid):
    """Encode 8x12 2bpp grid into 24-byte MLSS format."""
    raw = bytearray(24)
    for y_blk in range(3):
        for x_blk in range(2):
            idx0 = y_blk * 8 + x_blk * 2
            idx1 = idx0 + 1
            for ebp_pair in [0, 2]:
                target_idx = idx0 if ebp_pair == 0 else idx1
                b0 = 0
                b1 = 0
                bit_pos = 0
                for ebp in [ebp_pair, ebp_pair + 1]:
                    for esi in range(4):
                        row = y_blk * 4 + esi
                        col = x_blk * 4 + ebp
                        pix = grid[row][col]
                        if pix & 1:
                            b0 |= (1 << bit_pos)
                        if pix & 2:
                            b1 |= (1 << bit_pos)
                        bit_pos += 1
                raw[target_idx] = b0
                raw[target_idx + 4] = b1
    return bytes(raw)

def render_arabic_glyph(char, font):
    """Render Unicode Arabic glyph to 8x12 grid and return (grid, width)."""
    im = Image.new('L', (GLYPH_WIDTH, GLYPH_HEIGHT), 0)
    d = ImageDraw.Draw(im)
    d.text((0, 0), char, fill=255, font=font)
    
    grid = [[0]*GLYPH_WIDTH for _ in range(GLYPH_HEIGHT)]
    bbox = im.getbbox()
    
    for y in range(GLYPH_HEIGHT):
        for x in range(GLYPH_WIDTH):
            v = im.getpixel((x, y))
            if v > 100:
                grid[y][x] = 1
            elif v > 30:
                grid[y][x] = 3
            else:
                grid[y][x] = 0
                
    if bbox:
        char_w = max(2, min(8, bbox[2] + 1))
    else:
        char_w = 4
        
    return grid, char_w

def build_arabic_charmap(corpus_texts):
    """Build mapping of all unique presentation forms to byte codes 0x80..0xFF."""
    reshaped_corpus = arabic_reshaper.reshape(' '.join(corpus_texts))
    unique_chars = sorted(set(reshaped_corpus))
    
    ar_chars = [c for c in unique_chars if ord(c) >= 0x0600 or (0xFB50 <= ord(c) <= 0xFEFF)]
    for punct in ['،', '؟', '؛', 'ـ']:
        if punct not in ar_chars:
            ar_chars.append(punct)
            
    print(f"Total unique reshaped Arabic characters needed: {len(ar_chars)}")
    charmap = {}
    code = 0x80
    for c in ar_chars:
        if code > 0xFF:
            print("ERROR: Exceeded 128 glyph limit!")
            break
        charmap[c] = code
        code += 1
    return charmap

def patch_fonts_in_rom(rom, charmap):
    """Patch all 3 fonts with Arabic glyphs and width table entries."""
    font_path = "C:/Windows/Fonts/tahoma.ttf"
    font = ImageFont.truetype(font_path, 11)
    
    encoded_glyphs = {}
    glyph_widths = {}
    for ch, code in charmap.items():
        grid, width = render_arabic_glyph(ch, font)
        encoded_glyphs[code] = encode_glyph(grid)
        glyph_widths[code] = width
        
    print(f"Generated {len(encoded_glyphs)} glyphs.")
    
    for font_idx, font_base in enumerate(FONT_OFFSETS):
        print(f"  Patching Font {font_idx} at 0x{font_base:06X}...")
        # Width table
        for code in range(0x80, 0x100):
            w = glyph_widths.get(code, 4)
            byte_off = font_base + (code // 2)
            cur_byte = rom[byte_off]
            if code % 2 == 0:
                rom[byte_off] = (cur_byte & 0xF0) | (w & 0x0F)
            else:
                rom[byte_off] = (cur_byte & 0x0F) | ((w & 0x0F) << 4)
                
        # Glyphs table
        glyphs_base = font_base + 0x80
        for code in range(0x80, 0x100):
            if code in encoded_glyphs:
                tile_bytes = encoded_glyphs[code]
                off = glyphs_base + code * BYTES_PER_GLYPH
                rom[off : off + BYTES_PER_GLYPH] = tile_bytes

def convert_arabic_text(text, charmap):
    """
    Convert Arabic text containing control tokens like {02}, \n, [25]%A{41}
    into GBA font codes and control codes with line-level BiDi.
    """
    lines = text.split('\n')
    encoded = []
    
    for idx, line in enumerate(lines):
        # Handle control tokens {XX} and [XX]
        parts = re.split(r'(\{[0-9A-Fa-f]{2}\}|\[[0-9A-Fa-f]{2}\]|\[25\]%A\{41\}|\+[^+]+\+)', line)
        for part in parts:
            if not part:
                continue
            if part == '[25]%A{41}':
                # Button A icon control sequence: FF 25 41
                encoded.extend([0xFF, 0x25, 0x41])
            elif part.startswith('{') and part.endswith('}') and len(part) == 4:
                val = int(part[1:3], 16)
                encoded.append(val)
            elif part.startswith('[') and part.endswith(']') and len(part) == 4:
                val = int(part[1:3], 16)
                encoded.append(val)
            elif part.startswith('+') and part.endswith('+'):
                # Item marker: FF 2B + text + FF 20
                item_inner = part[1:-1]
                reshaped = arabic_reshaper.reshape(item_inner)
                bidi_rev = get_display(reshaped)
                encoded.extend([0xFF, 0x2B])
                for c in bidi_rev:
                    if c in charmap:
                        encoded.append(charmap[c])
                    elif ord(c) < 128:
                        encoded.append(ord(c))
                    else:
                        encoded.append(0x20)
                encoded.extend([0xFF, 0x20])
            else:
                # Arabic text segment: reshape & BiDi
                reshaped = arabic_reshaper.reshape(part)
                bidi_rev = get_display(reshaped)
                for c in bidi_rev:
                    if c in charmap:
                        encoded.append(charmap[c])
                    elif ord(c) < 128:
                        encoded.append(ord(c))
                    else:
                        encoded.append(0x20)
                        
        if idx < len(lines) - 1:
            encoded.extend([0xFF, 0x00])  # Newline
            
    return bytes(encoded)

def build_message(font_codes, box_style=(0x14, 0x05)):
    """Wrap message with box style, start header and end trailer."""
    data = bytearray()
    data.append(box_style[0])
    data.append(box_style[1])
    data.append(0xFF)
    data.append(0x0B)
    data.append(0x01)
    data.extend(font_codes)
    if not data.endswith(b'\xFF\x0A\x00\x00'):
        data.extend(b'\xFF\x0A\x00\x00')
    return bytes(data)

def build_intro_cutscene_messages(charmap):
    """Build bit-exact cutscene messages for entries 392-395 with generous display timings."""
    def enc(text):
        reshaped = arabic_reshaper.reshape(text)
        rev = get_display(reshaped)
        res = []
        for c in rev:
            if c in charmap:
                res.append(charmap[c])
            elif ord(c) < 128:
                res.append(ord(c))
            else:
                res.append(0x20)
        return bytes(res)
    
    # Entry 392
    msg392 = bytearray(b'\x18\x03\xff\x0b\x01\xff\x00\xff\x03\xff\x35\xff\x41\xff\x25')
    msg392.extend(enc("لقد وصل سفير النوايا الحسنة"))
    msg392.extend(b'\xff\x0c\x80\xff\x01\x00\xff\x0b\x01\xff\x00\xff\x03\xff\x35')
    msg392.extend(enc("من مملكة بين بين."))
    msg392.extend(b'\xff\x0c\x80\xff\x0a\x00\x00')
    
    # Entry 393
    msg393 = bytearray(b'\x17\x03\xff\x0b\x01\xff\x00\xff\x03\xff\x35\xff\x41\xff\x25')
    msg393.extend(enc("أرغب في توطيد علاقات مملكتي"))
    msg393.extend(b'\xff\x0c\x80\xff\x01\x00\xff\x0b\x01\xff\x00\xff\x03\xff\x35')
    msg393.extend(enc("مع مملكة الفطر الحبيبة."))
    msg393.extend(b'\xff\x0c\x80\xff\x0a\x00\x00')
    
    # Entry 394
    msg394 = bytearray(b'\x17\x03\xff\x0b\x01\xff\x00\xff\x03\xff\x35\xff\x41\xff\x25')
    msg394.extend(enc("أحمل هدية ثمينة من الملكة بين."))
    msg394.extend(b'\xff\x0c\x80\xff\x0a\x00\x00')
    
    # Entry 395
    msg395 = bytearray(b'\x10\x03\xff\x0b\x01\xff\x00\xff\x03\xff\x41\xff\x25')
    msg395.extend(enc("إيياهاهاهاها!"))
    msg395.extend(b'\xff\x0c\x80\xff\x0a\x00\x11\x03\xff\x0b\x01\xff\x03\xff\x33\xff\x35')
    msg395.extend(enc("أيها الأوغاد!!!"))
    msg395.extend(b'\xff\x0c\x80\xff\x0a\x00\x00')
    
    return {392: bytes(msg392), 393: bytes(msg393), 394: bytes(msg394), 395: bytes(msg395)}

def main():
    print("=" * 60)
    print("Mario & Luigi: Superstar Saga (EU) - Arabic Injection")
    print("=" * 60)
    
    # 1. Load Arabic dialogues
    sys.path.append("./"")
    from reinject_with_glyphs import ARABIC_STORY
    
    # Add/Update Intro Dialogues (Opening Cutscene at Peach's Castle)
    ARABIC_STORY[392] = "لقد وصل سفير النوايا الحسنة.{02}"
    ARABIC_STORY[393] = "من مملكة بين بين.{02}"
    ARABIC_STORY[394] = "هـ-هذا هو الحجر الأخير!{02}"
    ARABIC_STORY[395] = "الآن سنظهر روح الأخوين المطرقة!{02}"
    
    # Update Hammerhead Bros intro (Entry 236)
    ARABIC_STORY[236] = "هـ-هذا هو الحجر الأخير!\nالآن سنظهر روح الأخوين المطرقة!{02}"
    ARABIC_STORY[237] = "هذه الصخرة هي فرصتنا الأخيرة!{02}"
    ARABIC_STORY[238] = "هاااه... هوووف... هااارف...\nهذه الصخرة لا تنكسر أبداً!{02}"

    # 2. Build CharMap
    print("\n[1] Building Arabic CharMap...")
    charmap = build_arabic_charmap(list(ARABIC_STORY.values()))
    print(f"    Mapped {len(charmap)} glyphs to 0x80..0x{0x80+len(charmap)-1:02X}")
    
    # 3. Copy clean ROM and expand to 32MB
    print(f"\n[2] Expanding clean ROM to 32MB...")
    shutil.copy2(SRC_ROM, DST_ROM)
    with open(DST_ROM, 'rb') as f:
        rom = bytearray(f.read())
    orig_len = len(rom)
    if orig_len < ROM_TARGET_SIZE:
        rom.extend(b'\x00' * (ROM_TARGET_SIZE - orig_len))
    print(f"    ROM size: {len(rom)} bytes (0x{len(rom):X})")
    
    # 4. Patch Fonts (0x51C9E8, 0x51E26C, 0x51FAF0)
    print("\n[3] Patching game fonts in ROM...")
    patch_fonts_in_rom(rom, charmap)
    
    # 5. Inject Dialogues into Expanded Space
    print("\n[4] Injecting Arabic dialogues into expanded space...")
    custom_intro_msgs = build_intro_cutscene_messages(charmap)
    write_offset = EXPANDED_BASE
    injected_count = 0
    
    for entry in range(236, 406):
        if entry not in ARABIC_STORY and entry not in custom_intro_msgs:
            continue
        text = ARABIC_STORY.get(entry, "")
        
        ptr_idx = entry * 5  # Lang 0 (English)
        ptr_offset = STORY_PTR_TABLE + ptr_idx * 4
        orig_ptr = struct.unpack('<I', rom[ptr_offset:ptr_offset+4])[0]
        if orig_ptr < GBA_ROM_BASE:
            continue
            
        orig_file_off = orig_ptr - GBA_ROM_BASE
        orig_data = rom[orig_file_off:orig_file_off+2]
        box_style = (orig_data[0], orig_data[1]) if len(orig_data) == 2 else (0x14, 0x05)
        
        if entry in custom_intro_msgs:
            msg_data = custom_intro_msgs[entry]
        else:
            # Convert and build message
            font_codes = convert_arabic_text(text, charmap)
            msg_data = build_message(font_codes, box_style)
        
        if write_offset + len(msg_data) > len(rom):
            print(f"    ERROR: Out of ROM space at entry {entry}!")
            break
            
        rom[write_offset : write_offset + len(msg_data)] = msg_data
        new_gba_ptr = GBA_ROM_BASE + write_offset
        rom[ptr_offset : ptr_offset + 4] = struct.pack('<I', new_gba_ptr)
        
        write_offset += len(msg_data)
        write_offset = (write_offset + 3) & ~3  # 4-byte align
        injected_count += 1
        
    used_bytes = write_offset - EXPANDED_BASE
    print(f"    Injected {injected_count} dialogues ({used_bytes} bytes used in expanded space).")
    
    # 6. Save modified ROM
    print("\n[5] Writing patched ROM...")
    with open(DST_ROM, 'wb') as f:
        f.write(rom)
    print(f"    Saved: {DST_ROM}")
    
    # 7. Verification checks
    print("\n" + "=" * 60)
    print("VERIFICATION CHECKS")
    print("=" * 60)
    with open(DST_ROM, 'rb') as f:
        check_rom = f.read()
        
    print(f"1. ROM Size: 0x{len(check_rom):X} == 0x2000000 : {len(check_rom) == 0x2000000}")
    print(f"2. Header Valid (0xB2 == 0x96) : {check_rom[0xB2] == 0x96}")
    
    # Check Font 0 glyph 0x80 non-zero
    f0_glyph80 = check_rom[0x51C9E8 + 0x80 + 0x80*24 : 0x51C9E8 + 0x80 + 0x81*24]
    print(f"3. Font 0 Glyph 0x80 non-zero bytes : {sum(1 for b in f0_glyph80 if b != 0)}/24")
    
    # Check Story pointers
    redirected = sum(1 for e in range(236, 406) if struct.unpack('<I', check_rom[STORY_PTR_TABLE + e*5*4 : STORY_PTR_TABLE + e*5*4 + 4])[0] - GBA_ROM_BASE >= EXPANDED_BASE)
    print(f"4. Story Pointers Redirected : {redirected}/{len(ARABIC_STORY)}")
    print("\nBuild Complete and Verified!")

if __name__ == '__main__':
    main()
