with open("./work/"MLSS_EU_AR.gba', 'rb') as f:
    rom = f.read()

# Check the free space area where blocks were moved (0x082Fxxxx)
print('Checking free space area 0x082Fxxxx:')
for addr in [0x082FE609, 0x082FE60E, 0x082FEF0E, 0x082FE613, 0x082FE623]:
    off = addr - 0x08000000
    if off < len(rom):
        data = rom[off:off+64]
        print(f'  0x{addr:08X}: {" ".join(f"{b:02X}" for b in data[:40])}')

print()
print('Checking for Arabic glyph indices in translated blocks:')
for addr in [0x082FE609, 0x082FE60E]:
    off = addr - 0x08000000
    data = rom[off:off+80]
    arabic_count = sum(1 for b in data if 0xA0 <= b <= 0xFF)
    print(f'  0x{addr:08X}: {arabic_count} Arabic glyph bytes')