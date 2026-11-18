import csv

translations = {}
with open("./"Games\game\arabic_translation_merged.tsv", 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter='\t')
    next(reader)
    for row in reader:
        if len(row) >= 2:
            try:
                idx = int(row[0])
                translations[idx] = row[1]
            except:
                pass

with open("./"long_texts.txt", 'w', encoding='utf-8') as out:
    out.write('Indices with text length > 30:\n')
    for idx in sorted(translations.keys()):
        text = translations[idx]
        if len(text) > 30:
            out.write('  Index {:4d} (len={}): {}\n'.format(idx, len(text), text[:200]))
    
    out.write('\n\nAll indices 2000+:\n')
    for idx in sorted(translations.keys()):
        if idx >= 2000:
            out.write('  Index {:4d}: {}\n'.format(idx, translations[idx][:200]))

print("Done - check long_texts.txt")