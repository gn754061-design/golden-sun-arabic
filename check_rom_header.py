with open("./work/"MLSS_EU_AR.gba', 'rb') as f:
    header = f.read(0xC0)

print('=== ROM HEADER ===')
print('Game Title:', header[0xA0:0xAC].decode('ascii', errors='ignore').strip())
print('Game Code:', header[0xAC:0xB0].decode('ascii', errors='ignore').strip())
print('Maker Code:', header[0xB0:0xB2].decode('ascii', errors='ignore').strip())
print('Fixed Value (0x96):', hex(header[0xB2]))
print('Main Unit Code:', hex(header[0xB3]))
print('Device Type:', hex(header[0xB4]))
print('Reserved:', header[0xB5:0xC0].hex())

# Check Nintendo logo (first 0xA0 bytes)
logo = header[:0xA0]
print('First 16 bytes of logo:', header[:16].hex())

# Check entry point
entry = header[0x00:0x04]
print('Entry point (ARM):', entry.hex())

# Also check original ROM
with open("./work/"MLSS_EU.gba', 'rb') as f:
    orig_header = f.read(0xC0)

print()
print('=== ORIGINAL ROM HEADER ===')
print('Game Title:', orig_header[0xA0:0xAC].decode('ascii', errors='ignore').strip())
print('Game Code:', orig_header[0xAC:0xB0].decode('ascii', errors='ignore').strip())
print('Maker Code:', orig_header[0xB0:0xB2].decode('ascii', errors='ignore').strip())
print('Entry point (ARM):', orig_header[0x00:0x04].hex())