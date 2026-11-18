with open("./work/"MLSS_EU_AR.gba', 'rb') as f:
    rom = f.read()

# Check story table at 0x4EA268
print('Story table at 0x4EA268:')
for i in range(16):
    ptr = int.from_bytes(rom[0x4EA268+i*4:0x4EA268+i*4+4], 'little')
    print(f'  Block {i}: 0x{ptr:08X}')

# Check new block locations
print()
print('Checking new block locations in free space:')
for addr in [0x2FE600, 0x2FE634, 0x2FE65C, 0x2FE684, 0x2FE6B0]:
    off = addr
    data = rom[off:off+80]
    arabic_count = sum(1 for b in data if 0xA0 <= b <= 0xFF)
    print(f'  0x{addr:08X}: {arabic_count} Arabic bytes - {" ".join(f"{b:02X}" for b in data[:40])}')