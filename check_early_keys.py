import json

with open("./"all_story_english.json', 'r', encoding='utf-8') as f:
    en = json.load(f)

with open("./"all_story_arabic.json', 'r', encoding='utf-8') as f:
    ar = json.load(f)

for i in range(30):
    k = str(i)
    if k in en or k in ar:
        print(f'Key {i:2d}:')
        print('  EN:', repr(en.get(k)))
        print('  AR:', repr(ar.get(k)))
