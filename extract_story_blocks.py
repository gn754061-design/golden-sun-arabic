#!/usr/bin/env python3
"""
Extract all story text blocks from MLSS_EU.gba
Story table at 0x084EA268 (file offset 0x004EA268) with 16 pointers
Each pointer points to a text block with format: width, height, text bytes..., FF 0A (newline), etc.
"""
import struct
from pathlib import Path

ROM_PATH = Path("./work/"MLSS_EU.gba")
STORY_TABLE_FILE_OFF = 0x004EA268
STORY_TABLE_ENTRIES = 16

def read_rom():
    with open(ROM_PATH, 'rb') as f:
        return f.read()

def file_offset_to_addr(offset):
    return 0x08000000 + offset

def addr_to_file_offset(addr):
    return addr - 0x08000000

def parse_text_block(rom, start_offset):
    """Parse a text block starting at file offset"""
    data = rom[start_offset:]
    if len(data) < 2:
        return None, 0
    
    width = data[0]
    height = data[1]
    offset = 2
    text_segments = []
    control_codes = []
    
    while offset < len(data):
        byte = data[offset]
        if byte == 0xFF:
            # Control code
            if offset + 1 < len(data):
                next_byte = data[offset + 1]
                control_codes.append((offset, 0xFF, next_byte))
                if next_byte == 0x00:  # End of text block
                    offset += 2
                    break
                offset += 2
            else:
                break
        elif byte == 0x00 and offset > 2:
            # Possible padding/end
            offset += 1
        else:
            # Regular text byte (8-bit character)
            text_segments.append((offset, byte))
            offset += 1
    
    return {
        'width': width,
        'height': height,
        'text_bytes': bytes([b for _, b in text_segments]),
        'text_segments': text_segments,
        'control_codes': control_codes,
        'raw_data': data[:offset],
        'size': offset
    }, offset

def extract_all_blocks(rom):
    """Extract all 16 story blocks from the pointer table"""
    # Read pointer table
    table_data = rom[STORY_TABLE_FILE_OFF:STORY_TABLE_FILE_OFF + STORY_TABLE_ENTRIES * 4]
    pointers = []
    for i in range(STORY_TABLE_ENTRIES):
        ptr = struct.unpack('<I', table_data[i*4:i*4+4])[0]
        pointers.append(ptr)
    
    print(f"Story table pointers:")
    for i, ptr in enumerate(pointers):
        print(f"  [{i}] 0x{ptr:08X} (file off 0x{ptr - 0x08000000:08X})")
    
    blocks = []
    for i, ptr in enumerate(pointers):
        file_off = ptr - 0x08000000
        block, size = parse_text_block(rom, file_off)
        if block:
            block['index'] = i
            block['pointer'] = ptr
            block['file_offset'] = file_off
            blocks.append(block)
            print(f"\nBlock {i} at 0x{file_off:08X}:")
            print(f"  Width: {block['width']}, Height: {block['height']}")
            print(f"  Size: {block['size']} bytes")
            print(f"  Text bytes: {len(block['text_bytes'])}")
            print(f"  Control codes: {len(block['control_codes'])}")
            # Show first few control codes
            for cc_offset, cc1, cc2 in block['control_codes'][:10]:
                print(f"    0x{cc_offset:04X}: FF {cc2:02X}")
            if len(block['control_codes']) > 10:
                print(f"    ... and {len(block['control_codes']) - 10} more")
            # Show text as hex
            print(f"  Text hex: {block['text_bytes'][:80].hex()}")
    
    return blocks

def main():
    rom = read_rom()
    print(f"ROM size: {len(rom):,} bytes")
    
    blocks = extract_all_blocks(rom)
    
    # Save blocks for translation
    import json
    with open('story_blocks.json', 'w', encoding='utf-8') as f:
        json.dump([
            {
                'index': b['index'],
                'pointer': hex(b['pointer']),
                'file_offset': b['file_offset'],
                'width': b['width'],
                'height': b['height'],
                'size': b['size'],
                'text_bytes': b['text_bytes'].hex(),
                'control_codes': [[hex(off), hex(c1), hex(c2)] for off, c1, c2 in b['control_codes']],
                'raw_data': b['raw_data'].hex()
            }
            for b in blocks
        ], f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved {len(blocks)} blocks to story_blocks.json")

if __name__ == '__main__':
    import struct
    main()