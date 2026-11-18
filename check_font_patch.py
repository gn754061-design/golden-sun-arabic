with open("./"build_complete_arabic_v3.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(330, 380):
    if i < len(lines):
        print(f'{i+1:03d}: {lines[i]}', end='')
