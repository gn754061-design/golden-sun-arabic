#!/usr/bin/env python3
"""
Find functions that reference the width table (0x089418F0) and font tiles (0x08947538).
These will lead us to the text rendering function.
"""
import sys
import struct
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_ARM
except ImportError:
    print("Capstone not installed")
    sys.exit(1)

ROM_PATH = Path(r"C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU.gba")
WIDTH_TABLE_ADDR = 0x089418F0
FONT_TILES_ADDR = 0x08947538
STORY_TABLE_ADDR = 0x084EA268

def read_rom():
    with open(ROM_PATH, 'rb') as f:
        return f.read()

def file_offset_to_addr(offset):
    return 0x08000000 + offset

def addr_to_file_offset(addr):
    return addr - 0x08000000

def disassemble_thumb(rom, addr, size):
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
    md.detail = True
    offset = addr_to_file_offset(addr)
    code = rom[offset:offset+size]
    return list(md.disasm(code, addr))

def find_refs_to_addr(rom, target_addr, search_end=None):
    """Find all 32-bit LE references to target_addr"""
    if search_end is None:
        search_end = len(rom)
    le_bytes = struct.pack('<I', target_addr)
    refs = []
    pos = 0
    while True:
        pos = rom.find(le_bytes, pos, search_end)
        if pos == -1:
            break
        refs.append((pos, file_offset_to_addr(pos)))
        pos += 1
    return refs

def analyze_ref_context(rom, ref_off, window=0x1000):
    """Disassemble and analyze code around a reference"""
    window_start = max(0, ref_off - window)
    window_end = min(len(rom), ref_off + window)
    addr_start = file_offset_to_addr(window_start)
    
    insns = disassemble_thumb(rom, addr_start, window_end - window_start)
    
    # Find the instruction that references our target
    for i, insn in enumerate(insns):
        if insn.address > file_offset_to_addr(ref_off) + 4:
            break
        if insn.address <= file_offset_to_addr(ref_off) < insn.address + insn.size:
            return insns, i
    return insns, -1

def print_context(insns, idx, radius=25):
    start = max(0, idx - radius)
    end = min(len(insns), idx + radius)
    for j in range(start, end):
        insn = insns[j]
        marker = " >>> " if j == idx else "     "
        print(f"{marker}0x{insn.address:08X}: {insn.mnemonic:8s} {insn.op_str}")

def extract_bl_calls(insns, start_idx, end_idx):
    calls = []
    for j in range(start_idx, end_idx):
        insn = insns[j]
        if insn.mnemonic in ('bl', 'blx'):
            for op in insn.operands:
                if op.type == 1:
                    calls.append((insn.address, op.imm))
    return calls

def extract_literal_pools(rom, func_start_addr, size=0x400):
    """Extract literal pool values after a function"""
    scan_start = addr_to_file_offset(func_start_addr)
    scan_end = min(scan_start + size, len(rom))
    pools = []
    for off in range(scan_start & ~3, scan_end, 4):
        val = struct.unpack('<I', rom[off:off+4])[0]
        if 0x08000000 <= val <= 0x09FFFFFF:
            pools.append((file_offset_to_addr(off), val))
    return pools

def main():
    rom = read_rom()
    
    print("=" * 60)
    print("SEARCHING FOR REFERENCES TO WIDTH TABLE & FONT TILES")
    print("=" * 60)
    
    # Search for width table references
    print(f"\n1. Width table at 0x{WIDTH_TABLE_ADDR:08X} (file off 0x{WIDTH_TABLE_ADDR-0x08000000:08X})")
    width_refs = find_refs_to_addr(rom, WIDTH_TABLE_ADDR)
    print(f"   Found {len(width_refs)} direct references")
    
    for off, addr in width_refs[:10]:
        print(f"   Ref at file_off=0x{off:08X} (code addr=0x{addr:08X})")
        insns, idx = analyze_ref_context(rom, off)
        if idx >= 0:
            print(f"   >>> Code context:")
            print_context(insns, idx, 20)
            bl_calls = extract_bl_calls(insns, max(0, idx-20), min(len(insns), idx+20))
            if bl_calls:
                print(f"   BL calls:")
                for ca, tgt in bl_calls:
                    print(f"     0x{ca:08X} -> BL 0x{tgt:08X}")
            pools = extract_literal_pools(rom, insns[idx].address)
            if pools:
                print(f"   Literal pools after:")
                for paddr, pval in pools:
                    print(f"     0x{paddr:08X} -> 0x{pval:08X}")
            print()
    
    # Search for font tiles references
    print(f"\n2. Font tiles at 0x{FONT_TILES_ADDR:08X} (file off 0x{FONT_TILES_ADDR-0x08000000:08X})")
    font_refs = find_refs_to_addr(rom, FONT_TILES_ADDR)
    print(f"   Found {len(font_refs)} direct references")
    
    for off, addr in font_refs[:10]:
        print(f"   Ref at file_off=0x{off:08X} (code addr=0x{addr:08X})")
        insns, idx = analyze_ref_context(rom, off)
        if idx >= 0:
            print(f"   >>> Code context:")
            print_context(insns, idx, 20)
            bl_calls = extract_bl_calls(insns, max(0, idx-20), min(len(insns), idx+20))
            if bl_calls:
                print(f"   BL calls:")
                for ca, tgt in bl_calls:
                    print(f"     0x{ca:08X} -> BL 0x{tgt:08X}")
            pools = extract_literal_pools(rom, insns[idx].address)
            if pools:
                print(f"   Literal pools after:")
                for paddr, pval in pools:
                    print(f"     0x{paddr:08X} -> 0x{pval:08X}")
            print()
    
    # Also search for story table references
    print(f"\n3. Story table at 0x{STORY_TABLE_ADDR:08X}")
    story_refs = find_refs_to_addr(rom, STORY_TABLE_ADDR)
    print(f"   Found {len(story_refs)} direct references")
    
    for off, addr in story_refs[:10]:
        print(f"   Ref at file_off=0x{off:08X} (code addr=0x{addr:08X})")
        insns, idx = analyze_ref_context(rom, off)
        if idx >= 0:
            print(f"   >>> Code context:")
            print_context(insns, idx, 20)
            bl_calls = extract_bl_calls(insns, max(0, idx-20), min(len(insns), idx+20))
            if bl_calls:
                print(f"   BL calls:")
                for ca, tgt in bl_calls:
                    print(f"     0x{ca:08X} -> BL 0x{tgt:08X}")
            print()

if __name__ == '__main__':
    main()