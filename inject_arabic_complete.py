#!/usr/bin/env python3
"""
Complete Arabic injection for MLSS_EU.gba
Steps:
1. Copy clean ROM and expand to 32MB
2. Generate and inject Arabic font tiles (0xA0-0xFF)
3. Inject Arabic story text for English entries (index % 5 == 0) into expanded space
4. Update pointer table
"""

import struct
import csv
import shutil

# ============================================================
# CONSTANTS
# ============================================================
SRC_ROM = r"C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU.gba"
DST_ROM = r"C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.gba"
TRANSLATION_TSV = r"C:\Users\user\Desktop\game\Games\game\arabic_translation_merged.tsv"

FONT_TILES_ADDR = 0x00947538
WIDTH_TABLE_ADDR = 0x009418F0
STORY_PTR_TABLE = 0x004EA268
GBA_ROM_BASE = 0x08000000
EXPANDED_BASE = 0x01000000  # File offset for expanded space (0x09000000 in GBA address)

# ============================================================
# ARABIC CHARACTER -> FONT CODE MAPPING (0xA0-0xFF)
# ============================================================
arabic_map = {
    ' ': 0x20,
    # Arabic letters (isolated forms) - 0xA0-0xBC
    '\u0627': 0xA0, '\u0628': 0xA1, '\u062A': 0xA2, '\u062B': 0xA3,
    '\u062C': 0xA4, '\u062D': 0xA5, '\u062E': 0xA6, '\u062F': 0xA7,
    '\u0630': 0xA8, '\u0631': 0xA9, '\u0632': 0xAA, '\u0633': 0xAB,
    '\u0634': 0xAC, '\u0635': 0xAD, '\u0636': 0xAE, '\u0637': 0xAF,
    '\u0638': 0xB0, '\u0639': 0xB1, '\u063A': 0xB2, '\u0641': 0xB3,
    '\u0642': 0xB4, '\u0643': 0xB5, '\u0644': 0xB6, '\u0645': 0xB7,
    '\u0646': 0xB8, '\u0647': 0xB9, '\u0648': 0xBA, '\u0649': 0xBB,
    '\u064A': 0xBC,
    # Hamza variants
    '\u0623': 0xBD, '\u0625': 0xBE, '\u0622': 0xBF, '\u0621': 0xC0,
    '\u0629': 0xC1, '\u0624': 0xC2, '\u0626': 0xC3,
    # Tatweel/kashida
    '\u0640': 0xC4,
    # Diacritics (map to same as base or combine)
    '\u064B': 0xC5, '\u064D': 0xC6, '\u064E': 0xC7, '\u064F': 0xC8,
    '\u0650': 0xC9, '\u0651': 0xCA,
    # Punctuation
    '.': 0xCB, ',': 0xCC, '!': 0xCD, '?': 0xCE, ':': 0xCF, ';': 0xD0,
    '(': 0xD1, ')': 0xD2, '[': 0xD3, ']': 0xD4, '{': 0xD5, '}': 0xD6,
    '-': 0xD7, '_': 0xD8, '+': 0xD9, '=': 0xDA, '*': 0xDB, '/': 0xDC,
    '\\': 0xDD, '|': 0xDE, '<': 0xDF, '>': 0xE0, '@': 0xE1, '#': 0xE2,
    '$': 0xE3, '%': 0xE4, '^': 0xE5, '&': 0xE6, '~': 0xE7, '`': 0xE8,
    '"': 0xE9, "'": 0xEA,
    # Digits
    '0': 0xEB, '1': 0xEC, '2': 0xED, '3': 0xEE, '4': 0xEF,
    '5': 0xF0, '6': 0xF1, '7': 0xF2, '8': 0xF3, '9': 0xF4,
    # Arabic punctuation
    '\u060C': 0xF5, '\u061B': 0xF6, '\u061F': 0xF7, '\u066A': 0xF8,
    # Latin E (from control codes like {1E})
    'E': 0xF9, 'e': 0xFA,
}

# ============================================================
# FONT TILE GENERATION
# ============================================================
def create_arabic_tile(code):
    """Create an 8x8 4bpp tile with a unique pattern per character code"""
    tile = bytearray(32)
    for row in range(8):
        for plane in range(4):
            byte_val = 0
            for col in range(8):
                bit = 7 - col
                # Create a unique pattern based on code and position
                seed = (code * 13 + row * 7 + col * 11) % 16
                pixel_val = seed % 4
                if pixel_val & (1 << plane):
                    byte_val |= (1 << bit)
            tile[row * 4 + plane] = byte_val
    return bytes(tile)

def generate_all_arabic_tiles():
    """Generate 96 tiles for codes 0xA0-0xFF"""
    tiles = {}
    for code in range(0xA0, 0x100):
        tiles[code] = create_arabic_tile(code)
    return tiles

# ============================================================
# TEXT CONVERSION
# ============================================================
def arabic_text_to_font_codes(text):
    """Convert Arabic text string to font code bytes"""
    codes = []
    i = 0
    while i < len(text):
        ch = text[i]
        # Handle control codes like {02}, {1E}, {12}, etc.
        if ch == '{' and i + 3 < len(text) and text[i+3] == '}':
            # Extract control code
            ctrl = text[i:i+4]  # e.g., {02}
            try:
                num = int(text[i+1:i+3], 16)
                # Map common control codes to single bytes
                if num == 0x01:
                    codes.append(0x01)
                elif num == 0x02:
                    codes.append(0x02)
                elif num == 0x0A:
                    codes.append(0x0A)
                elif num == 0x0B:
                    codes.append(0x0B)
                elif num == 0x0C:
                    codes.append(0x0C)
                elif num == 0x0D:
                    codes.append(0x0D)
                elif num == 0x0E:
                    codes.append(0x0E)
                elif num == 0x0F:
                    codes.append(0x0F)
                elif num == 0x10:
                    codes.append(0x10)
                elif num == 0x11:
                    codes.append(0x11)
                elif num == 0x12:
                    codes.append(0x12)
                elif num == 0x13:
                    codes.append(0x13)
                elif num == 0x14:
                    codes.append(0x14)
                elif num == 0x15:
                    codes.append(0x15)
                elif num == 0x16:
                    codes.append(0x16)
                elif num == 0x17:
                    codes.append(0x17)
                elif num == 0x18:
                    codes.append(0x18)
                elif num == 0x19:
                    codes.append(0x19)
                elif num == 0x1A:
                    codes.append(0x1A)
                elif num == 0x1B:
                    codes.append(0x1B)
                elif num == 0x1C:
                    codes.append(0x1C)
                elif num == 0x1D:
                    codes.append(0x1D)
                elif num == 0x1E:
                    codes.append(0x1E)
                elif num == 0x1F:
                    codes.append(0x1F)
                else:
                    # Fallback: encode as individual chars
                    for c in ctrl:
                        codes.append(arabic_map.get(c, 0x20))
            except:
                # Fallback
                for c in ctrl:
                    codes.append(arabic_map.get(c, 0x20))
            i += 4
        else:
            code = arabic_map.get(ch, 0x20)
            codes.append(code)
            i += 1
    return codes

def build_message_data(font_codes, box_style=(0x14, 0x05)):
    """Build complete message data with control codes"""
    data = bytearray()
    # Message box style (2 bytes)
    data.append(box_style[0])
    data.append(box_style[1])
    # Start text: FF 0B 01
    data.append(0xFF)
    data.append(0x0B)
    data.append(0x01)
    # Font codes
    data.extend(font_codes)
    # End: FF 0A 00 00
    data.append(0xFF)
    data.append(0x0A)
    data.append(0x00)
    data.append(0x00)
    return bytes(data)

# ============================================================
# MAIN INJECTION
# ============================================================
def main():
    print("=" * 60)
    print("MLSS_EU.gba Arabic Injection")
    print("=" * 60)
    
    # Step 1: Copy clean ROM and expand to 32MB
    print("\n[1] Copying clean ROM and expanding to 32MB...")
    shutil.copy2(SRC_ROM, DST_ROM)
    
    with open(DST_ROM, 'rb') as f:
        rom = bytearray(f.read())
    
    original_size = len(rom)
    target_size = 0x02000000  # 32MB
    padding = target_size - original_size
    rom.extend(b'\x00' * padding)
    
    print(f"    Original: {original_size} bytes (0x{original_size:X})")
    print(f"    Expanded: {len(rom)} bytes (0x{len(rom):X})")
    print(f"    Padding added: {padding} bytes (0x{padding:X})")
    
    # Verify header
    print("\n[2] Verifying GBA header...")
    header = rom[:0xC0]
    game_code = header[0xAC:0xB0].decode('ascii', errors='replace')
    fixed_val = header[0xB2]
    print(f"    Game code: {game_code}")
    print(f"    Fixed value (0xB2): 0x{fixed_val:02X} {'OK' if fixed_val == 0x96 else 'BAD'}")
    
    # Step 3: Generate and inject Arabic font tiles
    print("\n[3] Generating Arabic font tiles (0xA0-0xFF)...")
    arabic_tiles = generate_all_arabic_tiles()
    print(f"    Generated {len(arabic_tiles)} tiles")
    
    print("    Injecting font tiles at 0x{:08X}...".format(FONT_TILES_ADDR))
    for code in range(0xA0, 0x100):
        offset = FONT_TILES_ADDR + code * 32
        rom[offset:offset+32] = arabic_tiles[code]
    
    # Update width table (already 6 for 0xA0-0xFF, but ensure)
    for code in range(0xA0, 0x100):
        rom[WIDTH_TABLE_ADDR + code] = 6
    print(f"    Width table updated at 0x{WIDTH_TABLE_ADDR:08X}")
    
    # Step 4: Load translations
    print("\n[4] Loading Arabic translations...")
    translations = {}
    with open(TRANSLATION_TSV, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        next(reader)
        for row in reader:
            if len(row) >= 2:
                try:
                    idx = int(row[0])
                    translations[idx] = row[1]
                except:
                    pass
    print(f"    Loaded {len(translations)} translations")
    
    # Step 5: Inject Arabic story text for English entries (index % 5 == 0)
    print("\n[5] Injecting Arabic story text for English entries...")
    print("    English entries are at pointer indices where (index % 5 == 0)")
    print("    Story entries start at pointer index 1180 (entry 236)")
    
    # Expanded space starts at file offset 0x01000000 (GBA address 0x09000000)
    write_offset = EXPANDED_BASE
    updated_pointers = []
    
    # Process English story entries (index % 5 == 0, starting from 1180)
    # Entry index = pointer_index // 5
    # English is language 0, so pointer_index % 5 == 0
    for ptr_idx in range(1180, 5000, 5):  # Every 5th entry starting from 1180
        entry_idx = ptr_idx // 5
        
        # Read original pointer
        ptr_offset = STORY_PTR_TABLE + ptr_idx * 4
        if ptr_offset + 4 > len(rom):
            break
        orig_ptr = struct.unpack("<I", rom[ptr_offset:ptr_offset+4])[0]
        if orig_ptr == 0:
            continue
        
        orig_file_offset = orig_ptr - GBA_ROM_BASE
        if orig_file_offset < 0 or orig_file_offset >= original_size:
            continue
        
        # Check if translation exists for this entry
        if entry_idx not in translations:
            continue
        
        arabic_text = translations[entry_idx]
        
        # Convert to font codes
        font_codes = arabic_text_to_font_codes(arabic_text)
        if not font_codes:
            continue
        
        # Build message data
        msg_data = build_message_data(font_codes)
        
        # Check space
        if write_offset + len(msg_data) > len(rom):
            print(f"    WARNING: Expanded space full at entry {entry_idx}")
            break
        
        # Write Arabic text to expanded space
        rom[write_offset:write_offset+len(msg_data)] = msg_data
        
        # Calculate new GBA pointer
        new_gba_ptr = GBA_ROM_BASE + write_offset
        
        # Update pointer table for English (lang 0)
        rom[ptr_offset:ptr_offset+4] = struct.pack("<I", new_gba_ptr)
        
        updated_pointers.append((entry_idx, ptr_idx, orig_ptr, new_gba_ptr, write_offset, len(msg_data), arabic_text[:50]))
        
        write_offset += len(msg_data)
        
        # Align to 4 bytes
        write_offset = (write_offset + 3) & ~3
    
    print(f"    Injected {len(updated_pointers)} Arabic story entries")
    print(f"    Used {write_offset - EXPANDED_BASE} bytes of expanded space")
    print(f"    Remaining expanded space: {len(rom) - write_offset} bytes")
    
    # Step 6: Write modified ROM
    print("\n[6] Writing modified ROM...")
    with open(DST_ROM, 'wb') as f:
        f.write(rom)
    print(f"    Written to {DST_ROM}")
    
    # Step 7: Print verification report
    print("\n" + "=" * 60)
    print("VERIFICATION REPORT")
    print("=" * 60)
    
    print("\nFirst 5 updated pointers:")
    for i, (entry_idx, ptr_idx, orig_ptr, new_ptr, file_off, msg_len, text_preview) in enumerate(updated_pointers[:5]):
        print(f"  Entry {entry_idx} (ptr_idx {ptr_idx}):")
        print(f"    Original ptr: 0x{orig_ptr:08X} (file 0x{orig_ptr - GBA_ROM_BASE:08X})")
        print(f"    New ptr:      0x{new_ptr:08X} (file 0x{file_off:08X})")
        print(f"    Message len:  {msg_len} bytes")
        print(f"    Text: {text_preview}")
        
        # Verify the written data
        written_data = rom[file_off:file_off+min(32, msg_len)]
        hex_str = " ".join(f"{b:02X}" for b in written_data)
        print(f"    Written bytes: {hex_str}")
    
    print(f"\nTotal Arabic story entries injected: {len(updated_pointers)}")
    print(f"Expanded space usage: 0x{write_offset - EXPANDED_BASE:X} / 0x{len(rom) - EXPANDED_BASE:X} bytes")
    
    # Verify font tiles
    print("\nFont tile verification (first 5 Arabic tiles):")
    for code in range(0xA0, 0xA5):
        offset = FONT_TILES_ADDR + code * 32
        tile_data = rom[offset:offset+16]
        hex_str = " ".join(f"{b:02X}" for b in tile_data)
        print(f"  0x{code:02X}: {hex_str}")
    
    print("\n=== INJECTION COMPLETE ===")

if __name__ == '__main__':
    main()