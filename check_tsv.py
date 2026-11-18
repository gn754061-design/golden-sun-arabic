import csv

# Load translations and check the actual story text content
translations = {}
with open("./"Games\game\arabic_translation_merged.tsv", 'r', encoding='utf-8') as f:
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

# Print translations for indices around the story range we found (244, 253, 262, etc.)
story_indices = [244, 253, 262, 273, 283, 297, 298, 299, 300, 303, 304, 305, 306, 308, 309, 310, 311, 312, 313, 341, 342, 343, 344, 347, 350, 353]

with open("./"tsv_check.txt", 'w', encoding='utf-8') as out:
    out.write('Translations for story indices:\n')
    for idx in story_indices:
        if idx in translations:
            out.write('  Index {:4d}: {}\n'.format(idx, translations[idx][:80]))
        else:
            out.write('  Index {:4d}: NO TRANSLATION\n'.format(idx))

    out.write('\nEarlier indices (0-200) with substantial text:\n')
    for idx in sorted(translations.keys()):
        if idx < 200 and len(translations[idx]) > 20:
            out.write('  Index {:4d}: {}\n'.format(idx, translations[idx][:80]))

print("Done - check tsv_check.txt")