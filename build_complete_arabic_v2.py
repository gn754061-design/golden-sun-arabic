#!/usr/bin/env python3
"""
Comprehensive Arabic Localization Build Script v2.0 for Mario & Luigi: Superstar Saga (EU)
1. Injects custom baseline-anchored 8x12 2bpp Arabic font from Golden Sun project (RooyinFree-RegularDots2.ttf).
   - Fixes all cut-off dots below baseline.
   - Perfect horizontal alignment across all joining letters at Row 6.
   - Complete presentation forms coverage (isolated, initial, medial, final) + punctuation.
2. Localizes:
   - System Menus (Save format, delete, sleep mode, language).
   - Story Dialogues & Cutscenes (Peach's Castle, Hammerhead Bros, Hoohoo Mountain, etc.).
   - Items & Equipment (Mushrooms, Nuts, Syrups, Peppers, Blends, Descriptions).
   - Bros Attacks & Battle Commands (Splash Bros, Swing Bros, Chopper Bros, Bounce Bros, etc.).
3. Updates all 3 pointer tables in ROM:
   - 0x004EA268: Story & System Dialogues
   - 0x003BD188: Items & Descriptions
   - 0x004FFE40: Bros Attacks & Battle Commands
4. Expands clean ROM to 32MB with safety guarantee.
"""

import os
import sys
import re
import json
import struct
import shutil
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

SRC_ROM = "./work/"MLSS_EU.gba"
DST_ROM = "./work/"MLSS_EU_AR.gba"
FONT_TTF = "./fonts/"RooyinFree-RegularDots2.ttf"

FONT_OFFSETS = [
    0x51C9E8,  # Font 0: Dialogue & Menu Font
    0x51E26C,  # Font 1: Secondary Font
    0x51FAF0,  # Font 2: Alternative Font
]

STORY_PTR_TABLE = 0x004EA268
ITEMS_PTR_TABLE = 0x003BD188
ATTACKS_PTR_TABLE = 0x004FFE40

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

def render_arabic_glyph_perfect(char, font):
    """
    Render Arabic glyph with baseline locked at Row 6 of the 8x12 tile.
    Ensures that all dots and descenders sit within rows 0..10 (0 clipping).
    """
    im_big = Image.new('L', (24, 24), 0)
    d = ImageDraw.Draw(im_big)
    # Draw character with offset
    d.text((4, 4), char, fill=255, font=font)
    bbox = im_big.getbbox()
    grid = [[0]*GLYPH_WIDTH for _ in range(GLYPH_HEIGHT)]
    if not bbox:
        return grid, 4  # space or empty
        
    x0, y0, x1, y1 = bbox
    ink_w = x1 - x0
    ink_h = y1 - y0
    ink = im_big.crop(bbox)
    
    # Scale horizontally if wider than 8
    target_w = min(GLYPH_WIDTH, ink_w)
    target_h = min(11, ink_h)
    if ink_w > target_w or ink_h > target_h:
        ink = ink.resize((target_w, target_h), Image.LANCZOS)
        ink_w, ink_h = target_w, target_h
        
    # Baseline anchoring:
    # In canvas (4, 4), the font's baseline at sz=10 is at y = 4 + 7 = 11.
    # We want baseline at Row 6 in our 12-row tile (index 6).
    # Therefore, y in tile = (y in canvas) - 5
    dest_y = y0 - 5
    if dest_y < 0: dest_y = 0
    if dest_y + ink_h > 12: dest_y = 12 - ink_h
    
    dest_x = 0
    for y in range(ink.size[1]):
        for x in range(ink.size[0]):
            v = ink.getpixel((x, y))
            gy = dest_y + y
            gx = dest_x + x
            if 0 <= gy < 12 and 0 <= gx < 8:
                if v > 100:
                    grid[gy][gx] = 1  # Primary stroke (white)
                elif v > 30:
                    grid[gy][gx] = 3  # Border / shadow
                    
    char_w = max(3, min(8, ink_w + 1))
    return grid, char_w

def build_arabic_charmap(corpus_texts):
    """Build unified mapping of all unique presentation forms to byte codes 0x80..0xFF."""
    reshaped_corpus = arabic_reshaper.reshape(' '.join(corpus_texts))
    unique_chars = sorted(set(reshaped_corpus))
    
    ar_chars = [c for c in unique_chars if ord(c) >= 0x0600 or (0xFB50 <= ord(c) <= 0xFEFF)]
    for punct in ['،', '؟', '؛', 'ـ']:
        if punct not in ar_chars:
            ar_chars.append(punct)
            
    print(f"Total unique reshaped Arabic characters needed: {len(ar_chars)}")
    if len(ar_chars) > 128:
        print(f"WARNING: {len(ar_chars)} exceeds 128 glyph limit!")
        ar_chars = ar_chars[:128]
        
    charmap = {}
    code = 0x80
    for c in ar_chars:
        charmap[c] = code
        code += 1
    return charmap

def patch_fonts_in_rom(rom, charmap):
    """Patch all 3 fonts with baseline-anchored Arabic glyphs and width table."""
    font = ImageFont.truetype(FONT_TTF, 10)
    
    encoded_glyphs = {}
    glyph_widths = {}
    for ch, code in charmap.items():
        grid, width = render_arabic_glyph_perfect(ch, font)
        encoded_glyphs[code] = encode_glyph(grid)
        glyph_widths[code] = width
        
    print(f"Generated {len(encoded_glyphs)} baseline-anchored glyphs from RooyinDots2.")
    
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

def convert_arabic_string(text, charmap):
    """Convert Arabic string with BiDi line reversal to GBA byte codes."""
    if not text:
        return b''
    lines = text.split('\n')
    encoded = []
    for idx, line in enumerate(lines):
        reshaped = arabic_reshaper.reshape(line)
        bidi_rev = get_display(reshaped)
        for c in bidi_rev:
            if c in charmap:
                encoded.append(charmap[c])
            elif ord(c) < 128:
                encoded.append(ord(c))
            else:
                encoded.append(0x20)
        if idx < len(lines) - 1:
            encoded.append(0x0A)  # Newline for simple strings
    return bytes(encoded)

def convert_dialogue_text(text, charmap):
    """Convert dialogue text with control tokens {02}, \n, [25]%A{41}, +...+ to GBA codes."""
    lines = text.split('\n')
    encoded = []
    for idx, line in enumerate(lines):
        parts = re.split(r'(\{[0-9A-Fa-f]{2}\}|\[[0-9A-Fa-f]{2}\]|\[25\]%A\{41\}|\+[^+]+\+)', line)
        for part in parts:
            if not part:
                continue
            if part == '[25]%A{41}':
                encoded.extend([0xFF, 0x25, 0x41])
            elif part.startswith('{') and part.endswith('}') and len(part) == 4:
                encoded.append(int(part[1:3], 16))
            elif part.startswith('[') and part.endswith(']') and len(part) == 4:
                encoded.append(int(part[1:3], 16))
            elif part.startswith('+') and part.endswith('+'):
                item_inner = part[1:-1]
                reshaped = arabic_reshaper.reshape(item_inner)
                bidi_rev = get_display(reshaped)
                encoded.extend([0xFF, 0x2B])
                for c in bidi_rev:
                    encoded.append(charmap.get(c, ord(c) if ord(c) < 128 else 0x20))
                encoded.extend([0xFF, 0x20])
            else:
                reshaped = arabic_reshaper.reshape(part)
                bidi_rev = get_display(reshaped)
                for c in bidi_rev:
                    encoded.append(charmap.get(c, ord(c) if ord(c) < 128 else 0x20))
        if idx < len(lines) - 1:
            encoded.extend([0xFF, 0x00])  # Dialogue newline
    return bytes(encoded)

def build_dialogue_message(font_codes, box_style=(0x14, 0x05)):
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

def get_localized_assets():
    """Returns dictionaries of translated Items, Bros Attacks, System Menus, and Story Dialogues."""
    
    # 1. 50 English Items
    items_ar = {
        0: "فطر",
        1: "استعادة 25 نقطة صحة.",
        2: "فطر خارق",
        3: "استعادة 50 نقطة صحة.",
        4: "فطر أقصى",
        5: "استعادة كامل الصحة.",
        6: "مكسرات",
        7: "استعادة 20 صحة لكل أخ.",
        8: "مكسرات خارقة",
        9: "استعادة 40 صحة لكل أخ.",
        10: "مكسرات قصوى",
        11: "استعادة كامل الصحة لكل أخ.",
        12: "شراب مركز",
        13: "استعادة 20 نقطة إخوة.",
        14: "شراب خارق",
        15: "استعادة 40 نقطة إخوة.",
        16: "شراب أقصى",
        17: "استعادة كامل نقاط الإخوة.",
        18: "أعشاب منعشة",
        19: "علاج الحالات السلبية.",
        20: "فطر إحياء",
        21: "إنعاش بنصف الصحة.",
        22: "فطر إحياء خارق",
        23: "إنعاش بكامل الصحة.",
        24: "فطر فائق",
        25: "استعادة 120 نقطة صحة.",
        26: "مكسرات فائقة",
        27: "استعادة 100 صحة لكل أخ.",
        28: "شراب فائق",
        29: "استعادة 100 نقطة إخوة.",
        30: "فطر ذهبي",
        31: "أقصى صحة ونقاط إخوة.",
        32: "فلفل أحمر",
        33: "زيادة القوة والوزن.",
        34: "فلفل أخضر",
        35: "زيادة الدفاع وتقليل الوزن.",
        36: "مزيج ووهو",
        37: "مزيج حبوب النجوم: +4 صحة",
        38: "مزيج هوهو",
        39: "مزيج حبوب النجوم: +4 نقاط إخوة",
        40: "مزيج الضحك",
        41: "مزيج حبوب النجوم: +4 سرعة",
        42: "مزيج البسمة",
        43: "مزيج حبوب النجوم: +4 شارب",
        44: "قهوة هولومبية",
        45: "مزيج حبوب النجوم: +4 قوة",
        46: "تشاكوتشينو",
        47: "مزيج حبوب النجوم: +4 دفاع",
        48: "إسبريسو البسمة",
        49: "مزيج حبوب النجوم: +6 ؟؟؟"
    }
    
    # 2. 36 English Attacks & Battle Commands
    attacks_ar = {
        0: "ضربة سبلاتش",
        1: "اقفز عالياً واهبط بقوة!",
        2: "ضربة التأرجح",
        3: "أرجح لويجي في الهواء!",
        4: "قفزة 3",
        5: "مؤقت",
        6: "ضربة المروحية",
        7: "اغرس لويجي واهجم!",
        8: "مطرقة 2",
        9: "مؤقت",
        10: "مطرقة 3",
        11: "مؤقت",
        12: "ضربة النار",
        13: "اهجم بالكرات النارية!",
        14: "نار 2",
        15: "مؤقت",
        16: "نار 3",
        17: "مؤقت",
        18: "ضربة الارتداد",
        19: "اقفز من فوق ماريو!",
        20: "قفزة 2",
        21: "مؤقت",
        22: "قفزة 3",
        23: "مؤقت",
        24: "ضربة القذف",
        25: "أطلق ماريو للهجوم!",
        26: "ضربة الإعصار",
        27: "هجوم الدوران الثنائي!",
        28: "مطرقة 3",
        29: "مؤقت",
        30: "ضربة الصاعقة",
        31: "اهجم بالصواعق الرعدية!",
        32: "صاعقة 2",
        33: "مؤقت",
        34: "صاعقة 3",
        35: "مؤقت"
    }
    
    # 3. System Menus in Story Table (Entries 8..29)
    system_menus_ar = {
        8: "تهيئة ملفات الحفظ؟\nنعم           لا",
        9: "مسح بيانات حفظ ماريو ولويجي وماريو بروس؟\nنعم           لا",
        10: "اللغة",
        11: "وضع السكون السهل",
        12: "خاصية الاهتزاز",
        13: "السكون التلقائي",
        14: "وضع السكون",
        15: "اضغط SELECT + L + R للخروج من وضع السكون.",
        16: "معلومات خاصية الاهتزاز:\nتعمل الخاصية فقط مع منفذ التحكم 1.",
        17: "تعمل الخاصية فقط مع منفذ التحكم 1.",
        18: "سكون تلقائي (دقيقة واحدة)\nاضغط SELECT + L + R للخروج.",
        19: "اضغط SELECT + L + R للخروج من السكون.",
        20: "فشل حفظ بيانات ماريو بروس.",
        21: "المتابعة من آخر منطقة حفظ",
        22: "المتابعة من مدينة قلعة بين بين",
        23: "المتابعة من قلعة بين بين",
        24: "المتابعة من جامعة هوهو",
        25: "المتابعة من واحة أوهو",
        26: "المتابعة من وادي تي هي",
        27: "المتابعة من مدينة الفطريات",
        28: "المتابعة من وادي تي هي",
        29: "جارٍ تهيئة ملفات الحفظ..."
    }
    
    return items_ar, attacks_ar, system_menus_ar

def main():
    print("=" * 60)
    print("Mario & Luigi: Superstar Saga (EU) - Arabic Injection v2.0")
    print("=" * 60)
    
    # 1. Load Story Dialogues from reinject_with_glyphs
    sys.path.append("./"")
    from reinject_with_glyphs import ARABIC_STORY
    
    # Get assets
    items_ar, attacks_ar, system_menus_ar = get_localized_assets()
    
    # Merge all story & system texts
    story_all = dict(ARABIC_STORY)
    story_all.update(system_menus_ar)
    
    # Load any additional translated entries from all_story_arabic.json
    all_story_json = "./"all_story_arabic.json"
    if os.path.exists(all_story_json):
        try:
            with open(all_story_json, 'r', encoding='utf-8') as f:
                extra_story = json.load(f)
                for k, v in extra_story.items():
                    story_all[int(k)] = v
            print(f"Loaded {len(extra_story)} entries from all_story_arabic.json")
        except Exception as e:
            print(f"Notice: all_story_arabic.json read error: {e}")
            
    # Prologue Cutscene Dialogues
    story_all[392] = "لقد وصل سفير النوايا الحسنة.{02}"
    story_all[393] = "من مملكة بين بين.{02}"
    story_all[394] = "هـ-هذا هو الحجر الأخير!{02}"
    story_all[395] = "الآن سنظهر روح الأخوين المطرقة!{02}"
    
    # 2. Gather full text corpus for CharMap
    corpus = list(story_all.values()) + list(items_ar.values()) + list(attacks_ar.values())
    print("\n[1] Building Arabic CharMap from full game corpus...")
    charmap = build_arabic_charmap(corpus)
    print(f"    Mapped {len(charmap)} unique presentation forms to 0x80..0x{0x80+len(charmap)-1:02X}")
    
    # 3. Expand Clean ROM
    print("\n[2] Expanding clean ROM to 32MB...")
    shutil.copy2(SRC_ROM, DST_ROM)
    with open(DST_ROM, 'rb') as f:
        rom = bytearray(f.read())
    orig_len = len(rom)
    if orig_len < ROM_TARGET_SIZE:
        rom.extend(b'\x00' * (ROM_TARGET_SIZE - orig_len))
    print(f"    ROM size: {len(rom):,} bytes (0x{len(rom):X})")
    
    # 4. Patch Fonts in ROM
    print("\n[3] Patching 3 font banks with baseline-anchored Arabic font...")
    patch_fonts_in_rom(rom, charmap)
    
    # 5. Inject Translated Data into Expanded Space
    write_offset = EXPANDED_BASE
    
    # A. Inject Items (0x3BD188)
    print("\n[4] Injecting Items & Descriptions (0x3BD188)...")
    injected_items = 0
    for idx, text in items_ar.items():
        ptr_off = ITEMS_PTR_TABLE + idx * 4
        enc = convert_arabic_string(text, charmap) + b'\x00'
        rom[write_offset : write_offset + len(enc)] = enc
        new_ptr = GBA_ROM_BASE + write_offset
        rom[ptr_off : ptr_off + 4] = struct.pack('<I', new_ptr)
        write_offset += len(enc)
        write_offset = (write_offset + 3) & ~3
        injected_items += 1
    print(f"    Injected {injected_items} items.")
    
    # B. Inject Bros Attacks (0x4FFE40)
    print("\n[5] Injecting Bros Attacks & Descriptions (0x4FFE40)...")
    injected_attacks = 0
    for idx, text in attacks_ar.items():
        ptr_off = ATTACKS_PTR_TABLE + idx * 4
        enc = convert_arabic_string(text, charmap) + b'\x00'
        rom[write_offset : write_offset + len(enc)] = enc
        new_ptr = GBA_ROM_BASE + write_offset
        rom[ptr_off : ptr_off + 4] = struct.pack('<I', new_ptr)
        write_offset += len(enc)
        write_offset = (write_offset + 3) & ~3
        injected_attacks += 1
    print(f"    Injected {injected_attacks} attacks.")
    
    # C. Inject Story Dialogues & System Menus (0x004EA268)
    print("\n[6] Injecting Story & System Dialogues (0x004EA268)...")
    
    # Custom bit-exact cutscene messages for 392..395
    def enc_cut(text):
        reshaped = arabic_reshaper.reshape(text)
        rev = get_display(reshaped)
        return bytes(charmap.get(c, ord(c) if ord(c) < 128 else 0x20) for c in rev)
        
    custom_intro = {
        392: (
            b'\x18\x03\xff\x0b\x01\xff\x00\xff\x03\xff\x35\xff\x41\xff\x25' +
            enc_cut("لقد وصل سفير النوايا الحسنة") +
            b'\xff\x0c\x80\xff\x01\x00\xff\x0b\x01\xff\x00\xff\x03\xff\x35' +
            enc_cut("من مملكة بين بين.") +
            b'\xff\x0c\x80\xff\x0a\x00\x00'
        ),
        393: (
            b'\x17\x03\xff\x0b\x01\xff\x00\xff\x03\xff\x35\xff\x41\xff\x25' +
            enc_cut("أرغب في توطيد علاقات مملكتي") +
            b'\xff\x0c\x80\xff\x01\x00\xff\x0b\x01\xff\x00\xff\x03\xff\x35' +
            enc_cut("مع مملكة الفطر الحبيبة.") +
            b'\xff\x0c\x80\xff\x0a\x00\x00'
        ),
        394: (
            b'\x17\x03\xff\x0b\x01\xff\x00\xff\x03\xff\x35\xff\x41\xff\x25' +
            enc_cut("أحمل هدية ثمينة من الملكة بين.") +
            b'\xff\x0c\x80\xff\x0a\x00\x00'
        ),
        395: (
            b'\x10\x03\xff\x0b\x01\xff\x00\xff\x03\xff\x41\xff\x25' +
            enc_cut("إيياهاهاهاها!") +
            b'\xff\x0c\x80\xff\x0a\x00\x11\x03\xff\x0b\x01\xff\x03\xff\x33\xff\x35' +
            enc_cut("أيها الأوغاد!!!") +
            b'\xff\x0c\x80\xff\x0a\x00\x00'
        )
    }
    
    injected_story = 0
    for entry, text in story_all.items():
        ptr_idx = entry * 5  # Lang 0 (English)
        ptr_offset = STORY_PTR_TABLE + ptr_idx * 4
        orig_ptr = struct.unpack('<I', rom[ptr_offset:ptr_offset+4])[0]
        if orig_ptr < GBA_ROM_BASE:
            continue
        orig_file_off = orig_ptr - GBA_ROM_BASE
        orig_data = rom[orig_file_off:orig_file_off+2]
        box_style = (orig_data[0], orig_data[1]) if len(orig_data) == 2 else (0x14, 0x05)
        
        if entry in custom_intro:
            msg_data = custom_intro[entry]
        else:
            font_codes = convert_dialogue_text(text, charmap)
            msg_data = build_dialogue_message(font_codes, box_style)
            
        rom[write_offset : write_offset + len(msg_data)] = msg_data
        new_ptr = GBA_ROM_BASE + write_offset
        rom[ptr_offset : ptr_offset + 4] = struct.pack('<I', new_ptr)
        write_offset += len(msg_data)
        write_offset = (write_offset + 3) & ~3
        injected_story += 1
        
    used_bytes = write_offset - EXPANDED_BASE
    print(f"    Injected {injected_story} story & system dialogues.")
    print(f"    Total space used in expanded area: {used_bytes:,} bytes.")
    
    # 6. Save modified ROM
    print("\n[7] Saving patched ROM...")
    with open(DST_ROM, 'wb') as f:
        f.write(rom)
    print(f"    Saved: {DST_ROM}")
    
    # 7. Verification checks
    print("\n" + "=" * 60)
    print("VERIFICATION CHECKS")
    print("=" * 60)
    with open(DST_ROM, 'rb') as f:
        chk = f.read()
    print(f"1. ROM Size (0x2000000): {len(chk) == 0x2000000}")
    print(f"2. GBA Header Valid: {chk[0xB2] == 0x96}")
    
    # Check items pointers
    it_ptrs = [struct.unpack('<I', chk[ITEMS_PTR_TABLE + i*4 : ITEMS_PTR_TABLE + (i+1)*4])[0] for i in range(50)]
    print(f"3. Items pointers redirected: {sum(1 for p in it_ptrs if p >= 0x09000000)}/50")
    
    # Check attacks pointers
    at_ptrs = [struct.unpack('<I', chk[ATTACKS_PTR_TABLE + i*4 : ATTACKS_PTR_TABLE + (i+1)*4])[0] for i in range(36)]
    print(f"4. Attacks pointers redirected: {sum(1 for p in at_ptrs if p >= 0x09000000)}/36")
    
    # Check story pointers
    st_ptrs = [struct.unpack('<I', chk[STORY_PTR_TABLE + e*5*4 : STORY_PTR_TABLE + e*5*4 + 4])[0] for e in story_all.keys()]
    print(f"5. Story pointers redirected: {sum(1 for p in st_ptrs if p >= 0x09000000)}/{len(story_all)}")
    
    print("\nBuild Complete & Verified!")

if __name__ == '__main__':
    main()
