import struct

with open("./work/"MLSS_EU.gba', 'rb') as f:
    clean_rom = f.read()

TABLE_ADDR = 0x004EA268

print('=== Checking clean TABLE_ADDR at 0x4EA268 ===')
for msg_id in [1, 2, 8, 9, 217, 224]:
    entry_off = TABLE_ADDR + (msg_id - 1) * 20
    ptrs = struct.unpack('<5I', clean_rom[entry_off : entry_off + 20])
    hex_ptrs = [f"0x{p:08X}" for p in ptrs]
    print(f'Msg {msg_id:4d}: {hex_ptrs}')
