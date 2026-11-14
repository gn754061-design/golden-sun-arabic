with open(r'C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.gba', 'rb') as f:
    rom = f.read()

# Check the actual block data at new pointer locations
print('Detailed check of block at 0x082FE609:')
off = 0x2FE609
data = rom[off:off+120]
for i in range(0, len(data), 16):
    chunk = data[i:i+16]
    hex_str = ' '.join(f'{b:02X}' for b in chunk)
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    print(f'  0x{off+i:08X}: {hex_str:<48} {ascii_str}')

print()
print('Checking for Arabic glyph indices (0xA0-0xFF) in area 0x2FE600-0x2FF000:')
for addr in range(0x2FE600, 0x2FF000, 16):
    data = rom[addr:addr+16]
    arabic_count = sum(1 for b in data if 0xA0 <= b <= 0xFF)
    if arabic_count > 0:
        print(f'  0x{addr:08X}: {arabic_count} Arabic bytes - {" ".join(f"{b:02X}" for b in data)}')