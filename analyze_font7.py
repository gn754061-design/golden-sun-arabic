#!/usr/bin/env python3
"""
Full ROM scan (16MB) for text rendering function:
- CMP #0xFF (both 16-bit and 32-bit Thumb encodings)
- Followed by BL to render function
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

def scan_full_rom(rom):
    """Scan entire ROM for CMP #0xFF + BL pattern"""
    print("Scanning FULL ROM (16MB) for text rendering patterns...")
    
    chunk_size = 0x40000  # 256KB chunks
    candidates = []
    total_chunks = (len(rom) + chunk_size - 1) // chunk_size
    
    for chunk_idx in range(total_chunks):
        chunk_start = chunk_idx * chunk_size
        chunk_end = min(chunk_start + chunk_size, len(rom))
        addr = file_offset_to_addr(chunk_start)
        
        if chunk_idx % 16 == 0:
            print(f"  Progress: {chunk_idx}/{total_chunks} chunks ({chunk_idx*100//total_chunks}%)")
        
        insns = disassemble_thumb(rom, addr, chunk_end - chunk_start)
        
        for i, insn in enumerate(insns):
            # Look for CMP with immediate 0xFF (both 16-bit and 32-bit)
            if insn.mnemonic == 'cmp':
                for op in insn.operands:
                    if op.type == 1 and op.imm == 0xFF:
                        # Found CMP #0xFF - check nearby for BL
                        for j in range(max(0, i-3), min(len(insns), i+20)):
                            insn2 = insns[j]
                            if insn2.mnemonic in ('bl', 'blx'):
                                for op2 in insn2.operands:
                                    if op2.type == 1:
                                        candidates.append({
                                            'cmp_addr': insn.address,
                                            'bl_addr': insn2.address,
                                            'bl_target': op2.imm,
                                            'distance': insn2.address - insn.address,
                                        })
                                        break
    
    return candidates

def analyze_candidate(rom, cand):
    """Analyze a candidate function"""
    # Disassemble around the CMP
    start_addr = cand['cmp_addr'] - 0x80
    end_addr = cand['cmp_addr'] + 0x200
    insns = disassemble_thumb(rom, start_addr, end_addr - start_addr)
    
    print(f"\n{'='*60}")
    print(f"CANDIDATE: CMP at 0x{cand['cmp_addr']:08X}, BL to 0x{cand['bl_target']:08X}")
    print(f"{'='*60}")
    
    for insn in insns:
        marker = " >>> " if insn.address == cand['cmp_addr'] else (" *** " if insn.address == cand['bl_addr'] else "     ")
        print(f"{marker}0x{insn.address:08X}: {insn.mnemonic:8s} {insn.op_str}")
        if insn.address > cand['bl_addr'] + 0x40:
            break
    
    # Find literal pools referenced
    print(f"\nLiteral pool references (LDR literal):")
    for insn in insns:
        if insn.id in [0x5D, 0x5E, 0x5F]:
            for op in insn.operands:
                if op.type == 1 and 0x08000000 <= op.imm <= 0x09FFFFFF:
                    print(f"  0x{insn.address:08X}: LDR -> 0x{op.imm:08X}")
    
    # Check for MOVW/MOVT
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
    
    candidates = scan_full_rom(rom)
    
    print(f"\nTotal candidates: {len(candidates)}")
    
    # Group by BL target
    by_target = {}
    for c in candidates:
        tgt = c['bl_target']
        if 0x08000000 <= tgt <= 0x09FFFFFF:
            if tgt not in by_target:
                by_target[tgt] = []
            by_target[tgt].append(c)
    
    print(f"Unique BL targets in ROM: {len(by_target)}")
    
    # Sort by number of call sites
    sorted_targets = sorted(by_target.items(), key=lambda x: -len(x[1]))
    
    print(f"\nTop BL targets (potential char render functions):")
    for tgt, calls in sorted_targets[:20]:
        print(f"  0x{tgt:08X}: {len(calls)} call sites")
        for c in calls[:2]:
            print(f"    CMP@0x{c['cmp_addr']:08X} (dist={c['distance']:+d})")
    
    # Analyze top 5 candidates
    print(f"\n{'='*60}")
    print("DETAILED ANALYSIS OF TOP CANDIDATES")
    print(f"{'='*60}")
    
    for tgt, calls in sorted_targets[:5]:
        print(f"\n{'#'*60}")
        print(f"TARGET FUNCTION: 0x{tgt:08X} ({len(calls)} call sites)")
        print(f"{'#'*60}")
        
        # Analyze the target function itself
        insns = disassemble_thumb(rom, tgt, 0x400)
        print(f"\nDisassembly of render function at 0x{tgt:08X}:")
        for insn in insns:
            print(f"  0x{insn.address:08X}: {insn.mnemonic:8s} {insn.op_str}")
            if insn.mnemonic in ('bx', 'b') and ('lr' in insn.op_str or insn.op_str.startswith('0x')):
                if len([i for i in insns if i.address <= insn.address]) > 15:
                    break
        
        # Extract literal pools from render function
        print(f"\nLiteral pools in/after render function:")
        pools = []
        for insn in insns:
            if insn.id in [0x5D, 0x5E, 0x5F]:
                for op in insn.operands:
                    if op.type == 1 and 0x08000000 <= op.imm <= 0x09FFFFFF:
                        pools.append((insn.address, op.imm))
        for paddr, pval in pools:
            print(f"  LDR at 0x{paddr:08X} -> 0x{pval:08X}")
        
        # Literal pool data after function
        func_end = insns[-1].address + insns[-1].size if insns else tgt + 0x400
        scan_start = addr_to_file_offset(func_end)
        scan_end = min(scan_start + 0x200, len(rom))
        print(f"\nLiteral pool data after function (0x{func_end:08X}):")
        for off in range(scan_start & ~3, scan_end, 4):
            val = struct.unpack('<I', rom[off:off+4])[0]
            if 0x08000000 <= val <= 0x09FFFFFF:
                print(f"  0x{file_offset_to_addr(off):08X} -> 0x{val:08X}")
        
        # Analyze one call site
        if calls:
            print(f"\nCall site analysis (first):")
            analyze_candidate(rom, calls[0])

if __name__ == '__main__':
    main()