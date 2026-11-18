import json

with open("./"all_story_english.json', 'r', encoding='utf-8') as f:
    en = json.load(f)

for k in [225, 226, 227, 228]:
    print(f'Key {k}:')
    print(' ', repr(en.get(str(k))))
