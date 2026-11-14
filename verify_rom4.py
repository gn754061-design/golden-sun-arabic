with open(r'C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.gba', 'rb') as f:
    rom = f.read()

# Check original block locations
print('Checking original block locations after injection:')
for addr in [0x3D9628, 0x3D9A34, 0x3D9F40, 0x3DA3C0, 0x3DA864]:
    off = addr
    data = rom[off:off+80]
    arabic_count = sum(1 for b in data if 0xA0 <= b <= 0xFF)
    print(f'  0x{addr:08X}: {arabic_count} Arabic bytes - {" ".join(f"{b:02X}" for b in data[:32])}')