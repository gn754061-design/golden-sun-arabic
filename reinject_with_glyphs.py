#!/usr/bin/env python3
"""
Complete re-injection with proper Arabic glyphs
"""

import struct
import shutil

SRC_ROM = r"C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU.gba"
DST_ROM = r"C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU_AR.gba"
FONT_BIN = r"C:\Users\user\Desktop\game\arabic_font_tiles.bin"

FONT_TILES_ADDR = 0x00947538
WIDTH_TABLE_ADDR = 0x009418F0
STORY_PTR_TABLE = 0x004EA268
GBA_ROM_BASE = 0x08000000
EXPANDED_BASE = 0x01000000

# Arabic font code mapping (matches generate_arabic_glyphs.py)
arabic_map = {
    ' ': 0x20,
    '\u0627': 0xA0, '\u0628': 0xA1, '\u062A': 0xA2, '\u062B': 0xA3,
    '\u062C': 0xA4, '\u062D': 0xA5, '\u062E': 0xA6, '\u062F': 0xA7,
    '\u0630': 0xA8, '\u0631': 0xA9, '\u0632': 0xAA, '\u0633': 0xAB,
    '\u0634': 0xAC, '\u0635': 0xAD, '\u0636': 0xAE, '\u0637': 0xAF,
    '\u0638': 0xB0, '\u0639': 0xB1, '\u063A': 0xB2, '\u0641': 0xB3,
    '\u0642': 0xB4, '\u0643': 0xB5, '\u0644': 0xB6, '\u0645': 0xB7,
    '\u0646': 0xB8, '\u0647': 0xB9, '\u0648': 0xBA, '\u0649': 0xBB,
    '\u064A': 0xBC,
    '\u0623': 0xBD, '\u0625': 0xBE, '\u0622': 0xBF, '\u0621': 0xC0,
    '\u0629': 0xC1, '\u0624': 0xC2, '\u0626': 0xC3,
    '\u0640': 0xC4,
    '.': 0xC5, ',': 0xC6, '!': 0xC7, '?': 0xC8, ':': 0xC9, ';': 0xCA,
    '(': 0xCB, ')': 0xCC, '[': 0xCD, ']': 0xCE, '{': 0xCF, '}': 0xD0,
    '-': 0xD1, '_': 0xD2, '+': 0xD3, '=': 0xD4, '*': 0xD5, '/': 0xD6,
    '\\': 0xD7, '|': 0xD8, '<': 0xD9, '>': 0xDA, '@': 0xDB, '#': 0xDC,
    '$': 0xDD, '%': 0xDE, '^': 0xDF, '&': 0xE0, '~': 0xE1, '`': 0xE2,
    '"': 0xE3, "'": 0xE4,
    '0': 0xE5, '1': 0xE6, '2': 0xE7, '3': 0xE8, '4': 0xE9,
    '5': 0xEA, '6': 0xEB, '7': 0xEC, '8': 0xED, '9': 0xEE,
    '\u060C': 0xEF, '\u061B': 0xF0, '\u061F': 0xF1, '\u066A': 0xF2,
    'A': 0xF3, 'B': 0xF4, 'C': 0xF5, 'D': 0xF6, 'E': 0xF7,
}

# Approximate widths for Arabic glyphs
arabic_widths = {
    0xA0: 4, 0xA1: 5, 0xA2: 5, 0xA3: 5, 0xA4: 5, 0xA5: 5, 0xA6: 5, 0xA7: 4,
    0xA8: 4, 0xA9: 4, 0xAA: 4, 0xAB: 5, 0xAC: 5, 0xAD: 5, 0xAE: 5, 0xAF: 5,
    0xB0: 5, 0xB1: 5, 0xB2: 5, 0xB3: 5, 0xB4: 5, 0xB5: 5, 0xB6: 4, 0xB7: 5,
    0xB8: 5, 0xB9: 5, 0xBA: 5, 0xBB: 4, 0xBC: 4,
    0xBD: 4, 0xBE: 4, 0xBF: 4, 0xC0: 3, 0xC1: 4, 0xC2: 4, 0xC3: 4,
    0xC4: 3, 0xC5: 2, 0xC6: 2, 0xC7: 3, 0xC8: 2, 0xC9: 2,
    0xCB: 2, 0xCC: 2, 0xCD: 2, 0xCE: 2, 0xCF: 2, 0xD0: 2,
    0xD1: 2, 0xD2: 2, 0xD3: 2, 0xD4: 2, 0xD5: 2, 0xD6: 2,
    0xD7: 2, 0xD8: 2, 0xD9: 2, 0xDA: 2, 0xDB: 2, 0xDC: 2,
    0xDD: 2, 0xDE: 2, 0xDF: 2, 0xE0: 2, 0xE1: 2, 0xE2: 2,
    0xE3: 3, 0xE4: 2,
    0xE5: 4, 0xE6: 4, 0xE7: 4, 0xE8: 4, 0xE9: 4,
    0xEA: 4, 0xEB: 4, 0xEC: 4, 0xED: 4, 0xEE: 4,
    0xEF: 2, 0xF0: 2, 0xF1: 3, 0xF2: 3,
    0xF3: 4, 0xF4: 4, 0xF5: 4, 0xF6: 4, 0xF7: 4,
}

# Arabic story translations (entries 236-405)
ARABIC_STORY = {
    236: "هذا هو الحجر الأخير!{02}",
    237: "هذه فرصتنا الأخيرة!{02}",
    238: "هاه... هاف... هورف...{02}",
    239: "موه؟!? ماذا تظنان؟{03}",
    240: "هيه؟ ماذا؟ تريدان منا أن{03}",
    241: "يا إلهي! أعرف هذين الشخصين!{05}",
    242: "نعم! أنت محق تماماً، سلدج!{05}",
    243: "أوه! انظروا... ليس لديكما{03}",
    244: "صحيح تماماً. المحترفون طوال الطريق.{02}",
    245: "لكن المشكلة هي، من أجل{05}",
    246: "صخور +هوهوه {20}أحجار صلبة.{05}",
    247: "أوه نعم! ماذا كنت أفكر؟{05}",
    248: "إذن، هل تقولان إنكما تستطيعان الذهاب{05}",
    249: "هذا سيربطنا حقاً!{05}",
    250: "تخدشون ظهورنا، يا برز،{03}",
    251: "أنا ماليت، الأصغر بين{05}",
    252: "إذا حصلتم على بعض صخور +هوهوه {20}،{03}",
    253: "يجب على الجميع تسلق هوهوه{05}",
    254: "للوصول إلى قمة جبل هوهوه،{05}",
    255: "رأيت أمير هذه المملكة،{05}",
    256: "الآن بعد أن عاد بلابلانادون،{03}",
    257: "هل قابلتم سلدج و{05}",
    258: "أن يكون لديك منزل فوق{05}",
    259: "هذه قرية هوهوه، على{05}",
    260: "إذا نزلتم من هذا الجبل،{05}",
    261: "بغض النظر عن المدة التي تنتظرون،{05}",
    262: "سقط نيزك من{05}",
    263: "أنا سعيد جداً لأن بلابلانادون{03}",
    264: "إيه؟ تريدان النزول{03}",
    265: "الصور التصويرية على الجدران هنا{05}",
    266: "سئمت العيش في العزلة.{05}",
    267: "آه... ضباب الشلال يشعركم{03}",
    268: "أتمنى لو استطعنا الوقوف هنا{03}",
    269: "إذا اتجهتم لليسار، يمكنكم التسلق{03}",
    270: "لا داعي للقلق إطلاقاً{05}",
    271: "منذ زمن طويل، على هذا الجبل ذاته،{05}",
    272: "يُقال إننا أحفاد{05}",
    273: "الجسر مكسور، لذا نحن{05}",
    274: "لا يمكنكما تسلق الجبل{03}",
    275: "الجنود يأتون إلى المدينة...{05}",
    276: "انتهينا من إصلاح الجسر!{05}",
    277: "كيف كان المنظر من{03}",
    278: "مسار جبل هوهوه {20}{04} {11}{01}",
    279: "مسار جبل هوهوه {20}{02}{11}{01}",
    280: "ثقب سقاية جبل هوهوه {20}{04} {11}{01}",
    281: "القمة أمامكم!{11}{01}{03}{05}{35}5",
    282: "تحذير +العاصفة الدوارة{20} {05}{35}5",
    283: "احذروا الإفراط في الترطيب!{17}{03}{05}{35}5",
    284: "آه. مسافرون. أنا هوهوروس.{05}",
    285: "بعد هذه النقطة، الطريق{05}",
    286: "هل تجرؤون على تجربة هذا التحدي؟{03}{05}{35}5",
    287: "يجب أن تبدؤوا الآن. ويجب أن{05}",
    288: "ابدأ!{19}[0C][0C]{05}{35}5",
    289: "كفى!!!{1E}[0C][0C]",
    290: "لقد فشلتم!{1E}[0C][0C]",
    291: "تجربون التحدي مرة أخرى؟{03}{05}{35}5",
    292: "لقد أزلتم{03}",
    293: "الآن للتحدي القادم.{11}{01}",
    294: "عليكما هزيمتي!{0C}[31]1{03}{05}",
    295: "لقد اجتزتم هذا الاختبار أيضاً!{05}",
    296: "حمقى!!!{19}([0C][0C]{05}{35}5",
    297: "لماذا تركل ذلك؟{05}",
    298: "إيه؟ اسمي؟ آه... صحيح!{03}",
    299: "ماذا؟ أهل المدينة كلهم{05}",
    300: "أوه! إنه هنا! حان الوقت!{05}",
    301: "غو-غوااا!{1E}([0C][0C]{05}{35}5{33}3",
    302: "آك! حسناً، هذه صدمة!{03}",
    303: "صحة لشاربيكما!{11}{01}",
    304: "هذا الرجل المبهر بشكل لا يصدق هو{05}",
    305: "حسناً! أعتقد أنه يمكنكما تسميته{03}",
    306: "بينما كنت أتحقق من الأحداث{05}",
    307: "ولكن بحلول الوقت الذي أدركت فيه من{03}",
    308: "لقد حولوني إلى ذلك{03}",
    309: "آه هه هه هه هه!{1E}([0C][0C]{05}{35}5",
    310: "كا-سووش!{1E}[0C][0C]",
    311: "زنغ!{1E}[0C][0C]",
    312: "هه هه هه!{1E}[0C][0C]",
    313: "أهذا صحيح؟ صوت الأميرة بيتش{03}",
    314: "هه هه هه... لا داعي للقلق{05}",
    315: "على أي حال، يجب أن نلاحق{03}",
    316: "أريدكما زيارة +الملكة بين{20} {05}",
    317: "أوه! هه هه هه... إليكما هدية{03}",
    318: "هه هه هه... نعم، أعتقد وردة{03}",
    319: "وبذلك، يجب أن{03}",
    320: "سآخذكما إلى القمة!{11}{01}",
    321: "تريدان الذهاب إلى القمة؟{03}",
    322: "ستضطران للمشي عائدين{05}",
    323: "همف! يا فتى، هل وصلتما{03}",
    324: "انظروا: سنستخدمه لصنع{03}",
    325: "هو! هو! هووو... يا رجل، شعور{05}",
    326: "في الواقع، شعور رائع جداً{05}",
    327: "انظروا إلى تلك الحرفية! بوو!{03}",
    328: "نعم! أصبت الهدف! هذه{03}",
    329: "حصلتم على مطارق!{11}[25]%A{41}[0C][0C]",
    330: "يمكنكما استخدام حركة المطارق الفردية!{11}[25]%A{41}",
    331: "أعتقد أننا يجب أن نعلمكما{03}",
    332: "أولاً، اضغط زر +{1A}{1B}{20} لكي{03}",
    333: "مطرقة{0C}[25]%A{41}{05}[03]{35}5",
    334: "ثم اضغط زر +{1C}{1D}{20}{03}",
    335: "لكن، مهلا، الآن فقط الرجل{03}",
    336: "إذن، حركة الرجل في المقدمة{05}",
    337: "جربوا ضرب جميع أنواع الأشياء{05}",
    338: "تعلمون، يجب عليكما كسر ذلك{05}",
    339: "اضغط زر +{0D}{0D}{01}[1A][1B]{20} لتغيير{05}",
    340: "***عربات المنجم الغامضة*** {20}{05}{03}{35}5",
    341: "منطقة حقول الغبار النجمي 64{11}{01}{03}",
    342: "عندما ترغبون في القفز إلى{05}",
    343: "أولاً، اضغط زر +{18}{19}{20} لكي{03}",
    344: "قفزة عالية{0C}[25]%A{41}{05}[03]",
    345: "ثم اضغط زر +{1E}{1F}{20} للقفز!{11}{01}",
    346: "في اللحظة التي تقفزون فيها عليه،{03}",
    347: "انظروا؟ يمكنكما القفز أعلى من{05}",
    348: "هل تحتاجون{05}{35}5",
    349: "جيد جداً، لويجي! إذن استخدموا{05}",
    350: "عمل ممتاز، رجال!{11}{01}",
    351: "إذا استخدمتم قفزتكم +العالية{20}{05}",
    352: "{18}{19}: اختر {1E}{1F}: أداء حركة{02}[25]%A{41}[03]",
    353: "البداية: تبديل المواقع {18}{19}: اختر{03}{03}{35}5{25}%A{41}",
    354: "الآن، اضغط +البداية{20} لتغيير{05}",
    355: "اضغط زر +{18}{19}{20} للاختيار{03}",
    356: "قفزة دوارة{0C}[25]%A{41}{05}[03]{35}5",
    357: "ثم اضغط زر +{1E}{1F}{20} للقفز!{11}{01}",
    358: "ترون؟ أنتم تركبون على الظهر!{11}{01}",
    359: "الآن، إذا ضغطتم زر +{1E}{1F}{20}{05}",
    360: "اضغط +لوحة التحكم{20} أثناء{03}",
    361: "يمكن استخدام هذه القفزة {2D}الدوارة{20}{05}",
    362: "حسناً، ماريو! إذن استخدم{05}",
    363: "ممتاز!{11}{01}",
    364: "انظروا، يا أولاد، الحركات التي{05}",
    365: "انتهى التدريب!{11}{01}",
    366: "جاهزان للعودة؟{06}[25]%A{41}[05]",
    367: "انقل {29}لويجي{20} للخلف واضغط{09}",
    368: "انقل {2D}ماريو{20} للخلف واضغط{08}",
    369: "لقد فشلتم! لكن التعلم دائماً{03}",
    370: "ماريو ولويجي! يا سادة!{0C}({03}[31]1",
    371: "هذا لقاء عاطفي، يا سادة!{11}{01}",
    372: "بإذنكم، هناك شيء{05}",
    373: "بالتأكيد! ترون، عندما{05}",
    374: "الآن وقد تعلمتم{05}",
    375: "يجب تأكيد التقنية{03}",
    376: "بهذا يمكننا تأكيد{05}",
    377: "التخطيط والإعداد السليم{05}",
    378: "الجنرال ستارشيد!{11}[03]{05}",
    379: "تأكيد!{05}[03]{35}5",
    380: "الجنرال ستارشيد!{03}[03]",
    381: "تأثير في حقول الغبار النجمي{02}[03]{35}5",
    382: "حالة طوارئ!{03}[03]{35}5",
    383: "حدود أرض الفاصولياء{0C}[25]%A{41}Z{02}[03]{35}5",
    384: "لا توجد قائمة هنا،{05}",
    385: "ماريو! لويجي!{0C}#[03]",
    386: "السيدة ليما طلبت أن{05}",
    387: "هذا +شارة{20}.{05}",
    388: "جهزوا هذا الآن.{05}",
    389: "الآن أنتم جاهزون!{03}",
    390: "أوه، آه... آسف، لويجي، لكن إذا{05}",
    391: "دير... بغض النظر عما تضربني به{03}",
    392: "{03}",
    393: "{03}",
    394: "{03}",
    395: "{03}",
    396: "أيها الأشرار!!!{11}-[0C][0C]{05}{35}5{33}3",
    397: "وجدناكم أخيراً!{05}",
    398: "نعم! لا مجال للخطأ!{03}",
    399: "لدينا شهود!{03}",
    400: "ماذا؟ تقولان إنكما{03}",
    401: "كذب! كذب صريح!{05}",
    402: "نيه... نك نيههه...{03}",
    403: "يقولون إنهم جاؤوا إلى هنا{05}",
    404: "أوه، عزيزي. يا إلهي! يا ولد!{03}",
    405: "وفقاً لشهادات شهود العيان،{05}",
}

# Control code mapping
ctrl_map = {
    '{01}': 0x01, '{02}': 0x02, '{03}': 0x03, '{04}': 0x04,
    '{05}': 0x05, '{06}': 0x06, '{07}': 0x07, '{08}': 0x08,
    '{09}': 0x09, '{0A}': 0x0A, '{0B}': 0x0B, '{0C}': 0x0C,
    '{0D}': 0x0D, '{0E}': 0x0E, '{0F}': 0x0F, '{10}': 0x10,
    '{11}': 0x11, '{12}': 0x12, '{13}': 0x13, '{14}': 0x14,
    '{15}': 0x15, '{16}': 0x16, '{17}': 0x17, '{18}': 0x18,
    '{19}': 0x19, '{1A}': 0x1A, '{1B}': 0x1B, '{1C}': 0x1C,
    '{1D}': 0x1D, '{1E}': 0x1E, '{1F}': 0x1F, '{20}': 0x20,
    '{21}': 0x21, '{22}': 0x22, '{23}': 0x23, '{24}': 0x24,
    '{25}': 0x25, '{26}': 0x26, '{27}': 0x27, '{28}': 0x28,
    '{29}': 0x29, '{2A}': 0x2A, '{2B}': 0x2B, '{2C}': 0x2C,
    '{2D}': 0x2D, '{2E}': 0x2E, '{2F}': 0x2F, '{30}': 0x30,
    '{31}': 0x31, '{32}': 0x32, '{33}': 0x33, '{34}': 0x34,
    '{35}': 0x35, '{36}': 0x36, '{37}': 0x37, '{38}': 0x38,
    '{39}': 0x39, '{3A}': 0x3A, '{3B}': 0x3B, '{3C}': 0x3C,
    '{3D}': 0x3D, '{3E}': 0x3E, '{3F}': 0x3F,
    '{40}': 0x40, '{41}': 0x41,
}

# Special FF-prefixed control codes (from original English)
ff_ctrl_map = {
    '[FF 0B]': (0xFF, 0x0B),
    '[FF 11]': (0xFF, 0x11),
    '[FF 0C]': (0xFF, 0x0C),
    '[FF 2B]': (0xFF, 0x2B),
    '[FF 20]': (0xFF, 0x20),
    '[FF 25]': (0xFF, 0x25),
    '[FF 29]': (0xFF, 0x29),
    '[FF 2D]': (0xFF, 0x2D),
    '[FF 31]': (0xFF, 0x31),
    '[FF 33]': (0xFF, 0x33),
    '[FF 35]': (0xFF, 0x35),
    '[FF 41]': (0xFF, 0x41),
}

def convert_text(text):
    """Convert Arabic text with control codes to font code bytes"""
    codes = []
    i = 0
    while i < len(text):
        # {XX} control codes
        if text[i] == '{' and i + 3 < len(text) and text[i+3] == '}':
            ctrl = text[i:i+4]
            if ctrl in ctrl_map:
                codes.append(ctrl_map[ctrl])
                i += 4
                continue
        # [FF XX] control codes
        if text[i] == '[' and i + 7 <= len(text):
            bracket = text[i:i+8]
            if bracket in ff_ctrl_map:
                codes.extend(ff_ctrl_map[bracket])
                i += 8
                continue
        # +item+ names (encode as regular text for now)
        if text[i] == '+' and '+' in text[i+1:]:
            end = text.find('+', i+1)
            for ch in text[i:end+1]:
                codes.append(arabic_map.get(ch, 0x20))
            i = end + 1
            continue
        # Regular character
        ch = text[i]
        code = arabic_map.get(ch, 0x20)
        codes.append(code)
        i += 1
    return codes

def build_message(font_codes, box_style=(0x14, 0x05)):
    """Build message with proper format: box_style + FF 0B 01 + codes + FF 0A 00 00"""
    data = bytearray()
    data.append(box_style[0])
    data.append(box_style[1])
    data.append(0xFF)
    data.append(0x0B)
    data.append(0x01)
    data.extend(font_codes)
    data.append(0xFF)
    data.append(0x0A)
    data.append(0x00)
    data.append(0x00)
    return bytes(data)

def main():
    print("=" * 60)
    print("MLSS_EU.gba Arabic Re-Injection (Proper Glyphs)")
    print("=" * 60)

    # Load generated font tiles
    with open(FONT_BIN, 'rb') as f:
        font_tiles = f.read()
    print(f"Loaded font tiles: {len(font_tiles)} bytes ({len(font_tiles)//32} glyphs)")

    # Copy clean ROM and expand
    print("\n[1] Copying clean ROM and expanding to 32MB...")
    shutil.copy2(SRC_ROM, DST_ROM)
    with open(DST_ROM, 'rb') as f:
        rom = bytearray(f.read())
    original_size = len(rom)
    rom.extend(b'\x00' * (0x02000000 - original_size))
    print(f"    Size: {len(rom)} bytes")

    # Inject font tiles
    print("\n[2] Injecting proper Arabic font tiles (0xA0-0xFF)...")
    for code in range(0xA0, 0x100):
        tile = font_tiles[(code - 0xA0) * 32:(code - 0xA0) * 32 + 32]
        offset = FONT_TILES_ADDR + code * 32
        rom[offset:offset+32] = tile
    print(f"    96 tiles injected")

    # Update width table
    print("\n[3] Updating width table...")
    for code in range(0xA0, 0x100):
        rom[WIDTH_TABLE_ADDR + code] = arabic_widths.get(code, 6)
    print(f"    Widths updated")

    # Inject story dialogues
    print("\n[4] Injecting 170 story dialogues...")
    write_offset = EXPANDED_BASE
    updated = 0
    
    for entry in range(236, 406):
        if entry not in ARABIC_STORY:
            continue
        arabic_text = ARABIC_STORY[entry]
        
        ptr_idx = entry * 5
        ptr_offset = STORY_PTR_TABLE + ptr_idx * 4
        orig_ptr = struct.unpack('<I', rom[ptr_offset:ptr_offset+4])[0]
        if orig_ptr == 0:
            continue
        orig_file_off = orig_ptr - GBA_ROM_BASE
        if not (0x003EC000 <= orig_file_off < 0x003F0000):
            continue
        
        # Determine box style from original
        orig_data = rom[orig_file_off:orig_file_off+2]
        box_style = (orig_data[0], orig_data[1]) if len(orig_data) == 2 else (0x14, 0x05)
        
        # Convert and build message
        font_codes = convert_text(arabic_text)
        msg_data = build_message(font_codes, box_style)
        
        if write_offset + len(msg_data) > len(rom):
            print(f"    WARNING: Space full at entry {entry}")
            break
        
        rom[write_offset:write_offset+len(msg_data)] = msg_data
        new_gba_ptr = GBA_ROM_BASE + write_offset
        rom[ptr_offset:ptr_offset+4] = struct.pack('<I', new_gba_ptr)
        
        updated += 1
        write_offset += len(msg_data)
        write_offset = (write_offset + 3) & ~3
    
    print(f"    Injected {updated} dialogues, used {write_offset - EXPANDED_BASE} bytes")

    # Write ROM
    print("\n[5] Writing modified ROM...")
    with open(DST_ROM, 'wb') as f:
        f.write(rom)
    print(f"    Done: {DST_ROM}")

    # Verification
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    with open(DST_ROM, 'rb') as f:
        rom = f.read()
    
    # Check font tiles
    sample = rom[FONT_TILES_ADDR + 0xA0*32:FONT_TILES_ADDR + 0xA0*32+16]
    print(f"\nFont tile 0xA0 (first 16 bytes): {' '.join(f'{b:02X}' for b in sample)}")
    
    # Check first 5 pointers
    print("\nFirst 5 updated pointers:")
    for entry in range(236, 241):
        ptr_idx = entry * 5
        ptr_offset = STORY_PTR_TABLE + ptr_idx * 4
        ptr = struct.unpack('<I', rom[ptr_offset:ptr_offset+4])[0]
        file_off = ptr - GBA_ROM_BASE
        if 0x01000000 <= file_off < 0x02000000:
            msg = rom[file_off:file_off+32]
            print(f"  Entry {entry}: GBA 0x{ptr:08X} (file 0x{file_off:08X})")
            print(f"    Bytes: {' '.join(f'{b:02X}' for b in msg)}")

if __name__ == '__main__':
    main()