#!/usr/bin/env python3
"""
Font extraction, Arabic font generation, and canary injection for MLSS_EU.gba
"""
import struct
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROM_PATH = Path(r"C:\Users\user\Desktop\game\MLSS_AR\work\MLSS_EU.gba")
FONT_TILES_ADDR = 0x00947538
WIDTH_TABLE_ADDR = 0x009418F0
STORY_BLOCK_220 = 0x003EBB04  # "I must find Mario immediately!" location

# Arabic test string
ARABIC_TEST = "أهلا بك في مملكة الفاصولياء"

def read_rom():
    with open(ROM_PATH, 'rb') as f:
        return bytearray(f.read())

def write_rom(rom):
    with open(ROM_PATH, 'wb') as f:
        f.write(rom)

# ============================================================
# 1. EXTRACT FONT TILES AND BUILD CHARACTER MAP
# ============================================================
def extract_font(rom):
    """Extract 256 8x8 4bpp tiles from font data"""
    font_data = rom[FONT_TILES_ADDR:FONT_TILES_ADDR + 256*32]
    tiles = []
    for t in range(256):
        tile_data = font_data[t*32:(t+1)*32]
        # Convert 4bpp to 8x8 pixel values (0-15)
        pixels = []
        for row in range(8):
            # Each row = 4 bytes (4bpp = 2 pixels per byte, but interleaved planes)
            # 4bpp GBA: 4 bitplanes, each 8 bytes = 8x8
            b0 = tile_data[row*4 + 0]
            b1 = tile_data[row*4 + 1]
            b2 = tile_data[row*4 + 2]
            b3 = tile_data[row*4 + 3]
            row_pixels = []
            for c in range(8):
                val = ((b3 >> (7-c)) & 1) * 8 + ((b2 >> (7-c)) & 1) * 4 + \
                      ((b1 >> (7-c)) & 1) * 2 + ((b0 >> (7-c)) & 1)
                row_pixels.append(val)
            pixels.append(row_pixels)
        tiles.append(pixels)
    return tiles

def tiles_to_image(tiles, cols=16):
    """Convert tiles to a single image for visualization"""
    rows = (len(tiles) + cols - 1) // cols
    img = Image.new('P', (cols*8, rows*8))
    # Create a palette (16 colors for 4bpp)
    palette = []
    for i in range(16):
        # Simple grayscale palette
        v = i * 17
        palette.extend([v, v, v])
    img.putpalette(palette)
    
    for idx, tile in enumerate(tiles):
        x = (idx % cols) * 8
        y = (idx // cols) * 8
        for ty in range(8):
            for tx in range(8):
                img.putpixel((x+tx, y+ty), tile[ty][tx])
    return img

def find_char_mapping(rom, tiles):
    """Find which tile index corresponds to each ASCII character"""
    # The text uses ASCII 0x20-0x7E
    # Check width table - non-zero entries for printable chars
    wt = rom[WIDTH_TABLE_ADDR:WIDTH_TABLE_ADDR+256]
    
    # Printable ASCII with non-zero width
    char_widths = {}
    for i in range(0x20, 0x7F):
        if wt[i] != 0 and wt[i] != 0xFF:
            char_widths[i] = wt[i]
    
    print(f"Characters with defined widths: {len(char_widths)}")
    for c, w in sorted(char_widths.items()):
        print(f"  0x{c:02X} ('{chr(c)}'): width={w}")
    
    # The mapping is likely: tile_index = char_code - 0x20 (for ASCII)
    # But let's verify by checking tile content
    # Tile 0 is at 0x00947538, likely space (0x20) or first printable
    
    return char_widths

# ============================================================
# 2. GENERATE ARABIC GLYPHS
# ============================================================
def generate_arabic_glyphs():
    """Generate Arabic letter forms for 0xA0-0xFF"""
    # Arabic presentation forms - we'll map:
    # 0xA0-0xBF: Isolated forms
    # 0xC0-0xDF: Initial forms  
    # 0xE0-0xFF: Medial/Final forms
    
    # Arabic letters in Unicode order
    arabic_letters = [
        'ا', 'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'د', 'ذ', 'ر', 'ز', 'س', 'ش',
        'ص', 'ض', 'ط', 'ظ', 'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'و', 'ى', 'ي'
    ]
    
    # Try to use a system Arabic font
    try:
        font = ImageFont.truetype("arial.ttf", 8)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
        except:
            font = ImageFont.load_default()
    
    # Generate 8x8 glyphs for each code point
    glyphs = {}
    
    # Keep ASCII 0x20-0x7E as-is (will copy from original)
    # Generate for 0xA0-0xFF
    for i, letter in enumerate(arabic_letters):
        if i >= 96:  # Only 96 slots (0xA0-0xFF)
            break
        code = 0xA0 + i
        
        # Create 8x8 image
        img = Image.new('L', (8, 8), 0)
        draw = ImageDraw.Draw(img)
        # Draw letter centered
        bbox = draw.textbbox((0, 0), letter, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (8 - w) // 2
        y = (8 - h) // 2 - 1
        draw.text((x, y), letter, fill=255, font=font)
        
        # Convert to 4bpp (16 levels)
        pixels = []
        for ty in range(8):
            row = []
            for tx in range(8):
                val = img.getpixel((tx, ty))
                row.append(min(15, val // 17))
            pixels.append(row)
        glyphs[code] = pixels
    
    # Fill remaining with placeholder
    for code in range(0xA0 + len(arabic_letters), 0x100):
        pixels = [[0]*8 for _ in range(8)]
        # Draw code number as pattern
        for y in range(8):
            for x in range(8):
                pixels[y][x] = 15 if (x == code % 8 or y == code // 8) else 0
        glyphs[code] = pixels
    
    return glyphs

def glyph_to_4bpp(pixels):
    """Convert 8x8 pixel values (0-15) to 32-byte 4bpp tile"""
    tile = bytearray(32)
    for row in range(8):
        b0 = b1 = b2 = b3 = 0
        for col in range(8):
            val = pixels[row][col] & 0xF
            bit = 7 - col
            if val & 1: b0 |= (1 << bit)
            if val & 2: b1 |= (1 << bit)
            if val & 4: b2 |= (1 << bit)
            if val & 8: b3 |= (1 << bit)
        tile[row*4 + 0] = b0
        tile[row*4 + 1] = b1
        tile[row*4 + 2] = b2
        tile[row*4 + 3] = b3
    return bytes(tile)

# ============================================================
# 3. INJECT ARABIC FONT AND CANARY STRING
# ============================================================
def inject_arabic_font(rom, arabic_glyphs):
    """Replace tiles 0xA0-0xFF with Arabic glyphs"""
    # Tile index = char_code (assuming direct mapping)
    # Original tiles at FONT_TILES_ADDR
    for code in range(0xA0, 0x100):
        if code in arabic_glyphs:
            tile_data = glyph_to_4bpp(arabic_glyphs[code])
            offset = FONT_TILES_ADDR + code * 32
            rom[offset:offset+32] = tile_data
    
    # Update width table for Arabic chars (estimate 6 pixels wide)
    for code in range(0xA0, 0x100):
        rom[WIDTH_TABLE_ADDR + code] = 6
    
    print(f"Injected {len(arabic_glyphs)} Arabic glyphs at 0x{FONT_TILES_ADDR:08X}")
    print(f"Updated width table at 0x{WIDTH_TABLE_ADDR:08X}")

def reshape_arabic(text):
    """Reshape Arabic text for display (using python-bidi logic)"""
    # Simplified: just reverse for RTL (proper shaping needs arabic-reshaper)
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except ImportError:
        # Fallback: simple reversal
        return text[::-1]

def arabic_to_font_codes(text):
    """Convert Arabic text to font codes 0xA0-0xFF"""
    arabic_map = {
        'ا': 0xA0, 'ب': 0xA1, 'ت': 0xA2, 'ث': 0xA3, 'ج': 0xA4, 'ح': 0xA5,
        'خ': 0xA6, 'د': 0xA7, 'ذ': 0xA8, 'ر': 0xA9, 'ز': 0xAA, 'س': 0xAB,
        'ش': 0xAC, 'ص': 0xAD, 'ض': 0xAE, 'ط': 0xAF, 'ظ': 0xB0, 'ع': 0xB1,
        'غ': 0xB2, 'ف': 0xB3, 'ق': 0xB4, 'ك': 0xB5, 'ل': 0xB6, 'م': 0xB7,
        'ن': 0xB8, 'ه': 0xB9, 'و': 0xBA, 'ى': 0xBB, 'ي': 0xBC,
        ' ': 0x20,
    }
    
    codes = []
    for ch in text:
        if ch in arabic_map:
            codes.append(arabic_map[ch])
        elif ch == ' ':
            codes.append(0x20)
        else:
            codes.append(0x20)
    return codes

def inject_canary_string(rom):
    """Inject Arabic test string at Block 220 (0x003EBB04)"""
    arabic_text = ARABIC_TEST
    print("Original Arabic: [Arabic text]")
    
    # Try to reshape
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(arabic_text)
        display = get_display(reshaped)
        print("Reshaped: [Arabic text]")
    except ImportError:
        # Fallback: simple reversal
        display = arabic_text
        print("arabic-reshaper not available, using raw text")
    
    # Convert to font codes
    codes = arabic_to_font_codes(display)
    print(f"Font codes count: {len(codes)}")
    
    # Build string data: width, height, codes..., FF 0A (newline), 00 padding
    # Width = number of chars * 6 (approx), height = 2 (standard)
    str_width = len(codes) * 6
    str_height = 2
    
    data = bytearray()
    data.append(str_width & 0xFF)
    data.append(str_height & 0xFF)
    data.extend(codes)
    data.append(0xFF)
    data.append(0x0A)  # newline/end
    data.append(0x00)
    data.append(0x00)
    data.append(0x00)
    data.append(0x00)
    
    print(f"Injecting {len(data)} bytes at 0x{STORY_BLOCK_220:08X}")
    print(f"Data: {data.hex()}")
    
    # Check space available
    original = rom[STORY_BLOCK_220:STORY_BLOCK_220+64]
    print(f"Original: {original.hex()}")
    
    # Inject
    rom[STORY_BLOCK_220:STORY_BLOCK_220+len(data)] = data

# ============================================================
# 4. RUN mGBA AND CAPTURE SCREENSHOT
# ============================================================
def run_mgba_screenshot(rom_path, output_png):
    """Run mGBA headless and capture screenshot"""
    # mGBA command line options for headless screenshot
    # -c: run without GUI, --screenshot: save screenshot
    cmd = [
        "mgba", "-c", "--screenshot", output_png, str(rom_path)
    ]
    try:
        result = subprocess.run(cmd, timeout=30, capture_output=True)
        print(f"mGBA exit code: {result.returncode}")
        if result.stdout:
            print(f"stdout: {result.stdout.decode()}")
        if result.stderr:
            print(f"stderr: {result.stderr.decode()}")
        return result.returncode == 0
    except FileNotFoundError:
        print("mGBA not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("mGBA timed out")
        return False

# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("MLSS_EU.gba Arabic Font Injection & Canary Test")
    print("=" * 60)
    
    rom = read_rom()
    
    # Step 1: Extract and analyze font
    print("\n[1] Extracting font tiles...")
    tiles = extract_font(rom)
    print(f"  Extracted {len(tiles)} tiles (8x8 4bpp)")
    
    # Save font atlas for reference
    img = tiles_to_image(tiles)
    img.save("font_atlas.png")
    print("  Saved font_atlas.png")
    
    char_widths = find_char_mapping(rom, tiles)
    
    # Step 2: Generate Arabic glyphs
    print("\n[2] Generating Arabic glyphs...")
    arabic_glyphs = generate_arabic_glyphs()
    print(f"  Generated {len(arabic_glyphs)} glyphs for 0xA0-0xFF")
    
    # Step 3: Inject Arabic font
    print("\n[3] Injecting Arabic font...")
    inject_arabic_font(rom, arabic_glyphs)
    
    # Step 4: Inject canary string
    print("\n[4] Injecting canary string...")
    inject_canary_string(rom)
    
    # Step 5: Write modified ROM
    print("\n[5] Writing modified ROM...")
    write_rom(rom)
    print(f"  Written to {ROM_PATH}")
    
    # Step 6: Run mGBA and capture screenshot
    print("\n[6] Running mGBA for canary test...")
    success = run_mgba_screenshot(ROM_PATH, "canary_screenshot.png")
    
    if success:
        print("\n✓ Canary test complete! Screenshot saved as canary_screenshot.png")
    else:
        print("\n✗ mGBA screenshot failed")
    
    print("\n=== SUMMARY ===")
    print(f"Font tiles: 0x{FONT_TILES_ADDR:08X} (256 tiles, 32 bytes each)")
    print(f"Width table: 0x{WIDTH_TABLE_ADDR:08X} (256 bytes)")
    print(f"Arabic range: 0xA0-0xFF (96 glyphs)")
    print(f"Canary location: 0x{STORY_BLOCK_220:08X}")
    print(f"Test string: [Arabic: Ahla bik fi mamlakat al-fasuliyya]")

if __name__ == '__main__':
    main()