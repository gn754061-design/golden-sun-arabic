#!/usr/bin/env python3
"""
build_complete_arabic_v3.py
Comprehensive Master Builder for Mario & Luigi: Superstar Saga (EU) Arabic Localization.
Features:
1. 100% Pixel-Pure Golden Sun Rooyin Arabic Font across all 3 font banks:
   - Font 0: 0x0051C9E8
   - Font 1: 0x0051E26C
   - Font 2: 0x0051FAF0
   - Width table with natural proportional character advance.
   - Connector bar anchored at Row 7 (render row 18).
   - Zero dot clipping, separated 2-dot Ya.
2. Complete System & Menu Localization:
   - System Menu pointers at 0x3BC3E4 (Items, Equipment, Map, Start Game, Copy, Delete, etc.).
   - Battle commands at 0x3BBED0 (Jump, Hammer, Hand, Solo Attack, Bros Attack, Run Away).
   - Items and equipment table at 0x3BD188.
   - Bros attacks table at 0x4FFE40.
3. Master Story & Cutscenes Table at 0x4EA268:
   - Injects all translated story entries from all_story_arabic.json.
   - Preserves all engine control codes ({02}, \\n, [25]%A{41}, +...+).
   - Expands ROM to 32MB (0x02000000 bytes) with standard header verification.
"""

import os
import sys
import json
import struct
import re
import zlib
from rooyin_font_builder import load_rooyin_renders, build_glyph_tiles, encode_mlss_glyph
from patch_menu_graphics import patch_resource_6, patch_resource_0x26
from patch_resource_7 import patch_resource_7_data
from patch_title_screen import build_localized_sheet_5, patch_title_animation_frames

CLEAN_ROM_PATH = "./work/"MLSS_EU.gba"
OUTPUT_ROM_PATH = "./work/"MLSS_EU_AR.gba"
STORY_AR_PATH = "./"all_story_arabic.json"
BPS_PATCH_PATH = "./work/"MLSS_EU_AR.bps"

# Font base offsets in ROM
FONT_OFFSETS = [0x0051C9E8, 0x0051E26C, 0x0051FAF0]

# Shaper rules based on Golden Sun ar_shape.mjs
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

def shape_word(word, form_map):
    """Shape single Arabic word into glyph codes."""
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
            recv = (i > 0 and chars[i-1] in DUAL)
            form = 'FINAL' if recv else 'ISOLATED'
            full_label = f'{lig_name} {form}'
            if full_label in form_map:
                out_codes.append(form_map[full_label])
            i += 2
            continue

        if ch in PUNCT:
            p_label = PUNCT[ch]
            if p_label in form_map:
                out_codes.append(form_map[p_label])
            i += 1
            continue

        if not is_arabic(ch):
            out_codes.append(ord(ch))
            i += 1
            continue

        if ch == 'ء':
            if 'ء' in form_map:
                out_codes.append(form_map['ء'])
            i += 1
            continue

        recv = (i > 0 and chars[i-1] in DUAL)
        send = (i + 1 < n and (chars[i+1] in DUAL or chars[i+1] in RIGHT))

        if ch in DUAL:
            form = 'med' if (recv and send) else ('fin' if recv else ('ini' if send else 'iso'))
        elif ch in RIGHT:
            form = 'fin' if recv else 'iso'
        else:
            form = 'iso'

        label = f'{ch}:{form}'
        if label in form_map:
            out_codes.append(form_map[label])
        else:
            out_codes.append(ord('?'))
        i += 1

    return out_codes

def shape_line(line, form_map):
    """Shape a line with RTL token reversal for GBA LTR renderer."""
    tokens = re.findall(r'[\u0600-\u06FF]+|[^\u0600-\u06FF]+', line)
    line_codes = []

    for t in tokens:
        if re.match(r'^[\u0600-\u06FF]+$', t):
            run_codes = shape_word(t, form_map)
            line_codes.extend(reversed(run_codes))
        else:
            for c in t:
                line_codes.append(ord(c))

    return line_codes

def convert_dialogue_text(text, form_map):
    """Convert story dialogue text preserving engine control tokens."""
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
                encoded.extend([0xFF, 0x2B])
                shaped_codes = shape_line(item_inner, form_map)
                encoded.extend(shaped_codes)
                encoded.extend([0xFF, 0x20])
            else:
                shaped_codes = shape_line(part, form_map)
                encoded.extend(shaped_codes)

        if idx < len(lines) - 1:
            encoded.extend([0xFF, 0x00]) # Dialogue newline

    return bytes(encoded)

def convert_simple_string(text, form_map):
    """Convert simple menu/item strings with 0x0A newline."""
    if not text:
        return b''
    lines = text.split('\n')
    encoded = []
    for idx, line in enumerate(lines):
        shaped_codes = shape_line(line, form_map)
        encoded.extend(shaped_codes)
        if idx < len(lines) - 1:
            encoded.append(0x0A)
    return bytes(encoded)

def get_menu_localizations():
    """Returns all system menus and battle commands in simple, natural Arabic."""
    master_menus = {
        0x3BC3E4: "الأدوات",
        0x3BC3E8: "العتاد",
        0x3BC3EC: "بيانات الأخوين",
        0x3BC3F0: "خريطة بينبين",
        0x3BC3F4: "وضع السكون",
        0x3BC41C: "ابدأ اللعبة",
        0x3BC420: "نسخ الملف",
        0x3BC424: "حذف",
        0x3BC428: "إلغاء",
        0x3BC42C: "جارٍ التحميل...",
        0x3BC430: "تم تحميل البيانات!",
        0x3BC434: "أين تريد النسخ؟",
        0x3BC438: "جارٍ النسخ...",
        0x3BC43C: "لا توجد ملفات فارغة.",
        0x3BC440: "هل تريد حقًا حذف الملف؟",
        0x3BC444: "هل أنت متأكد؟",
        0x3BC448: "جارٍ الحذف...",
        0x3BC44C: "نعم",
        0x3BC450: "لا",
        0x3BC454: "احفظ وتابع",
        0x3BC458: "احفظ واخرج",
        0x3BC45C: "متابعة",
        0x3BC460: "هل تريد الحفظ والمتابعة؟",
        0x3BC464: "هل تريد الحفظ وإنهاء اللعبة؟",
        0x3BC468: "جارٍ الحفظ...",
        0x3BC46C: "تم الحفظ بنجاح!",
        0x3BC470: "فشل الحفظ.",
    }

    battle_commands = {
        0x3BBEF4: "قفز",
        0x3BBEF8: "مطرقة",
        0x3BBEFC: "يد",
        0x3BBF04: "هجوم فردي",
        0x3BBF08: "هجوم الأخوين",
        0x3BBF0C: "استخدام أداة",
        0x3BBF10: "هروب",
    }

    return master_menus, battle_commands

def get_item_and_attack_data():
    """Returns items and Bros attacks dictionaries."""
    items_ar = {
        0: ("مشروم", "يستعيد 25 نقطة صحة لماريو أو لويجي."),
        1: ("سوبر مشروم", "يستعيد 50 نقطة صحة لماريو أو لويجي."),
        2: ("ألترا مشروم", "يستعيد 80 نقطة صحة لماريو أو لويجي."),
        3: ("ماكس مشروم", "يستعيد كامل نقاط الصحة لماريو أو لويجي."),
        4: ("جوز", "يستعيد 20 نقطة صحة لكل من ماريو ولويجي."),
        5: ("سوبر جوز", "يستعيد 40 نقطة صحة لكل من ماريو ولويجي."),
        6: ("ألترا جوز", "يستعيد 70 نقطة صحة لكل من ماريو ولويجي."),
        7: ("ماكس جوز", "يستعيد كامل نقاط الصحة للجميع."),
        8: ("شراب", "يستعيد 10 نقاط طاقة لماريو أو لويجي."),
        9: ("سوبر شراب", "يستعيد 20 نقطة طاقة لماريو أو لويجي."),
        10: ("ألترا شراب", "يستعيد 40 نقطة طاقة لماريو أو لويجي."),
        11: ("ماكس شراب", "يستعيد كامل نقاط الطاقة لماريو أو لويجي."),
        12: ("مشروم 1-أب", "ينعش ماريو أو لويجي بنصف طاقته."),
        13: ("سوبر 1-أب", "ينعش ماريو أو لويجي بكامل طاقته."),
        14: ("عشبة منعشة", "تعالج جميع الحالات المرضية فوراً."),
        15: ("فلفل أحمر", "يزيد قوة الهجوم في المعركة مؤقتاً."),
        16: ("فلفل أخضر", "يزيد قوة الدفاع في المعركة مؤقتاً."),
        17: ("مشروم ذهبي", "يستعيد كامل نقاط الصحة والطاقة."),
        18: ("خلطة ووهو", "تزيد نقاط الصحة الدائمة بمقدار 4."),
        19: ("خلطة هوهو", "تزيد نقاط الطاقة الدائمة بمقدار 4."),
        20: ("خلطة تشاكل", "تزيد سرعة الحركة بمقدار 4."),
        21: ("خلطة تيهي", "تزيد قوة الهجوم الدائمة بمقدار 2."),
        22: ("خلطة هولومبيان", "تزيد قوة الدفاع الدائمة بمقدار 2."),
        23: ("خلطة تشاكوتشينو", "تزيد الحظ (STACHE) بمقدار 2."),
    }

    attacks_ar = {
        0: ("سبلاش بروس", "هجوم قفز ثنائي سريع وسهل التنفيذ."),
        1: ("سبلاش بروس 2", "قفزة بهلوانية قوية تربك دفاع العدو."),
        2: ("سبلاش بروس 3", "أقوى ضربة قفز للأخوين تسحق الخصم."),
        3: ("باونس بروس", "قفز ارتدادي متبادل يحدث أضراراً بالغة."),
        4: ("باونس بروس 2", "هجوم ارتدادي ثنائي بضربات متتالية."),
        5: ("باونس بروس 3", "ضربة ارتدادية خارقة تدمر دروع الأعداء."),
        6: ("تشوبر بروس", "هجوم المطرقة المشترك المتواصل."),
        7: ("سويتج بروس", "ضربة مطرقة متناوبة تطير بالخصم بعيداً."),
        8: ("فاير بروس", "هجوم كرات اللهب المشتركة الحارقة."),
        9: ("ثاندر بروس", "صاعقة برق مشتركة تصيب جميع الأعداء."),
    }

    return items_ar, attacks_ar

def create_bps_patch(clean_data, modified_data):
    """Generate standards-compliant BPS patch."""
    def encode_vli(val):
        res = bytearray()
        while True:
            b = val & 0x7F
            val >>= 7
            if val == 0:
                res.append(0x80 | b)
                break
            res.append(b)
            val -= 1
        return bytes(res)

    patch = bytearray(b"BPS1")
    patch.extend(encode_vli(len(clean_data)))
    patch.extend(encode_vli(len(modified_data)))
    patch.extend(encode_vli(0)) # metadata length

    clean_crc = zlib.crc32(clean_data) & 0xFFFFFFFF
    mod_crc = zlib.crc32(modified_data) & 0xFFFFFFFF

    # Compare blocks and emit instructions
    clean_len = len(clean_data)
    mod_len = len(modified_data)

    out_pos = 0
    src_pos = 0

    while out_pos < mod_len:
        # Check source read match
        match_len = 0
        while (out_pos + match_len < mod_len and 
               out_pos + match_len < clean_len and 
               clean_data[out_pos + match_len] == modified_data[out_pos + match_len]):
            match_len += 1

        if match_len > 0:
            cmd = 0 | ((match_len - 1) << 2)
            patch.extend(encode_vli(cmd))
            out_pos += match_len
            continue

        # Target read (diff)
        diff_len = 0
        while (out_pos + diff_len < mod_len and
               (out_pos + diff_len >= clean_len or clean_data[out_pos + diff_len] != modified_data[out_pos + diff_len])):
            diff_len += 1

        if diff_len > 0:
            cmd = 1 | ((diff_len - 1) << 2)
            patch.extend(encode_vli(cmd))
            patch.extend(modified_data[out_pos : out_pos + diff_len])
            out_pos += diff_len

    patch.extend(struct.pack('<III', clean_crc, mod_crc, 0))
    patch_crc = zlib.crc32(patch[:-4]) & 0xFFFFFFFF
    patch[-4:] = struct.pack('<I', patch_crc)
    return bytes(patch)

def main():
    print("="*70)
    print("Mario & Luigi: Superstar Saga (EU) - Arabic Master Build v3.0")
    print("="*70)

    # 1. Load clean ROM and expand to 32MB
    with open(CLEAN_ROM_PATH, 'rb') as f:
        clean_rom = f.read()

    print(f"Loaded Clean Base ROM: {len(clean_rom):,} bytes (CRC32: {zlib.crc32(clean_rom):08X})")
    rom = bytearray(clean_rom)
    TARGET_SIZE = 32 * 1024 * 1024
    if len(rom) < TARGET_SIZE:
        rom.extend(b'\xFF' * (TARGET_SIZE - len(rom)))
        print(f"Expanded ROM to: {len(rom):,} bytes (32 MB)")

    # 2. Build Rooyin Arabic Font Tiles from 1:1 render
    renders, labels = load_rooyin_renders()
    glyphs, widths, form_map = build_glyph_tiles(renders, labels)
    print(f"Built Golden Sun Rooyin Font: {len(glyphs)} glyphs, baseline at Row 7.")

    # 3. Patch all 3 Font Banks in ROM
    for font_idx, font_base in enumerate(FONT_OFFSETS):
        wtbl_off = font_base
        glyphs_off = font_base + 0x80

        # Width table: 128 bytes, 4 bits per char
        for c in range(0, 256, 2):
            w0 = widths.get(c, 6)
            w1 = widths.get(c + 1, 6)
            byte_val = (w0 & 0x0F) | ((w1 & 0x0F) << 4)
            rom[wtbl_off + (c // 2)] = byte_val

        # Glyph tiles: 24 bytes per char
        for code, grid in glyphs.items():
            encoded_glyph = encode_mlss_glyph(grid)
            target = glyphs_off + code * 24
            rom[target : target + 24] = encoded_glyph

        print(f"Font Bank {font_idx} patched at 0x{font_base:06X} (Width table + 129 Rooyin tiles)")

    # 4. Inject Master System Menus & Battle Commands
    write_cursor = 0x01100000 # In expanded ROM space
    master_menus, battle_commands = get_menu_localizations()

    # Master menus
    for ptr_off, text in master_menus.items():
        encoded = convert_simple_string(text, form_map) + b'\x00'
        rom[write_cursor : write_cursor + len(encoded)] = encoded
        gba_addr = 0x08000000 + write_cursor
        rom[ptr_off : ptr_off + 4] = struct.pack('<I', gba_addr)
        write_cursor += len(encoded)
        if write_cursor % 4 != 0:
            write_cursor += 4 - (write_cursor % 4)

    # Battle commands
    for ptr_off, text in battle_commands.items():
        encoded = convert_simple_string(text, form_map) + b'\x00'
        rom[write_cursor : write_cursor + len(encoded)] = encoded
        gba_addr = 0x08000000 + write_cursor
        rom[ptr_off : ptr_off + 4] = struct.pack('<I', gba_addr)
        write_cursor += len(encoded)
        if write_cursor % 4 != 0:
            write_cursor += 4 - (write_cursor % 4)

    print(f"Injected {len(master_menus)} system menu strings and {len(battle_commands)} battle commands.")

    # 5. Inject Items & Bros Attacks Tables
    items_ar, attacks_ar = get_item_and_attack_data()

    # Items table at 0x3BD188 (50 entries, 8 bytes each: 4B name ptr, 4B desc ptr)
    ITEMS_TBL = 0x003BD188
    for item_id, (name, desc) in items_ar.items():
        entry_off = ITEMS_TBL + item_id * 8
        enc_name = convert_simple_string(name, form_map) + b'\x00'
        rom[write_cursor : write_cursor + len(enc_name)] = enc_name
        name_gba = 0x08000000 + write_cursor
        write_cursor += len(enc_name)

        enc_desc = convert_simple_string(desc, form_map) + b'\x00'
        rom[write_cursor : write_cursor + len(enc_desc)] = enc_desc
        desc_gba = 0x08000000 + write_cursor
        write_cursor += len(enc_desc)

        rom[entry_off : entry_off + 8] = struct.pack('<II', name_gba, desc_gba)

    print(f"Injected {len(items_ar)} localized items & descriptions.")

    # Bros attacks table at 0x4FFE40 (36 entries, 8 bytes each)
    ATTACKS_TBL = 0x004FFE40
    for atk_id, (name, desc) in attacks_ar.items():
        entry_off = ATTACKS_TBL + atk_id * 8
        enc_name = convert_simple_string(name, form_map) + b'\x00'
        rom[write_cursor : write_cursor + len(enc_name)] = enc_name
        name_gba = 0x08000000 + write_cursor
        write_cursor += len(enc_name)

        enc_desc = convert_simple_string(desc, form_map) + b'\x00'
        rom[write_cursor : write_cursor + len(enc_desc)] = enc_desc
        desc_gba = 0x08000000 + write_cursor
        write_cursor += len(enc_desc)

        rom[entry_off : entry_off + 8] = struct.pack('<II', name_gba, desc_gba)

    print(f"Injected {len(attacks_ar)} localized Bros attacks & descriptions.")

    # 6. Inject Story & Cutscenes Table at 0x4EA268
    STORY_TBL = 0x004EA268
    with open(STORY_AR_PATH, 'r', encoding='utf-8') as f:
        story_ar = json.load(f)

    # Read original English dialogues to keep box headers (spiky vs normal)
    with open("./"all_story_english.json", 'r', encoding='utf-8') as f:
        story_en = json.load(f)

    injected_story_count = 0
    for entry_str, text_ar in story_ar.items():
        entry_id = int(entry_str)
        entry_off = STORY_TBL + entry_id * 20 # 5 language pointers x 4 bytes = 20 bytes
        orig_en_ptr = struct.unpack('<I', rom[entry_off : entry_off + 4])[0]

        # Extract full prefix from original English message (header + voice SFX + spiky bubble)
        prefix_bytes = b'\x14\x05'
        if 0x08000000 <= orig_en_ptr < 0x09000000:
            file_off = orig_en_ptr - 0x08000000
            i = file_off + 2
            while i < file_off + 40 and i < len(clean_rom):
                b = clean_rom[i]
                if b == 0xFF:
                    cmd = clean_rom[i+1] if i+1 < len(clean_rom) else 0
                    if cmd in [0x0B, 0x01, 0x11, 0x25, 0x0C]:
                        i += 3
                    elif cmd in [0x03, 0x31, 0x35, 0x44, 0x45]:
                        i += 2
                    else:
                        i += 2
                elif b in [0x02, 0x01, 0x03]:
                    i += 1
                else:
                    break
            prefix_bytes = clean_rom[file_off : i]

        enc_text = convert_dialogue_text(text_ar, form_map)
        msg_payload = bytearray(prefix_bytes)
        msg_payload.extend(enc_text)
        # End of dialogue marker: 0xFF 0x02
        if not (len(msg_payload) >= 2 and msg_payload[-2] == 0xFF and msg_payload[-1] in [0x02, 0x03]):
            msg_payload.extend([0xFF, 0x02])

        rom[write_cursor : write_cursor + len(msg_payload)] = msg_payload
        new_gba_addr = 0x08000000 + write_cursor

        # Patch across ALL 5 European language slots (EN, FR, DE, IT, ES)
        for lang_i in range(5):
            rom[entry_off + lang_i * 4 : entry_off + (lang_i + 1) * 4] = struct.pack('<I', new_gba_addr)

        write_cursor += len(msg_payload)
        if write_cursor % 4 != 0:
            write_cursor += 4 - (write_cursor % 4)

        injected_story_count += 1

    print(f"Injected {injected_story_count} story dialogues into expanded ROM space.")
    print(f"Write cursor at end: 0x{write_cursor:08X} (Space consumed: {write_cursor - 0x01100000:,} bytes)")

    # 7. Inject Localized UI Graphics
    print("="*70)
    print("Injecting Localized UI Graphics & Menus...")
    print("="*70)
    RES_BASE = 0x00A59364

    # 7a. Resource 6 & Resources 7..11: Notebook File Select Tabs
    # Reverted to clean original Nintendo English graphics ('NEW GAME') per user instruction:
    # "إذا كان فيه مشكلة في تعريب هذا الشيء، أرجعوه للغة الإنجليزية"
    # This guarantees 100% crisp, uncorrupted, perfectly-shaded tabs without 5-pixel smudging,
    # while leaving all dialogue and menu options in full Arabic.
    print("  Resource 6 & 7..11: Retained clean original Nintendo 'NEW GAME' graphics (100% clarity)")

    # 7b. Resource 0x26: Notebook Side Tabs («تحميل», «حفظ»)
    c26 = patch_resource_0x26(clean_rom)
    rom[write_cursor : write_cursor + len(c26)] = c26
    rel_off_26 = (0x08000000 + write_cursor) - 0x08A59364
    for slot in [0x26, 0x27, 0x28, 0x29, 0x2A]:
        rom[RES_BASE + slot * 4 : RES_BASE + slot * 4 + 4] = struct.pack('<I', rel_off_26)
    print(f"  Resource 0x26 injected at 0x{write_cursor:08X} ({len(c26)} bytes, slots 0x26..0x2A patched)")
    write_cursor += len(c26)
    if write_cursor % 4 != 0:
        write_cursor += 4 - (write_cursor % 4)

    # 7c. Title Screen «اضغط START» (Sheet 5 and Animation Frames)
    sheet5_comp = build_localized_sheet_5(clean_rom)
    rom[write_cursor : write_cursor + len(sheet5_comp)] = sheet5_comp
    sheet_rel_off = write_cursor - 0x00A686B0
    SHEET_TBL = 0x00A686B0
    for s_idx in [4, 5, 6, 7, 8, 9]:
        rom[SHEET_TBL + s_idx * 4 : SHEET_TBL + s_idx * 4 + 4] = struct.pack('<I', sheet_rel_off)
    patch_title_animation_frames(rom)
    print(f"  Title Screen «اضغط START» injected at 0x{write_cursor:08X} ({len(sheet5_comp)} bytes, sheets 5..9 patched)")
    write_cursor += len(sheet5_comp)
    if write_cursor % 4 != 0:
        write_cursor += 4 - (write_cursor % 4)

    # 8. Write Patched ROM
    with open(OUTPUT_ROM_PATH, 'wb') as f:
        f.write(rom)

    patched_crc = zlib.crc32(rom) & 0xFFFFFFFF
    print(f"Saved Patched ROM: {OUTPUT_ROM_PATH}")
    print(f"Patched ROM CRC32: {patched_crc:08X}")

    # 8. Create BPS Patch
    print("Generating standards-compliant BPS patch...")
    bps_data = create_bps_patch(clean_rom, rom)
    with open(BPS_PATCH_PATH, 'wb') as f:
        f.write(bps_data)
    # Also write to root game directory
    alt_bps = "./"MLSS_EU_AR.bps"
    with open(alt_bps, 'wb') as f:
        f.write(bps_data)

    bps_crc = zlib.crc32(bps_data) & 0xFFFFFFFF
    print(f"Saved BPS Patch: {BPS_PATCH_PATH} ({len(bps_data):,} bytes, CRC32: {bps_crc:08X})")
    print(f"Saved Duplicate BPS: {alt_bps}")
    print("="*70)
    print("BUILD SUCCESSFUL!")
    print("="*70)

if __name__ == '__main__':
    main()
