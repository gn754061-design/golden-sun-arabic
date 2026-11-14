#!/usr/bin/env python3
"""
Analyze MLSS_EU.gba to find text rendering function, font table, and width table
using Capstone disassembly. No emulator, no Ghidra needed.
"""
import sys
import struct
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_ARM
except ImportError:
    print("Capstone not installed. Install with: pip install capstone")
    sys.exit(1)

ROM_PATH = Path(r"C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU.gba")
STORY_TABLE_ADDR = 0x084EA268
STORY_TABLE_BYTES = b'\x68\xA2\x4E\x08'  # Little-endian
SEARCH_RANGE_START = 0x000000
SEARCH_RANGE_END = 0x200000
FONT_MATCH_OFFSET = 0x947528
FONT_AREA_START = 0x940000
FONT_AREA_END = 0x960000
DISASM_WINDOW = 0x1000

def read_rom():
    with open(ROM_PATH, 'rb') as f:
        return f.read()

def file_offset_to_addr(offset):
    """Convert file offset to GBA memory address (0x08000000 base)"""
    return 0x08000000 + offset

def addr_to_file_offset(addr):
    """Convert GBA memory address to file offset"""
    return addr - 0x08000000

def find_literal_pool_refs(rom, target_bytes, start, end):
    """Find all occurrences of target_bytes in range"""
    refs = []
    pos = start
    while True:
        pos = rom.find(target_bytes, pos, end)
        if pos == -1:
            break
        refs.append(pos)
        pos += 1
    return refs

def disassemble_thumb(rom, addr, size):
    """Disassemble Thumb code at address"""
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    md.detail = True
    offset = addr_to_file_offset(addr)
    code = rom[offset:offset+size]
    return list(md.disasm(code, addr))

def disassemble_arm(rom, addr, size):
    """Disassemble ARM code at address"""
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    md.detail = True
    offset = addr_to_file_offset(addr)
    code = rom[offset:offset+size]
    return list(md.disasm(code, addr))

def analyze_function_at_ref(rom, ref_offset):
    """Analyze the function that references the story table"""
    ref_addr = file_offset_to_addr(ref_offset)
    print(f"\n=== Reference at file offset 0x{ref_offset:08X} (addr 0x{ref_addr:08X}) ===")
    
    # Disassemble window around the reference
    window_start = max(SEARCH_RANGE_START, ref_offset - DISASM_WINDOW)
    window_end = min(SEARCH_RANGE_END, ref_offset + DISASM_WINDOW)
    window_addr_start = file_offset_to_addr(window_start)
    
    # Try Thumb first (most GBA code is Thumb)
    insns = disassemble_thumb(rom, window_addr_start, window_end - window_start)
    
    # Find instructions that load the story table address
    for i, insn in enumerate(insns):
        # Look for LDR with literal pool reference to our address
        if insn.id in [0x5D, 0x5E]:  # LDR literal (Thumb)
            # Check operands for our target address
            for op in insn.operands:
                if op.type == 1:  # ARM_OP_IMM
                    if op.imm == STORY_TABLE_ADDR:
                        print(f"  Found LDR to story table at 0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
                        # Print surrounding instructions
                        start_idx = max(0, i - 20)
                        end_idx = min(len(insns), i + 40)
                        for j in range(start_idx, end_idx):
                            insn2 = insns[j]
                            marker = " >> " if j == i else "    "
                            print(f"{marker}0x{insn2.address:08X}: {insn2.mnemonic} {insn2.op_str}")
                        return insn.address, insns[start_idx:end_idx]
        
        # Also check for MOVW/MOVT pairs that construct the address
        if insn.mnemonic in ['movw', 'movt']:
            for op in insn.operands:
                if op.type == 1 and (op.imm & 0xFFFF) in [0x4EA2, 0x084E]:
                    print(f"  Found MOVW/MOVT at 0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
                    start_idx = max(0, i - 20)
                    end_idx = min(len(insns), i + 40)
                    for j in range(start_idx, end_idx):
                        insn2 = insns[j]
                        marker = " >> " if j == i else "    "
                        print(f"{marker}0x{insn2.address:08X}: {insn2.mnemonic} {insn2.op_str}")
                    return insn.address, insns[start_idx:end_idx]
    
    # Also try ARM mode
    insns_arm = disassemble_arm(rom, window_addr_start, window_end - window_start)
    for i, insn in enumerate(insns_arm):
        if insn.id in [0x4C, 0x4D]:  # LDR literal (ARM)
            for op in insn.operands:
                if op.type == 1 and op.imm == STORY_TABLE_ADDR:
                    print(f"  [ARM] Found LDR to story table at 0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
                    start_idx = max(0, i - 20)
                    end_idx = min(len(insns_arm), i + 40)
                    for j in range(start_idx, end_idx):
                        insn2 = insns_arm[j]
                        marker = " >> " if j == i else "    "
                        print(f"{marker}0x{insn2.address:08X}: {insn2.mnemonic} {insn2.op_str}")
                    return insn.address, insns_arm[start_idx:end_idx]
    
    return None, None

def find_bl_calls(insns, start_addr):
    """Find BL (Branch with Link) calls in disassembly"""
    calls = []
    for insn in insns:
        if insn.mnemonic == 'bl' or insn.mnemonic == 'blx':
            for op in insn.operands:
                if op.type == 1:  # Immediate
                    calls.append((insn.address, op.imm))
    return calls

def extract_literal_pools(rom, func_start, func_end):
    """Extract literal pool values from a function range"""
    pools = []
    # Literal pools are typically after function or between functions
    # Look for word-aligned addresses that look like pointers (0x08xxxxxx)
    offset_start = addr_to_file_offset(func_start)
    offset_end = addr_to_file_offset(func_end)
    for addr in range(offset_start & ~3, offset_end, 4):
        val = struct.unpack('<I', rom[addr:addr+4])[0]
        if 0x08000000 <= val <= 0x09FFFFFF:  # GBA ROM/WRAM range
            pools.append((file_offset_to_addr(addr), val))
    return pools

def analyze_font_area(rom):
    """Analyze the font tile area around 0x947528"""
    print(f"\n=== Font Tile Area Analysis (0x{FONT_AREA_START:08X} - 0x{FONT_AREA_END:08X}) ===")
    print(f"Match at file offset 0x{FONT_MATCH_OFFSET:08X}")
    
    # Read the area
    area_data = rom[FONT_AREA_START:FONT_AREA_END]
    match_rel = FONT_MATCH_OFFSET - FONT_AREA_START
    
    print(f"\nData around match (offset 0x{match_rel:04X} in area):")
    start = max(0, match_rel - 64)
    end = min(len(area_data), match_rel + 64)
    hexdump = area_data[start:end]
    for i in range(0, len(hexdump), 16):
        line = hexdump[i:i+16]
        addr = FONT_AREA_START + start + i
        hex_str = ' '.join(f'{b:02X}' for b in line)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in line)
        marker = " <<< MATCH" if (start + i) <= match_rel < (start + i + 16) else ""
        print(f"  0x{addr:08X}: {hex_str:<48} {ascii_str}{marker}")
    
    # Try rendering as 1bpp, 2bpp, 4bpp tiles
    print("\n--- Tile rendering attempts ---")
    tile_data = rom[FONT_MATCH_OFFSET:FONT_MATCH_OFFSET+0x800]  # 2KB = 128 8x8 tiles @ 4bpp
    
    # 1bpp: 8 bytes per 8x8 tile
    print(f"\n1bpp tiles (8 bytes each) at 0x{FONT_MATCH_OFFSET:08X}:")
    for t in range(min(16, len(tile_data)//8)):
        tile = tile_data[t*8:t*8+8]
        print(f"  Tile {t:3d}: {' '.join(f'{b:02X}' for b in tile)}")
        # Render
        for row in tile:
            print(f"    {''.join('#' if (row >> (7-c)) & 1 else '.' for c in range(8))}")
    
    # 2bpp: 16 bytes per 8x8 tile
    print(f"\n2bpp tiles (16 bytes each) at 0x{FONT_MATCH_OFFSET:08X}:")
    for t in range(min(16, len(tile_data)//16)):
        tile = tile_data[t*16:t*16+16]
        print(f"  Tile {t:3d}: {' '.join(f'{b:02X}' for b in tile)}")
        for row_pair in range(0, 16, 2):
            lo = tile[row_pair]
            hi = tile[row_pair+1]
            line = ''.join(
                '0123'[(hi >> (7-c)) & 1 * 2 + ((lo >> (7-c)) & 1)] 
                for c in range(8)
            )
            print(f"    {line}")
    
    # 4bpp: 32 bytes per 8x8 tile
    print(f"\n4bpp tiles (32 bytes each) at 0x{FONT_MATCH_OFFSET:08X}:")
    for t in range(min(8, len(tile_data)//32)):
        tile = tile_data[t*32:t*32+32]
        print(f"  Tile {t:3d}: {' '.join(f'{b:02X}' for b in tile)}")
        for row_pair in range(0, 32, 4):
            b0, b1, b2, b3 = tile[row_pair:row_pair+4]
            line = ''.join(
                '0123456789ABCDEF'[
                    ((b3 >> (7-c)) & 1) * 8 + 
                    ((b2 >> (7-c)) & 1) * 4 + 
                    ((b1 >> (7-c)) & 1) * 2 + 
                    ((b0 >> (7-c)) & 1)
                ] for c in range(8)
            )
            print(f"    {line}")
    
    # Check for LZ77 compression header
    print(f"\n--- Compression check at 0x{FONT_MATCH_OFFSET:08X} ---")
    header = rom[FONT_MATCH_OFFSET:FONT_MATCH_OFFSET+4]
    print(f"Header bytes: {' '.join(f'{b:02X}' for b in header)}")
    if header[0] & 0xF == 0x1:
        print("  Possible LZ77 (type 0x10)")
    elif header[0] & 0xF == 0x2:
        print("  Possible Huffman (type 0x20)")
    elif header[0] & 0xF == 0x3:
        print("  Possible RLE (type 0x30)")
    else:
        print("  No standard compression header detected")

def main():
    print("=" * 60)
    print("MLSS_EU.gba Font & Text Function Analysis")
    print("=" * 60)
    
    rom = read_rom()
    print(f"ROM size: {len(rom):,} bytes (0x{len(rom):X})")
    
    # Step 1: Find all references to story table address
    print(f"\nSearching for story table reference 0x{STORY_TABLE_ADDR:08X} ({STORY_TABLE_BYTES.hex().upper()})")
    print(f"Range: 0x{SEARCH_RANGE_START:08X} - 0x{SEARCH_RANGE_END:08X}")
    
    refs = find_literal_pool_refs(rom, STORY_TABLE_BYTES, SEARCH_RANGE_START, SEARCH_RANGE_END)
    print(f"Found {len(refs)} reference(s)")
    
    all_calls = []
    all_pools = []
    
    for ref in refs:
        func_addr, insns = analyze_function_at_ref(rom, ref)
        if func_addr and insns:
            # Find BL calls in this function
            calls = find_bl_calls(insns, func_addr)
            print(f"\n  BL calls from this function:")
            for call_addr, target in calls:
                print(f"    0x{call_addr:08X} -> BL 0x{target:08X}")
                all_calls.append((call_addr, target))
            
            # Extract literal pools
            pools = extract_literal_pools(rom, func_addr, func_addr + 0x200)
            print(f"\n  Literal pools near function:")
            for pool_addr, pool_val in pools:
                print(f"    0x{pool_addr:08X} = 0x{pool_val:08X}")
                all_pools.append((pool_addr, pool_val))
    
    # Step 2: Analyze font tile area
    analyze_font_area(rom)
    
    # Step 3: Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Story table address: 0x{STORY_TABLE_ADDR:08X}")
    print(f"References found: {len(refs)}")
    for ref in refs:
        print(f"  - File offset 0x{ref:08X} (addr 0x{file_offset_to_addr(ref):08X})")
    
    print(f"\nBL calls to potential font/render functions:")
    unique_calls = sorted(set(all_calls))
    for addr, target in unique_calls:
        print(f"  0x{addr:08X} -> 0x{target:08X}")
    
    print(f"\nLiteral pool pointers (potential font/width tables):")
    unique_pools = sorted(set(all_pools))
    for addr, val in unique_pools:
        if 0x08400000 <= val <= 0x09000000:  # Likely data tables
            print(f"  0x{addr:08X} -> 0x{val:08X}  *** CANDIDATE ***")
        else:
            print(f"  0x{addr:08X} -> 0x{val:08X}")

if __name__ == '__main__':
    main()