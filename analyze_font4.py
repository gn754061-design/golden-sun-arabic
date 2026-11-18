#!/usr/bin/env python3
"""
Full ROM scan for text rendering function:
- CMP rX, #0xFF (check for control code 0xFF)
- Followed by BL to character render function
- Extract font table and width table from literal pools
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

def scan_for_text_renderer(rom):
    """Scan entire ROM for CMP #0xFF + BL pattern"""
    print("Scanning ROM for text rendering function (CMP #0xFF + BL)...")
    
    chunk_size = 0x10000
    candidates = []
    
    for chunk_start in range(0, len(rom), chunk_size):
        chunk_end = min(chunk_start + chunk_size, len(rom))
        addr = file_offset_to_addr(chunk_start)
        
        insns = disassemble_thumb(rom, addr, chunk_end - chunk_start)
        
        for i, insn in enumerate(insns):
            # Look for CMP with immediate 0xFF
            if insn.mnemonic == 'cmp':
                for op in insn.operands:
                    if op.type == 1 and op.imm == 0xFF:
                        # Found CMP #0xFF - check nearby for BL
                        for j in range(max(0, i-3), min(len(insns), i+15)):
                            insn2 = insns[j]
                            if insn2.mnemonic in ('bl', 'blx'):
                                for op2 in insn2.operands:
                                    if op2.type == 1:
                                        candidates.append({
                                            'cmp_addr': insn.address,
                                            'cmp_insn': f"{insn.mnemonic} {insn.op_str}",
                                            'bl_addr': insn2.address,
                                            'bl_target': op2.imm,
                                            'bl_insn': f"{insn2.mnemonic} {insn2.op_str}",
                                            'distance': insn2.address - insn.address,
                                            'chunk_start': addr,
                                        })
                                        break
    
    print(f"Found {len(candidates)} CMP #0xFF + BL candidates")
    
    # Filter: keep only those where BL target is in ROM (0x08xxxxxx)
    valid = [c for c in candidates if 0x08000000 <= c['bl_target'] <= 0x09FFFFFF]
    print(f"Valid candidates (BL to ROM): {len(valid)}")
    
    # Group by BL target (the character render function)
    by_target = {}
    for c in valid:
        tgt = c['bl_target']
        if tgt not in by_target:
            by_target[tgt] = []
        by_target[tgt].append(c)
    
    print(f"\nUnique BL targets (potential char render functions):")
    for tgt, calls in sorted(by_target.items(), key=lambda x: -len(x[1])):
        print(f"  0x{tgt:08X}: {len(calls)} call sites")
        for c in calls[:3]:
            print(f"    from 0x{c['cmp_addr']:08X} (dist={c['distance']:+d})")
    
    return by_target

def analyze_render_function(rom, func_addr):
    """Analyze a character render function to find font/width tables"""
    print(f"\n{'='*60}")
    print(f"ANALYZING RENDER FUNCTION AT 0x{func_addr:08X}")
    print(f"{'='*60}")
    
    # Disassemble function (estimate size ~500 bytes)
    insns = disassemble_thumb(rom, func_addr, 0x400)
    
    print(f"Disassembly (first 80 instructions):")
    for i, insn in enumerate(insns[:80]):
        print(f"  0x{insn.address:08X}: {insn.mnemonic:8s} {insn.op_str}")
        # Stop at BX LR or unconditional branch
        if insn.mnemonic in ('bx', 'b') and 'lr' in insn.op_str.lower():
            if i > 10:  # Not too early
                break
    
    # Extract literal pools referenced by this function
    # Look for LDR literal instructions
    print(f"\nLiteral pool references (LDR literal):")
    pool_refs = []
    for insn in insns:
        if insn.id in [0x5D, 0x5E, 0x5F]:  # LDR literal
            for op in insn.operands:
                if op.type == 1:
                    target = op.imm
                    if 0x08000000 <= target <= 0x09FFFFFF:
                        pool_refs.append((insn.address, target))
                        print(f"  0x{insn.address:08X}: LDR -> 0x{target:08X}")
    
    # Also check for LDR [PC, #imm] - PC-relative loads
    print(f"\nPC-relative loads (LDR rX, [PC, #imm]):")
    for insn in insns:
        if insn.mnemonic == 'ldr':
            for op in insn.operands:
                if op.type == 3:  # ARM_OP_MEM
                    # Check if base is PC (r15)
                    if op.mem.base == 15:  # PC register
                        print(f"  0x{insn.address:08X}: {insn.mnemonic} {insn.op_str}")
                        # Calculate literal address
                        # PC = insn.address + 4
                        # Target = PC + imm*4 (for word) or imm (for byte)
                        # This is complex in Thumb, just note it
    
    # Extract literal pool values after function
    func_end = insns[-1].address + insns[-1].size if insns else func_addr + 0x400
    scan_start = addr_to_file_offset(func_end)
    scan_end = min(scan_start + 0x400, len(rom))
    
    print(f"\nLiteral pool values after function (0x{func_end:08X} - 0x{file_offset_to_addr(scan_end):08X}):")
    pools = []
    for off in range(scan_start & ~3, scan_end, 4):
        val = struct.unpack('<I', rom[off:off+4])[0]
        if 0x08000000 <= val <= 0x09FFFFFF:
            pools.append((file_offset_to_addr(off), val))
            print(f"  0x{file_offset_to_addr(off):08X} -> 0x{val:08X}")
    
    return pools, pool_refs

def analyze_font_area_detailed(rom):
    """Detailed analysis of font tile area at 0x947528"""
    print(f"\n{'='*60}")
    print(f"DETAILED FONT AREA ANALYSIS")
    print(f"{'='*60}")
    
    # The match at 0x947528 is in a region of zeros
    # Let's look at the actual font data which seems to start at 0x947538
    font_data_start = 0x947538
    font_data = rom[font_data_start:font_data_start+0x2000]
    
    print(f"Font data at 0x{font_data_start:08X} (first 512 bytes):")
    for i in range(0, min(512, len(font_data)), 16):
        line = font_data[i:i+16]
        addr = font_data_start + i
        hex_str = ' '.join(f'{b:02X}' for b in line)
        print(f"  0x{addr:08X}: {hex_str}")
    
    # Try to interpret as 4bpp tiles (32 bytes per 8x8 tile)
    print(f"\n4bpp tile rendering (32 bytes/tile):")
    for t in range(min(32, len(font_data)//32)):
        tile = font_data[t*32:t*32+32]
        non_zero = sum(1 for b in tile if b != 0)
        if non_zero > 4:
            print(f"\n  Tile {t:3d} (addr 0x{font_data_start + t*32:08X}, {non_zero} non-zero):")
            for row in range(0, 32, 4):
                b0, b1, b2, b3 = tile[row:row+4]
                line = ''.join(
                    ' .:-=+*#%@'[min(9, ((b3>>(7-c))&1)*8 + ((b2>>(7-c))&1)*4 + ((b1>>(7-c))&1)*2 + ((b0>>(7-c))&1))]
                    for c in range(8)
                )
                print(f"    {line}")
    
    # Look for width table - scan for byte arrays with values 1-12
    print(f"\nScanning for width table in 0x940000-0x960000...")
    area = rom[0x940000:0x960000]
    for off in range(0, len(area) - 256, 4):
        block = area[off:off+256]
        valid = sum(1 for b in block if 1 <= b <= 12)
        zero = sum(1 for b in block if b == 0)
        if valid > 80 and zero > 50:
            addr = 0x940000 + off
            print(f"  Candidate at 0x{addr:08X}: {valid} valid widths, {zero} zeros")
            print(f"    First 64: {' '.join(f'{b:02X}' for b in block[:64])}")

def main():
    rom = read_rom()
    print(f"ROM size: {len(rom):,} bytes (0x{len(rom):X})")
    
    # Step 1: Find text renderer candidates
    by_target = scan_for_text_renderer(rom)
    
    # Step 2: Analyze top candidates
    for tgt, calls in sorted(by_target.items(), key=lambda x: -len(x[1]))[:5]:
        pools, refs = analyze_render_function(rom, tgt)
        
        # Check if any pool refs point to font-like areas (0x094xxxxx or similar)
        font_candidates = [p for p in pools if 0x08940000 <= p[1] <= 0x08960000 or 0x08400000 <= p[1] <= 0x08500000]
        if font_candidates:
            print(f"\n  *** FONT TABLE CANDIDATES ***")
            for paddr, pval in font_candidates:
                print(f"    0x{paddr:08X} -> 0x{pval:08X}")
    
    # Step 3: Detailed font area analysis
    analyze_font_area_detailed(rom)

if __name__ == '__main__':
    main()