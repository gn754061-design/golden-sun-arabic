with open(r'C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.gba', 'rb') as f:
    rom = f.read()

glyph_to_char = {}
for i in range(0xA0, 0x100):
    ch = chr(0x0627 + (i - 0xA0) % 96)
    glyph_to_char[i] = ch

with open('arabic_text_check.txt', 'w', encoding='utf-8') as out:
    for addr in [0x2FE600, 0x2FE634, 0x2FE65C, 0x2FE6B0, 0x2FE6DC, 0x2FE720]:
        off = addr
        data = rom[off:off+100]
        text = []
        for b in data[2:]:
            if b == 0xFF:
                break
            if b in glyph_to_char:
                text.append(glyph_to_char[b])
            elif 32 <= b < 128:
                text.append(chr(b))
        out.write('0x%08X: %s\n' % (addr, ''.join(text)[:80]))

print('Written to arabic_text_check.txt')