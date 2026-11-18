with open("./work/"MLSS_EU_AR.gba', 'rb') as f:
    rom = f.read()

# Check the new block locations
print('Checking new block locations in free space:')
for addr in [0x2FE600, 0x2FE638, 0x2FE670, 0x2FE6A4, 0x2FE6D4]:
    off = addr
    data = rom[off:off+80]
    arabic_count = sum(1 for b in data if 0xA0 <= b <= 0xFF)
    print(f'  0x{addr:08X}: {arabic_count} Arabic bytes - {" ".join(f"{b:02X}" for b in data[:40])}')

# Check pointers in story table
print()
print('Checking story table pointers:')
table_off = 0x4EA268
for i in range(16):
    ptr = int.from_bytes(rom[table_off+i*4:table_off+i*4+4], 'little')
    print(f'  Block {i}: 0x{ptr:08X}')