#!/usr/bin/env python3
"""
Search for MOVW/MOVT pairs constructing addresses, and PC-relative LDRs
that could reference width table, font tiles, or story table.
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

def find_movw_movt_pairs(rom, search_end=None):
    """Find MOVW/MOVT pairs that construct target addresses"""
    if search_end is None:
        search_end = len(rom)
    
    insns = disassemble_thumb(rom, 0x08000000, search_end)
    
    # Track MOVW instructions by register
    movw_by_reg = {}  # reg -> (addr, imm16)
    pairs = []
    
    for insn in insns:
        if insn.mnemonic == 'movw':
            # MOVW Rd, #imm16
            if len(insn.operands) >= 2:
                rd = insn.operands[0]
                imm = insn.operands[1]
                if rd.type == 1 and imm.type == 1:  # reg, imm
                    reg = rd.reg
                    movw_by_reg[reg] = (insn.address, imm.imm & 0xFFFF)
        
        elif insn.mnemonic == 'movt':
            # MOVT Rd, #imm16
            if len(insn.operands) >= 2:
                rd = insn.operands[0]
                imm = insn.operands[1]
                if rd.type == 1 and imm.type == 1:
                    reg = rd.reg
                    if reg in movw_by_reg:
                        movw_addr, movw_imm = movw_by_reg[reg]
                        movt_imm = imm.imm & 0xFFFF
                        full_addr = (movt_imm << 16) | movw_imm
                        if full_addr in TARGETS:
                            pairs.append({
                                'target': full_addr,
                                'target_name': TARGETS[full_addr],
                                'movw_addr': movw_addr,
                                'movt_addr': insn.address,
                                'reg': reg,
                            })
    
    return pairs

def find_pc_relative_ldrs(rom, search_end=None):
    """Find LDR rX, [PC, #imm] that could load target addresses"""
    if search_end is None:
        search_end = len(rom)
    
    insns = disassemble_thumb(rom, 0x08000000, search_end)
    
    results = []
    for insn in insns:
        if insn.mnemonic == 'ldr' and insn.operands:
            # Check for LDR Rd, [PC, #imm] - PC-relative literal load
            # In Thumb, this is encoded as: 01001 Rd imm8
            # PC = address of instruction + 4
            # Target = (PC & ~3) + imm8 * 4
            for op in insn.operands:
                if op.type == 3:  # MEM
                    if op.mem.base == 15:  # PC register
                        # This is a PC-relative load
                        pc = insn.address + 4
                        target = (pc & ~3) + (op.mem.disp if op.mem.disp else 0)
                        # The actual literal pool entry is at target
                        # We need to read the value at that address
                        if 0 <= addr_to_file_offset(target) < len(rom) - 4:
                            val = struct.unpack('<I', rom[addr_to_file_offset(target):addr_to_file_offset(target)+4])[0]
                            if val in TARGETS:
                                results.append({
                                    'ldr_addr': insn.address,
                                    'literal_addr': target,
                                    'loaded_value': val,
                                    'target_name': TARGETS[val],
                                    'insn_str': f"{insn.mnemonic} {insn.op_str}",
                                })
    
    return results

def find_ldr_literal(rom, search_end=None):
    """Find LDR literal (LDR Rd, =value) instructions"""
    if search_end is None:
        search_end = len(rom)
    
    insns = disassemble_thumb(rom, 0x08000000, search_end)
    
    results = []
    for insn in insns:
        # LDR literal in Thumb: opcode 0x4800-0x4BFF (LDR Rd, [PC, #imm])
        # But capstone shows these as 'ldr' with PC-relative addressing
        # The literal pool entries are separate
        if insn.id in [0x5D, 0x5E, 0x5F]:  # LDR literal (Thumb)
            for op in insn.operands:
                if op.type == 1:  # Immediate address
                    if op.imm in TARGETS:
                        results.append({
                            'insn_addr': insn.address,
                            'target': op.imm,
                            'target_name': TARGETS[op.imm],
                            'insn_str': f"{insn.mnemonic} {insn.op_str}",
                        })
    return results

def analyze_function_at(rom, addr, size=0x200):
    """Disassemble and analyze a function"""
    insns = disassemble_thumb(rom, addr, size)
    print(f"\nFunction at 0x{addr:08X}:")
    for insn in insns:
        print(f"  0x{insn.address:08X}: {insn.mnemonic:8s} {insn.op_str}")
        if insn.mnemonic in ('bx', 'b') and ('lr' in insn.op_str or insn.op_str.startswith('0x')):
            break
    return insns

def main():
    rom = read_rom()
    search_end = min(len(rom), 0x200000)  # First 2MB
    
    print("=" * 60)
    print("SEARCHING FOR ADDRESS CONSTRUCTION PATTERNS")
    print("=" * 60)
    
    # 1. MOVW/MOVT pairs
    print(f"\n1. MOVW/MOVT pairs constructing target addresses:")
    pairs = find_movw_movt_pairs(rom, search_end)
    if pairs:
        for p in pairs:
            print(f"   {p['target_name']} (0x{p['target']:08X}):")
            print(f"     MOVW at 0x{p['movw_addr']:08X} (reg r{p['reg']})")
            print(f"     MOVT at 0x{p['movt_addr']:08X} (reg r{p['reg']})")
            # Analyze function containing MOVT
            analyze_function_at(rom, p['movt_addr'] & ~1, 0x100)
    else:
        print("   None found")
    
    # 2. PC-relative LDRs
    print(f"\n2. PC-relative LDRs loading target addresses:")
    pc_ldrs = find_pc_relative_ldrs(rom, search_end)
    if pc_ldrs:
        for p in pc_ldrs:
            print(f"   {p['target_name']} (0x{p['loaded_value']:08X}):")
            print(f"     LDR at 0x{p['ldr_addr']:08X}: {p['insn_str']}")
            print(f"     Literal at 0x{p['literal_addr']:08X}")
            analyze_function_at(rom, p['ldr_addr'] & ~1, 0x100)
    else:
        print("   None found")
    
    # 3. LDR literal
    print(f"\n3. LDR literal instructions:")
    ldr_lits = find_ldr_literal(rom, search_end)
    if ldr_lits:
        for p in ldr_lits:
            print(f"   {p['target_name']} (0x{p['target']:08X}):")
            print(f"     At 0x{p['insn_addr']:08X}: {p['insn_str']}")
            analyze_function_at(rom, p['insn_addr'] & ~1, 0x100)
    else:
        print("   None found")
    
    # 4. Also search for ADD/SUB with PC to construct addresses
    print(f"\n4. ADD/SUB with PC (r15) to construct addresses:")
    insns = disassemble_thumb(rom, 0x08000000, search_end)
    for insn in insns:
        if insn.mnemonic in ('add', 'sub') and insn.operands:
            for op in insn.operands:
                if op.type == 3 and op.mem.base == 15:  # PC-relative
                    pc = insn.address + 4
                    target = (pc & ~3) + (op.mem.disp if op.mem.disp else 0)
                    if 0 <= addr_to_file_offset(target) < len(rom) - 4:
                        val = struct.unpack('<I', rom[addr_to_file_offset(target):addr_to_file_offset(target)+4])[0]
                        if val in TARGETS:
                            print(f"   {TARGETS[val]} (0x{val:08X}) at 0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
                            analyze_function_at(rom, insn.address & ~1, 0x100)

if __name__ == '__main__':
    main()