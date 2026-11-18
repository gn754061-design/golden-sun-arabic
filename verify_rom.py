with open("./work/"MLSS_EU_AR.gba', 'rb') as f:
    rom = f.read()

# Check width table
wt = rom[0x9418F0:0x9418F0+256]
print('Width table (Arabic range 0xA0-0xFF):')
for i in range(0xA0, 0x100):
    if wt[i] != 0:
        print(f'  0x{i:02X}: {wt[i]}')

# Check first translated block at new pointer location
ptr0 = 0x083D9628
off0 = ptr0 - 0x08000000
data = rom[off0:off0+80]
print(f'Block 0 at 0x{ptr0:08X}:')
print(' '.join(f'{b:02X}' for b in data[:64]))

# Check new pointer locations
print('\nNew pointer locations:')
for idx, ptr in [(0, 0x083D9628), (5, 0x083D9630), (10, 0x083D9638), (15, 0x083D9640)]:
    off = ptr - 0x08000000
    data = rom[off:off+40]
    print(f'  Block {idx} @ 0x{ptr:08X}: {" ".join(f"{b:02X}" for b in data[:32])}')