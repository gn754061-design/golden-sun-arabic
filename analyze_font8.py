#!/usr/bin/env python3
"""
Search for text processing patterns:
- LDRB (load byte from text) followed by comparison
- Various comparison instructions (CMP, TST, TEQ, CMN)
- Both Thumb and ARM mode
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

def disassemble_arm(rom, addr, size):
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    md.detail = True
    offset = addr_to_file_offset(addr)
    code = rom[offset:offset+size]
    return list(md.disasm(code, addr))

def search_patterns_thumb(rom, start_addr, end_addr):
    """Search for text processing patterns in Thumb code"""
    insns = disassemble_thumb(rom, start_addr, end_addr - start_addr)
    
    candidates = []
    for i, insn in enumerate(insns):
        # Pattern 1: LDRB followed by CMP/TST with #0xFF
        if insn.mnemonic == 'ldrb':
            # Check next few instructions for comparison
            for j in range(i+1, min(i+6, len(insns))):
                insn2 = insns[j]
                if insn2.mnemonic in ('cmp', 'tst', 'teq', 'cmn'):
                    for op in insn2.operands:
                        if op.type == 1 and op.imm == 0xFF:
                            candidates.append(('LDRB+CMP#FF', insn.address, insn2.address, insns[i:j+3]))
                            break
        
        # Pattern 2: LDRB -> AND #0xFF -> CMP #0
        if insn.mnemonic == 'ldrb':
            for j in range(i+1, min(i+8, len(insns))):
                insn2 = insns[j]
                if insn2.mnemonic == 'and' or insn2.mnemonic == 'ands':
                    for op in insn2.operands:
                        if op.type == 1 and op.imm == 0xFF:
                            # Check for CMP #0 after
                            for k in range(j+1, min(j+4, len(insns))):
                                insn3 = insns[k]
                                if insn3.mnemonic == 'cmp':
                                    for op3 in insn3.operands:
                                        if op3.type == 1 and op3.imm == 0:
                                            candidates.append(('LDRB+AND#FF+CMP#0', insn.address, insn3.address, insns[i:k+3]))
                                            break
        
        # Pattern 3: CBZ/CBNZ after LDRB (check for zero/non-zero)
        if insn.mnemonic in ('cbz', 'cbnz'):
            # Check if previous was LDRB
            for j in range(max(0, i-3), i):
                if insns[j].mnemonic == 'ldrb':
                    candidates.append(('LDRB+CBZ/CBNZ', insns[j].address, insn.address, insns[j:i+2]))
                    break
        
        # Pattern 4: BL to function after loading byte (potential char render call)
        if insn.mnemonic in ('bl', 'blx'):
            for op in insn.operands:
                if op.type == 1 and 0x08000000 <= op.imm <= 0x09FFFFFF:
                    # Check if recent LDRB
                    for j in range(max(0, i-10), i):
                        if insns[j].mnemonic == 'ldrb':
                            candidates.append(('LDRB+BL', insns[j].address, insn.address, insns[j:i+3], op.imm))
                            break
    
    return candidates

def search_patterns_arm(rom, start_addr, end_addr):
    """Search for text processing patterns in ARM code"""
    insns = disassemble_arm(rom, start_addr, end_addr - start_addr)
    
    candidates = []
    for i, insn in enumerate(insns):
        if insn.mnemonic == 'ldrb':
            for j in range(i+1, min(i+6, len(insns))):
                insn2 = insns[j]
                if insn2.mnemonic in ('cmp', 'tst', 'teq', 'cmn'):
                    for op in insn2.operands:
                        if op.type == 1 and op.imm == 0xFF:
                            candidates.append(('ARM_LDRB+CMP#FF', insn.address, insn2.address, insns[i:j+3]))
                            break
    return candidates

def analyze_candidate(rom, cand, mode='thumb'):
    """Analyze a candidate in detail"""
    typ = cand[0]
    start = cand[1]
    bl_target = cand[4] if len(cand) > 4 else None
    
    print(f"\n{'='*60}")
    print(f"CANDIDATE: {typ} at 0x{start:08X}" + (f", BL->0x{bl_target:08X}" if bl_target else ""))
    print(f"{'='*60}")
    
    # Disassemble wider context
    ctx_start = start - 0x60
    ctx_end = start + 0x100
    if mode == 'thumb':
        insns = disassemble_thumb(rom, ctx_start, ctx_end - ctx_start)
    else:
        insns = disassemble_arm(rom, ctx_start, ctx_end - ctx_start)
    
    for insn in insns:
        marker = " >>> " if insn.address == start else "     "
        print(f"{marker}0x{insn.address:08X}: {insn.mnemonic:8s} {insn.op_str}")
        if insn.address > start + 0x80:
            break
    
    # Look for literal pools
    print(f"\nLiteral pools (LDR literal):")
    for insn in insns:
        if mode == 'thumb' and insn.id in [0x5D, 0x5E, 0x5F]:
            for op in insn.operands:
                if op.type == 1 and 0x08000000 <= op.imm <= 0x09FFFFFF:
                    print(f"  0x{insn.address:08X}: LDR -> 0x{op.imm:08X}")
        elif mode == 'arm' and insn.id in [0x4C, 0x4D]:
            for op in insn.operands:
                if op.type == 1 and 0x08000000 <= op.imm <= 0x09FFFFFF:
                    print(f"  0x{insn.address:08X}: LDR -> 0x{op.imm:08X}")
    
    # MOVW/MOVT
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
                    print(f"  MOVW@0x{movw_addr:08X} + MOVT@0x{insn.address:08X} -> r{rd.reg} = 0x{full:08X}")

def main():
    rom = read_rom()
    print(f"ROM size: {len(rom):,} bytes (0x{len(rom):X})")
    
    # Search first 2MB (main code area) in Thumb
    print(f"\nSearching Thumb code in 0x08000000-0x08200000...")
    thumb_cands = search_patterns_thumb(rom, 0x08000000, 0x08200000)
    print(f"Found {len(thumb_cands)} Thumb candidates")
    
    # Group by type
    by_type = {}
    for c in thumb_cands:
        typ = c[0]
        if typ not in by_type:
            by_type[typ] = []
        by_type[typ].append(c)
    
    for typ, cands in by_type.items():
        print(f"  {typ}: {len(cands)}")
        # Show unique BL targets for LDRB+BL
        if typ == 'LDRB+BL':
            bl_targets = {}
            for c in cands:
                tgt = c[4]
                if tgt not in bl_targets:
                    bl_targets[tgt] = 0
                bl_targets[tgt] += 1
            print(f"    BL targets: {sorted(bl_targets.items(), key=lambda x: -x[1])[:10]}")
    
    # Analyze top LDRB+BL candidates
    if 'LDRB+BL' in by_type:
        bl_targets = {}
        for c in by_type['LDRB+BL']:
            tgt = c[4]
            if tgt not in bl_targets:
                bl_targets[tgt] = []
            bl_targets[tgt].append(c)
        
        sorted_targets = sorted(bl_targets.items(), key=lambda x: -len(x[1]))
        print(f"\n{'='*60}")
        print("TOP LDRB+BL RENDER FUNCTION CANDIDATES")
        print(f"{'='*60}")
        
        for tgt, cands in sorted_targets[:10]:
            print(f"\n{'#'*60}")
            print(f"RENDER FUNCTION: 0x{tgt:08X} ({len(cands)} call sites)")
            print(f"{'#'*60}")
            
            # Analyze the render function
            insns = disassemble_thumb(rom, tgt, 0x400)
            print(f"Disassembly:")
            for insn in insns:
                print(f"  0x{insn.address:08X}: {insn.mnemonic:8s} {insn.op_str}")
                if insn.mnemonic in ('bx', 'b') and ('lr' in insn.op_str or insn.op_str.startswith('0x')):
                    break
            
            # Literal pools
            print(f"\nLiteral pool refs:")
            for insn in insns:
                if insn.id in [0x5D, 0x5E, 0x5F]:
                    for op in insn.operands:
                        if op.type == 1 and 0x08000000 <= op.imm <= 0x09FFFFFF:
                            print(f"  0x{insn.address:08X}: LDR -> 0x{op.imm:08X}")
            
            # Pool data after
            func_end = insns[-1].address + insns[-1].size if insns else tgt + 0x400
            scan_start = addr_to_file_offset(func_end)
            scan_end = min(scan_start + 0x200, len(rom))
            print(f"\nPool data after (0x{func_end:08X}):")
            for off in range(scan_start & ~3, scan_end, 4):
                val = struct.unpack('<I', rom[off:off+4])[0]
                if 0x08000000 <= val <= 0x09FFFFFF:
                    print(f"  0x{file_offset_to_addr(off):08X} -> 0x{val:08X}")
            
            # Analyze one call site
            if cands:
                analyze_candidate(rom, cands[0])
    
    # Also search ARM mode in first 2MB
    print(f"\n\nSearching ARM code in 0x08000000-0x08200000...")
    arm_cands = search_patterns_arm(rom, 0x08000000, 0x08200000)
    print(f"Found {len(arm_cands)} ARM candidates")
    for c in arm_cands[:5]:
        analyze_candidate(rom, c, 'arm')

if __name__ == '__main__':
    main()