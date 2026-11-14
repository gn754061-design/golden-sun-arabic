#!/usr/bin/env python3
"""
Search Thumb code region (0x08017A00+) for text rendering:
- LDRB (load text byte) -> CMP #0xFF -> BL (render char)
- Extract font/width table addresses from literal pools
"""
import sys
import struct
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
except ImportError:
    print("Capstone not installed")
    sys.exit(1)

ROM_PATH = Path(r"C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU.gba")
WIDTH_TABLE_ADDR = 0x089418F0
FONT_TILES_ADDR = 0x08947538
STORY_TABLE_ADDR = 0x084EA268

TARGETS = {
    WIDTH_TABLE_ADDR: "WIDTH_TABLE",
    FONT_TILES_ADDR: "FONT_TILES",
    STORY_TABLE_ADDR: "STORY_TABLE",
}

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

def scan_region(rom, start_addr, end_addr):
    """Scan a region for text rendering patterns"""
    insns = disassemble_thumb(rom, start_addr, end_addr - start_addr)
    
    candidates = []
    for i, insn in enumerate(insns):
        # Pattern: LDRB -> CMP #0xFF -> BL
        if insn.mnemonic == 'ldrb':
            # Check next 5 instructions for CMP #0xFF
            for j in range(i+1, min(i+6, len(insns))):
                insn2 = insns[j]
                if insn2.mnemonic == 'cmp':
                    for op in insn2.operands:
                        if op.type == 1 and op.imm == 0xFF:
                            # Found LDRB -> CMP #0xFF, check for BL after
                            for k in range(j+1, min(j+8, len(insns))):
                                insn3 = insns[k]
                                if insn3.mnemonic in ('bl', 'blx'):
                                    for op3 in insn3.operands:
                                        if op3.type == 1 and 0x08000000 <= op3.imm <= 0x09FFFFFF:
                                            candidates.append({
                                                'ldrb_addr': insn.address,
                                                'cmp_addr': insn2.address,
                                                'bl_addr': insn3.address,
                                                'bl_target': op3.imm,
                                                'insns': insns[i:k+3],
                                            })
                                            break
                            break
        
        # Also check for CMP #0xFF directly (might be in a register)
        if insn.mnemonic == 'cmp':
            for op in insn.operands:
                if op.type == 1 and op.imm == 0xFF:
                    # Check for BL in next few instructions
                    for j in range(i+1, min(i+8, len(insns))):
                        insn2 = insns[j]
                        if insn2.mnemonic in ('bl', 'blx'):
                            for op2 in insn2.operands:
                                if op2.type == 1 and 0x08000000 <= op2.imm <= 0x09FFFFFF:
                                    candidates.append({
                                        'cmp_addr': insn.address,
                                        'bl_addr': insn2.address,
                                        'bl_target': op2.imm,
                                        'insns': insns[i:j+3],
                                    })
                                    break
    
    return candidates, insns

def analyze_render_function(rom, func_addr):
    """Analyze a character render function"""
    insns = disassemble_thumb(rom, func_addr, 0x500)
    
    print(f"\n{'='*60}")
    print(f"RENDER FUNCTION at 0x{func_addr:08X}")
    print(f"{'='*60}")
    
    # Print disassembly
    for insn in insns:
        print(f"  0x{insn.address:08X}: {insn.mnemonic:8s} {insn.op_str}")
        if insn.mnemonic in ('bx', 'b') and ('lr' in insn.op_str or insn.op_str.startswith('0x')):
            break
    
    # Literal pool references (LDR literal)
    print(f"\nLiteral pool references (LDR literal):")
    for insn in insns:
        if insn.id in [0x5D, 0x5E, 0x5F]:
            for op in insn.operands:
                if op.type == 1 and 0x08000000 <= op.imm <= 0x09FFFFFF:
                    name = TARGETS.get(op.imm, "")
                    marker = " ***" if name else ""
                    print(f"  0x{insn.address:08X}: LDR -> 0x{op.imm:08X} {name}{marker}")
    
    # MOVW/MOVT pairs
    print(f"\nMOVW/MOVT pairs:")
    movw_regs = {}
    for insn in insns:
        if insn.mnemonic == 'movw' and len(insn.operands) >= 2:
            rd, imm = insn.operands[0], insn.operands[1]
            if rd.type == 1 and imm.type == 1:
                movw_regs[rd.reg] = (insn.address, imm.imm & 0xFFFF)
        elif insn.mnemonic == 'movt' and len(insn.operands) >= 2:
            rd, imm = insn.operands[0], insn.operands[1]
            if rd.type == 1 and imm.type == 1 and rd.reg in movw_regs:
                movw_addr, movw_imm = movw_regs[rd.reg]
                full = (imm.imm << 16) | movw_imm
                if 0x08000000 <= full <= 0x09FFFFFF:
                    name = TARGETS.get(full, "")
                    marker = " ***" if name else ""
                    print(f"  MOVW@0x{movw_addr:08X} + MOVT@0x{insn.address:08X} -> r{rd.reg} = 0x{full:08X} {name}{marker}")
    
    # Literal pool data after function
    func_end = insns[-1].address + insns[-1].size if insns else func_addr + 0x500
    scan_start = addr_to_file_offset(func_end)
    scan_end = min(scan_start + 0x300, len(rom))
    print(f"\nLiteral pool data after function (0x{func_end:08X}):")
    for off in range(scan_start & ~3, scan_end, 4):
        val = struct.unpack('<I', rom[off:off+4])[0]
        if 0x08000000 <= val <= 0x09FFFFFF:
            name = TARGETS.get(val, "")
            marker = " ***" if name else ""
            print(f"  0x{file_offset_to_addr(off):08X} -> 0x{val:08X} {name}{marker}")

def main():
    rom = read_rom()
    
    # Scan the Thumb code region (0x08017A00 to end of ROM or 0x09000000)
    start_addr = 0x08017A00
    end_addr = min(0x09000000, file_offset_to_addr(len(rom)))
    
    print(f"Scanning Thumb code region 0x{start_addr:08X} - 0x{end_addr:08X}")
    candidates, all_insns = scan_region(rom, start_addr, end_addr)
    
    print(f"Found {len(candidates)} LDRB->CMP#FF->BL candidates")
    
    # Group by BL target (render function)
    by_target = {}
    for c in candidates:
        tgt = c['bl_target']
        if tgt not in by_target:
            by_target[tgt] = []
        by_target[tgt].append(c)
    
    print(f"\nUnique render function targets: {len(by_target)}")
    for tgt, calls in sorted(by_target.items(), key=lambda x: -len(x[1])):
        print(f"  0x{tgt:08X}: {len(calls)} call sites")
        for c in calls[:2]:
            print(f"    CMP@0x{c['cmp_addr']:08X}, BL@0x{c['bl_addr']:08X}")
    
    # Analyze top 5 render functions
    print(f"\n{'#'*60}")
    print("ANALYZING TOP RENDER FUNCTIONS")
    print(f"{'#'*60}")
    
    for tgt, calls in sorted(by_target.items(), key=lambda x: -len(x[1]))[:5]:
        analyze_render_function(rom, tgt)
    
    # Also search for story table access
    print(f"\n{'#'*60}")
    print("SEARCHING FOR STORY TABLE ACCESS (0x084EA268)")
    print(f"{'#'*60}")
    
    # Look for LDR literal or MOVW/MOVT that loads 0x084EA268
    for insn in all_insns:
        if insn.id in [0x5D, 0x5E, 0x5F]:
            for op in insn.operands:
                if op.type == 1 and op.imm == STORY_TABLE_ADDR:
                    print(f"  LDR literal at 0x{insn.address:08X}: -> 0x{op.imm:08X}")
                    # Print context
                    idx = all_insns.index(insn)
                    for j in range(max(0, idx-10), min(len(all_insns), idx+15)):
                        insn2 = all_insns[j]
                        marker = " >>> " if j == idx else "     "
                        print(f"{marker}0x{insn2.address:08X}: {insn2.mnemonic:8s} {insn2.op_str}")
                    print()
        
        if insn.mnemonic in ('movw', 'movt'):
            for op in insn.operands:
                if op.type == 1:
                    val = op.imm & 0xFFFF
                    if val in [0x4EA2, 0x084E, 0xA268]:
                        print(f"  {insn.mnemonic} at 0x{insn.address:08X}: {insn.op_str} (partial match)")

if __name__ == '__main__':
    main()