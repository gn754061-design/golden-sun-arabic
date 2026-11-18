#!/usr/bin/env python3
"""
Extended analysis: search entire ROM for story table references,
find text rendering function via Capstone, extract font/width tables.
"""
import sys
import struct
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_ARM
except ImportError:
    print("Capstone not installed. Install with: pip install capstone")
    sys.exit(1)

ROM_PATH = Path("./work/"MLSS_EU.gba")
STORY_TABLE_ADDR = 0x084EA268
STORY_TABLE_FILE_OFF = 0x004EA268
FONT_MATCH_OFFSET = 0x947528

def read_rom():
    with open(ROM_PATH, 'rb') as f:
        return f.read()

def file_offset_to_addr(offset):
    return 0x08000000 + offset

def addr_to_file_offset(addr):
    return addr - 0x08000000

def find_all_refs(rom, target_addr):
    """Find all references to target address in various forms"""
    results = []
    
    # 1. Direct 32-bit little-endian (memory address)
    le_bytes = struct.pack('<I', target_addr)
    pos = 0
    while True:
        pos = rom.find(le_bytes, pos)
        if pos == -1:
            break
        results.append(('LE32', pos, file_offset_to_addr(pos)))
        pos += 1
    
    # 2. Direct 32-bit big-endian
    be_bytes = struct.pack('>I', target_addr)
    pos = 0
    while True:
        pos = rom.find(be_bytes, pos)
        if pos == -1:
            break
        results.append(('BE32', pos, file_offset_to_addr(pos)))
        pos += 1
    
    # 3. File offset (0x004EA268)
    fo_bytes = struct.pack('<I', STORY_TABLE_FILE_OFF)
    pos = 0
    while True:
        pos = rom.find(fo_bytes, pos)
        if pos == -1:
            break
        results.append(('FILE_OFF', pos, file_offset_to_addr(pos)))
        pos += 1
    
    # 4. MOVW/MOVT pairs (lower 16 bits / upper 16 bits)
    # MOVW: 0xF240 0x0xxx (Thumb2) or 0xE300xxxx (ARM)
    # MOVT: 0xF2C0 0x0xxx (Thumb2) or 0xE340xxxx (ARM)
    low16 = target_addr & 0xFFFF
    high16 = (target_addr >> 16) & 0xFFFF
    
    # Search for low16 in MOVW immediate encoding
    # Thumb MOVW: 11110 0 1 0 0 1 0 0 0 0 0 0 0 0 0 0 | imm4 | 0 | imm3 | imm8
    # = 0xF240 | (imm4<<12) | (imm3<<8) | imm8
    # ARM MOVW: 1110 0011 0000 | rd | imm4 | 0 0 0 0 | imm3 | imm8
    
    return results

def disassemble_thumb(rom, addr, size):
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    md.detail = True
    offset = addr_to_file_offset(addr)
    code = rom[offset:offset+size]
    return list(md.disasm(code, addr))

def disassemble_arm(rom, addr, size):
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    md.detail = True
    offset = addr_to_file_offset(addr)
    code = rom[offset:offset+size]
    return list(md.disasm(code, addr))

def find_function_containing(rom, target_addr, search_start=0, search_end=None):
    """Find function that references target_addr by scanning code"""
    if search_end is None:
        search_end = len(rom)
    
    # First find all literal pool references
    refs = find_all_refs(rom, target_addr)
    print(f"Found {len(refs)} direct references to 0x{target_addr:08X}")
    for typ, off, addr in refs[:20]:
        print(f"  {typ}: file_off=0x{off:08X}, addr=0x{addr:08X}")
    
    # Now disassemble around each reference to find the function
    functions = []
    for typ, ref_off, ref_addr in refs:
        # Disassemble window around reference
        window_start = max(search_start, ref_off - 0x2000)
        window_end = min(search_end, ref_off + 0x2000)
        window_addr = file_offset_to_addr(window_start)
        
        # Try Thumb
        insns = disassemble_thumb(rom, window_addr, window_end - window_start)
        
        # Find the instruction that loads our target
        for i, insn in enumerate(insns):
            if insn.address > ref_addr + 4:
                break
            if insn.address <= ref_addr and insn.address + insn.size > ref_addr:
                # This instruction spans our reference - it's likely a LDR literal
                print(f"\n  >> Candidate at 0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
                # Print function context
                start_idx = max(0, i - 30)
                end_idx = min(len(insns), i + 50)
                print(f"     Function context (Thumb):")
                for j in range(start_idx, end_idx):
                    insn2 = insns[j]
                    marker = " >>> " if j == i else "     "
                    print(f"{marker}0x{insn2.address:08X}: {insn2.mnemonic:8s} {insn2.op_str}")
                
                # Find BL calls in this region
                bl_calls = []
                for j in range(start_idx, end_idx):
                    insn2 = insns[j]
                    if insn2.mnemonic in ('bl', 'blx'):
                        for op in insn2.operands:
                            if op.type == 1:  # immediate
                                bl_calls.append((insn2.address, op.imm))
                
                if bl_calls:
                    print(f"     BL calls:")
                    for ca, tgt in bl_calls:
                        print(f"       0x{ca:08X} -> BL 0x{tgt:08X}")
                
                functions.append({
                    'ref_type': typ,
                    'ref_offset': ref_off,
                    'insn_addr': insn.address,
                    'insns': insns[start_idx:end_idx],
                    'bl_calls': bl_calls
                })
                break
    
    return functions

def analyze_font_area(rom):
    """Detailed analysis of font tile area"""
    print(f"\n{'='*60}")
    print(f"FONT TILE AREA ANALYSIS: 0x{FONT_MATCH_OFFSET:08X}")
    print(f"{'='*60}")
    
    # Read larger area
    area_start = FONT_MATCH_OFFSET - 0x1000
    area_end = FONT_MATCH_OFFSET + 0x3000
    area_data = rom[area_start:area_end]
    match_rel = FONT_MATCH_OFFSET - area_start
    
    print(f"\nHex dump around match (relative offset 0x{match_rel:X}):")
    start = max(0, match_rel - 128)
    end = min(len(area_data), match_rel + 128)
    for i in range(start, end, 16):
        line = area_data[i:i+16]
        addr = area_start + i
        hex_str = ' '.join(f'{b:02X}' for b in line)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in line)
        marker = " <<< MATCH" if i <= match_rel < i + 16 else ""
        print(f"  0x{addr:08X}: {hex_str:<48} {ascii_str}{marker}")
    
    # Check for patterns - look for tile data structures
    print(f"\nSearching for tile patterns in 0x{area_start:08X}-0x{area_end:08X}...")
    
    # 4bpp tiles: look for non-zero 32-byte blocks
    tile_candidates = []
    for off in range(0, len(area_data) - 32, 4):
        block = area_data[off:off+32]
        non_zero = sum(1 for b in block if b != 0)
        if non_zero > 8:  # At least 8 non-zero bytes
            tile_candidates.append((area_start + off, non_zero, block[:16]))
    
    print(f"  Found {len(tile_candidates)} potential 4bpp tile blocks")
    for addr, nz, preview in tile_candidates[:10]:
        print(f"    0x{addr:08X}: {nz} non-zero bytes, preview: {' '.join(f'{b:02X}' for b in preview)}")
    
    # Check for width table pattern (array of bytes, typically 1-12 per char)
    print(f"\nScanning for width table (byte array with values 1-12)...")
    for off in range(0, len(area_data) - 256, 4):
        block = area_data[off:off+256]
        # Width tables typically have many values in range 1-12
        valid_widths = sum(1 for b in block if 1 <= b <= 12)
        if valid_widths > 100:  # At least 100 valid width bytes
            print(f"  Potential width table at 0x{area_start + off:08X}: {valid_widths}/256 valid width bytes")
            print(f"    First 32: {' '.join(f'{b:02X}' for b in block[:32])}")

def search_text_render_functions(rom):
    """Search for known text rendering patterns"""
    print(f"\n{'='*60}")
    print(f"SEARCHING FOR TEXT RENDER FUNCTIONS")
    print(f"{'='*60}")
    
    # Common patterns in GBA text rendering:
    # 1. CMP rX, #0xFF (check for control code)
    # 2. BL to font rendering function
    # 3. LDR from font table / width table
    
    # Search entire ROM for CMP #0xFF followed by BL
    # Thumb: CMP rN, #0xFF = 0x2NFF (if N<8) or 0xF01N 0x0F00 (Thumb2)
    # ARM: CMP rN, #0xFF = 0xE35N 0x00FF
    
    # Let's disassemble the whole ROM in chunks and look for patterns
    chunk_size = 0x10000
    for chunk_start in range(0, min(len(rom), 0x200000), chunk_size):
        chunk_end = min(chunk_start + chunk_size, len(rom))
        addr = file_offset_to_addr(chunk_start)
        
        insns = disassemble_thumb(rom, addr, chunk_end - chunk_start)
        
        for i, insn in enumerate(insns):
            # Look for CMP with 0xFF immediate
            if insn.mnemonic == 'cmp':
                for op in insn.operands:
                    if op.type == 1 and op.imm == 0xFF:
                        # Check nearby for BL calls
                        for j in range(max(0, i-5), min(len(insns), i+20)):
                            insn2 = insns[j]
                            if insn2.mnemonic in ('bl', 'blx'):
                                for op2 in insn2.operands:
                                    if op2.type == 1:
                                        print(f"  0x{insn.address:08X}: CMP #0xFF")
                                        print(f"  0x{insn2.address:08X}: BL 0x{op2.imm:08X}")
                                        # Print context
                                        for k in range(max(0, i-10), min(len(insns), i+15)):
                                            insn3 = insns[k]
                                            marker = " >> " if k in (i, j) else "    "
                                            print(f"{marker}0x{insn3.address:08X}: {insn3.mnemonic:8s} {insn3.op_str}")
                                        print()
                                        break

def main():
    print("=" * 60)
    print("MLSS_EU.gba Extended Font & Text Analysis")
    print("=" * 60)
    
    rom = read_rom()
    print(f"ROM size: {len(rom):,} bytes (0x{len(rom):X})")
    
    # Step 1: Find all references to story table
    print(f"\nSearching for story table address 0x{STORY_TABLE_ADDR:08X}...")
    functions = find_function_containing(rom, STORY_TABLE_ADDR)
    
    # Step 2: Analyze font area
    analyze_font_area(rom)
    
    # Step 3: Search for text render patterns
    search_text_render_functions(rom)
    
    # Step 4: Also search for the story table file offset directly
    print(f"\n{'='*60}")
    print(f"SEARCHING FOR FILE OFFSET 0x{STORY_TABLE_FILE_OFF:08X}")
    print(f"{'='*60}")
    refs = find_all_refs(rom, STORY_TABLE_FILE_OFF)
    print(f"Direct references to file offset: {len(refs)}")
    for typ, off, addr in refs[:20]:
        print(f"  {typ}: file_off=0x{off:08X}, addr=0x{addr:08X}")
    
    # Also check if there's a pointer table at the story table location
    print(f"\nStory table content at file offset 0x{STORY_TABLE_FILE_OFF:08X}:")
    table_data = rom[STORY_TABLE_FILE_OFF:STORY_TABLE_FILE_OFF+64]
    for i in range(0, len(table_data), 4):
        val = struct.unpack('<I', table_data[i:i+4])[0]
        print(f"  0x{STORY_TABLE_FILE_OFF+i:08X}: 0x{val:08X} (addr 0x{val:08X})")

if __name__ == '__main__':
    main()