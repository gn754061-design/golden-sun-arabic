#!/usr/bin/env python3
"""
Targeted search: find code that reads story text strings,
then trace to the story table reader function.
"""
import sys
import struct
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_ARM
except ImportError:
    print("Capstone not installed")
    sys.exit(1)

ROM_PATH = Path("./work/"MLSS_EU.gba")
STORY_TABLE_FILE_OFF = 0x004EA268

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

def find_refs_to_addresses(rom, target_addrs, search_range=0x200000):
    """Find all references to any of the target addresses"""
    results = []
    for target in target_addrs:
        le_bytes = struct.pack('<I', target)
        pos = 0
        while True:
            pos = rom.find(le_bytes, pos, search_range)
            if pos == -1:
                break
            results.append((target, pos, file_offset_to_addr(pos)))
            pos += 1
    return sorted(results, key=lambda x: x[1])

def analyze_code_around(rom, ref_addr, window=0x1000):
    """Disassemble and analyze code around a reference"""
    window_start = max(0, ref_addr - window)
    window_end = min(len(rom), ref_addr + window)
    addr_start = file_offset_to_addr(window_start)
    
    insns = disassemble_thumb(rom, addr_start, window_end - window_start)
    
    # Find instructions that reference our target
    for i, insn in enumerate(insns):
        # Check if instruction accesses memory at our target address
        # LDR literal, LDR [pc, #imm], etc.
        if insn.id in [0x5D, 0x5E, 0x5F]:  # LDR literal (Thumb)
            for op in insn.operands:
                if op.type == 1:  # Immediate address
                    if op.imm in [0x083D9628, 0x083D9A34, 0x083D9F40, 0x083DA3C0, 0x083DA864]:
                        return insns, i
        
        # Check for MOVW/MOVT constructing address
        if insn.mnemonic in ['movw', 'movt']:
            for op in insn.operands:
                if op.type == 1:
                    val = op.imm & 0xFFFF
                    if val in [0x9628, 0x9A34, 0x9F40, 0xA3C0, 0xA864, 0x3D96, 0x3D9A, 0x3D9F, 0x3DA3, 0x3DA8]:
                        return insns, i
    
    return insns, -1

def print_function_context(insns, center_idx, radius=30):
    """Print disassembly around center instruction"""
    start = max(0, center_idx - radius)
    end = min(len(insns), center_idx + radius)
    print(f"\n  Function context at 0x{insns[center_idx].address:08X}:")
    for j in range(start, end):
        insn = insns[j]
        marker = " >>> " if j == center_idx else "     "
        print(f"{marker}0x{insn.address:08X}: {insn.mnemonic:8s} {insn.op_str}")
    
    # Find BL calls in this range
    bl_calls = []
    for j in range(start, end):
        insn = insns[j]
        if insn.mnemonic in ('bl', 'blx'):
            for op in insn.operands:
                if op.type == 1:
                    bl_calls.append((insn.address, op.imm))
    
    if bl_calls:
        print(f"  BL calls in range:")
        for addr, tgt in bl_calls:
            print(f"    0x{addr:08X} -> BL 0x{tgt:08X}")
    
    return bl_calls

def extract_literal_pools(rom, insns, start_idx, end_idx):
    """Extract literal pool values from instruction range"""
    pools = []
    # Look at addresses after the function (literal pools typically follow)
    func_end = insns[end_idx].address + insns[end_idx].size
    # Scan a bit after
    scan_start = addr_to_file_offset(func_end)
    scan_end = scan_start + 0x200
    for off in range(scan_start & ~3, min(scan_end, len(rom)), 4):
        val = struct.unpack('<I', rom[off:off+4])[0]
        if 0x08000000 <= val <= 0x09FFFFFF:
            pools.append((file_offset_to_addr(off), val))
    return pools

def main():
    rom = read_rom()
    
    # Story text string addresses from the table
    story_strings = [
        0x083D9628, 0x083D9A34, 0x083D9F40, 0x083DA3C0, 0x083DA864,
        0x083D9630, 0x083D9A3C, 0x083D9F48, 0x083DA3C8, 0x083DA86C,
        0x083D9638, 0x083D9A44, 0x083D9F58, 0x083DA3D0, 0x083DA880,
        0x083D9640,
    ]
    
    print("=" * 60)
    print("SEARCHING FOR CODE THAT READS STORY TEXT STRINGS")
    print("=" * 60)
    
    refs = find_refs_to_addresses(rom, story_strings)
    print(f"Found {len(refs)} references to story text strings")
    
    # Group by target address
    by_target = {}
    for target, off, addr in refs:
        if target not in by_target:
            by_target[target] = []
        by_target[target].append((off, addr))
    
    for target in story_strings:
        if target in by_target:
            print(f"\n  Target 0x{target:08X}: {len(by_target[target])} refs")
            for off, addr in by_target[target][:5]:
                print(f"    file_off=0x{off:08X} (addr=0x{addr:08X})")
    
    # Analyze code around each unique reference address
    print(f"\n{'='*60}")
    print("ANALYZING CODE AROUND REFERENCES")
    print(f"{'='*60}")
    
    analyzed_funcs = set()
    all_bl_calls = []
    
    for target, off, addr in refs[:50]:  # Limit to first 50
        if addr in analyzed_funcs:
            continue
        analyzed_funcs.add(addr)
        
        insns, idx = analyze_code_around(rom, off)
        if idx >= 0:
            print(f"\n>>> Reference to 0x{target:08X} at file_off 0x{off:08X} (code addr 0x{addr:08X})")
            bl_calls = print_function_context(insns, idx)
            all_bl_calls.extend(bl_calls)
            
            # Extract literal pools
            pools = extract_literal_pools(rom, insns, max(0, idx-30), min(len(insns), idx+30))
            if pools:
                print(f"  Literal pools after function:")
                for paddr, pval in pools:
                    if 0x08400000 <= pval <= 0x09000000:
                        print(f"    0x{paddr:08X} -> 0x{pval:08X}  *** DATA TABLE ***")
                    else:
                        print(f"    0x{paddr:08X} -> 0x{pval:08X}")
    
    # Summary of BL calls
    print(f"\n{'='*60}")
    print("SUMMARY: BL CALLS FROM TEXT-READING FUNCTIONS")
    print(f"{'='*60}")
    unique_bl = sorted(set(all_bl_calls))
    for addr, tgt in unique_bl:
        print(f"  0x{addr:08X} -> BL 0x{tgt:08X}")
    
    # Now search for the story table reader - look for code that loads 0x084EA268
    # via PC-relative addressing
    print(f"\n{'='*60}")
    print("SEARCHING FOR PC-RELATIVE ACCESS TO STORY TABLE (0x084EA268)")
    print(f"{'='*60}")
    
    # The story table is at 0x084EA268. In Thumb, LDR rX, [PC, #imm] 
    # PC is current instruction + 4. So if instruction at 0x08XXXXXX,
    # the literal pool entry would be at 0x08XXXXXX + 4 + imm*4
    # Let's search for LDR instructions that could load from near 0x084EA268
    
    # Disassemble early ROM (first 2MB) and look for LDR literal patterns
    insns = disassemble_thumb(rom, 0x08000000, 0x200000)
    
    story_table_refs = []
    for i, insn in enumerate(insns):
        if insn.id in [0x5D, 0x5E, 0x5F]:  # LDR literal
            for op in insn.operands:
                if op.type == 1:
                    target = op.imm
                    # Check if target is near story table
                    if 0x084EA000 <= target <= 0x084EB000:
                        story_table_refs.append((insn.address, target, i))
    
    print(f"Found {len(story_table_refs)} LDR literal refs near story table")
    for addr, target, idx in story_table_refs[:20]:
        print(f"  0x{addr:08X}: LDR -> 0x{target:08X}")
        # Print context
        start = max(0, idx - 20)
        end = min(len(insns), idx + 30)
        for j in range(start, end):
            insn = insns[j]
            marker = " >>> " if j == idx else "     "
            print(f"{marker}0x{insn.address:08X}: {insn.mnemonic:8s} {insn.op_str}")
        print()
    
    # Also check ARM mode
    insns_arm = disassemble_arm(rom, 0x08000000, 0x200000)
    arm_refs = []
    for i, insn in enumerate(insns_arm):
        if insn.id in [0x4C, 0x4D]:  # LDR literal ARM
            for op in insn.operands:
                if op.type == 1:
                    target = op.imm
                    if 0x084EA000 <= target <= 0x084EB000:
                        arm_refs.append((insn.address, target, i))
    
    print(f"ARM mode: Found {len(arm_refs)} LDR literal refs near story table")
    for addr, target, idx in arm_refs[:10]:
        print(f"  0x{addr:08X}: LDR -> 0x{target:08X}")

if __name__ == '__main__':
    main()