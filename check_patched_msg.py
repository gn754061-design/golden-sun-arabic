import struct

with open(r'C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.gba', 'rb') as f:
    rom = f.read()

STORY_TBL = 0x004EA268

def inspect_patched_msg(msg_id):
    entry_off = STORY_TBL + msg_id * 20
    ptr = struct.unpack('<I', rom[entry_off : entry_off + 4])[0]
    file_off = ptr - 0x08000000
    raw = rom[file_off : file_off + 80]
    print(f'=== Patched Msg {msg_id} (ptr=0x{ptr:08X}, off=0x{file_off:06X}) ===')
    print('Raw hex:', raw.hex())

inspect_patched_msg(217)
inspect_patched_msg(224)
