# Build mapping without embedding Arabic literals in source
# Use Unicode escape sequences

basic_arabic_map = {
    ' ': 0x20,
    # Arabic letters (isolated forms) - map to 0xA0-0xBC
    '\u0627': 0xA0,  # ا
    '\u0628': 0xA1,  # ب
    '\u062A': 0xA2,  # ت
    '\u062B': 0xA3,  # ث
    '\u062C': 0xA4,  # ج
    '\u062D': 0xA5,  # ح
    '\u062E': 0xA6,  # خ
    '\u062F': 0xA7,  # د
    '\u0630': 0xA8,  # ذ
    '\u0631': 0xA9,  # ر
    '\u0632': 0xAA,  # ز
    '\u0633': 0xAB,  # س
    '\u0634': 0xAC,  # ش
    '\u0635': 0xAD,  # ص
    '\u0636': 0xAE,  # ض
    '\u0637': 0xAF,  # ط
    '\u0638': 0xB0,  # ظ
    '\u0639': 0xB1,  # ع
    '\u063A': 0xB2,  # غ
    '\u0641': 0xB3,  # ف
    '\u0642': 0xB4,  # ق
    '\u0643': 0xB5,  # ك
    '\u0644': 0xB6,  # ل
    '\u0645': 0xB7,  # م
    '\u0646': 0xB8,  # ن
    '\u0647': 0xB9,  # ه
    '\u0648': 0xBA,  # و
    '\u0649': 0xBB,  # ى
    '\u064A': 0xBC,  # ي
    # Hamza variants
    '\u0623': 0xBD,  # أ
    '\u0625': 0xBE,  # إ
    '\u0622': 0xBF,  # آ
    '\u0621': 0xC0,  # ء
    '\u0629': 0xC1,  # ة
    '\u0624': 0xC2,  # ؤ
    '\u0626': 0xC3,  # ئ
    # Punctuation
    '.': 0xC8, ',': 0xC9, '!': 0xCA, '?': 0xCB, ':': 0xCC, ';': 0xCD,
    '(': 0xCE, ')': 0xCF, '[': 0xD0, ']': 0xD1, '{': 0xD2, '}': 0xD3,
    '-': 0xD4, '_': 0xD5, '+': 0xD6, '=': 0xD7, '*': 0xD8, '/': 0xD9,
    '\\': 0xDA, '|': 0xDB, '<': 0xDC, '>': 0xDD, '@': 0xDE, '#': 0xDF,
    '$': 0xE0, '%': 0xE1, '^': 0xE2, '&': 0xE3, '~': 0xE4, '`': 0xE5,
    '"': 0xE6, "'": 0xE7,
}

# Digits
for i, d in enumerate('0123456789'):
    basic_arabic_map[d] = 0xE8 + i

# Arabic punctuation
basic_arabic_map['\u060C'] = 0xF2
basic_arabic_map['\u061B'] = 0xF3
basic_arabic_map['\u061F'] = 0xF4
basic_arabic_map['\u066A'] = 0xF5
basic_arabic_map['\u06D4'] = 0xF6

print("Basic Arabic map: {} characters".format(len(basic_arabic_map)))
print("Code range: {} - {}".format(min(basic_arabic_map.values()), max(basic_arabic_map.values())))

# Test on sample
sample = "\u0623\u062E\u0628\u0631\u0646\u064A \u0628\u0627\u0633\u0645\u0643.{02}"
print("Sample: {}".format(sample))
for ch in sample:
    code = basic_arabic_map.get(ch, 0x20)
    print("  U+{:04X} -> 0x{:02X}".format(ord(ch), code))

# Load translations and check coverage
import csv
translations = {}
with open(r"C:\Users\user\Desktop\game\Games\game\arabic_translation_merged.tsv", 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter='\t')
    next(reader)
    for row in reader:
        if len(row) >= 2:
            try:
                idx = int(row[0])
                arabic = row[1]
                translations[idx] = arabic
            except:
                pass

print("\nLoaded {} translations".format(len(translations)))

# Check coverage
all_chars = set()
for text in translations.values():
    for ch in text:
        all_chars.add(ch)

print("Total unique characters in translations: {}".format(len(all_chars)))
missing = [ch for ch in all_chars if ch not in basic_arabic_map]
print("Missing from basic map: {}".format(len(missing)))
for ch in sorted(missing, key=lambda x: ord(x))[:40]:
    print("  U+{:04X} ('{}')".format(ord(ch), ch))
if len(missing) > 40:
    print("  ... and {} more".format(len(missing) - 40))