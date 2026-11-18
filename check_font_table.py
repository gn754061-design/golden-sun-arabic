with open("./"build_complete_arabic_v3.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('FONT_OFFSETS')
print(text[idx:idx+1500])
