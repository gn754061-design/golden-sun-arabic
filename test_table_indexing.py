import struct, json

with open("./work/"MLSS_EU.gba', 'rb') as f:
    clean_rom = f.read()

with open("./"all_story_english.json', 'r', encoding='utf-8') as f:
    story_en = json.load(f)

STORY_TBL = 0x004EA268

def read_ascii_at(rom, gba_addr):
    if not (0x08000000 <= gba_addr < 0x09000000):
        return f'<INVALID {hex(gba_addr)}>'
    off = gba_addr - 0x08000000
    # read up to 60 bytes
    b = rom[off:off+60]
    return repr(b)

for test_id in [8, 9, 217, 224]:
    print(f'=== Testing Key {test_id} ===')
    print('JSON English:', repr(story_en.get(str(test_id), '<NONE>'))[:60])
    
    # Check entry_id * 20
    off_0 = STORY_TBL + test_id * 20
    ptr_0 = struct.unpack('<I', clean_rom[off_0 : off_0 + 4])[0]
    print(f'At entry_id * 20 (0x{off_0:06X}): ptr=0x{ptr_0:08X} -> {read_ascii_at(clean_rom, ptr_0)}')
    
    # Check (entry_id - 1) * 20
    off_1 = STORY_TBL + (test_id - 1) * 20
    ptr_1 = struct.unpack('<I', clean_rom[off_1 : off_1 + 4])[0]
    print(f'At (entry_id - 1) * 20 (0x{off_1:06X}): ptr=0x{ptr_1:08X} -> {read_ascii_at(clean_rom, ptr_1)}')
