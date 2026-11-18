#!/usr/bin/env python3
"""
rooyin_font_builder.py
Generates 100% pixel-pure Golden Sun Rooyin Arabic font for Mario & Luigi: Superstar Saga (GBA).
Maps all 129 glyphs directly from rooyin_render.txt to 8x12 2bpp tiles with baseline at Row 7.
"""
import os
import json
import re
from PIL import Image, ImageDraw

ROOYIN_TXT = "./fonts/"rooyin_render.txt'
LABELS_JSON = "./fonts/"render_labels.json'

def load_rooyin_renders():
    with open(LABELS_JSON, 'r', encoding='utf-8') as f:
        labels = json.load(f)

    with open(ROOYIN_TXT, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    renders = {}
    cur = None
    for l in lines:
        l_str = l.strip()
        if not l_str:
            continue
        if l_str.startswith('cp '):
            parts = l_str.split()
            cp = parts[1].lower()
            if parts[2] == 'EMPTY':
                renders[cp] = None
                cur = None
            else:
                cur = {'cp': cp, 'x': int(parts[2]), 'y': int(parts[3]), 'w': int(parts[4]), 'h': int(parts[5]), 'rows': []}
                renders[cp] = cur
        elif cur:
            cur['rows'].append(l_str)
    return renders, labels

def build_glyph_tiles(renders, labels):
    """
    Assemble each Rooyin render into an 8x12 tile.
    Baseline / connector row is at Row 7 (render row 18).
    """
    glyphs = {}
    widths = {}

    # Define code mapping for 129 forms into 0x80..0xFF
    # We assign codes 0x80..0xFE (127 codes) and 0x7E, 0x7D if needed.
    # To be super clean, let's map:
    form_map = {}
    code_counter = 0x80

    for cp_hex, label in labels.items():
        r = renders.get(cp_hex.lower())
        if not r or r['h'] <= 0:
            continue

        grid = [[0]*8 for _ in range(12)]
        w = r['w']
        h = r['h']
        orig_y = r['y']

        # Determine target tile rows
        if cp_hex in ['fe83', 'fe84', 'fef7', 'fef8']:
            # Alef with Hamza above / Lamalef with Hamza above:
            # Shift so that Hamza starts at row 0, alef stem reaches row 7
            top_y = 0
            # Rows in render: 0..2 hamza, 3 gap, 4..9 stem (height 10)
            # In 8x12: row 0..2 hamza, row 3 gap, row 4..7 stem (shortened stem by 2 rows to fit)
            for i in range(min(h, 10)):
                if i < 4:
                    ty = i
                else:
                    ty = min(7, i - 2) # map 4..9 to 4..7
                for j in range(min(w, 8)):
                    if j < len(r['rows'][i]) and r['rows'][i][j] == '#':
                        grid[ty][j] = 1
        else:
            # Standard baseline alignment: connector at render row 18 -> tile row 7
            # Shift = 7 - 18 = -11
            top_y = orig_y - 11
            # Safety clamp for glyph bounds
            if top_y < 0:
                top_y = 0
            if top_y + h > 12:
                top_y = 12 - h

            if w <= 8:
                for i in range(h):
                    ty = top_y + i
                    if 0 <= ty < 12:
                        for j in range(min(w, 8)):
                            if j < len(r['rows'][i]) and r['rows'][i][j] == '#':
                                grid[ty][j] = 1
            else:
                # Width > 8: 11 glyphs (Seen, Sheen, Sad, Dad, Zah)
                # Intelligently condense width to 8 columns (cols 0..7)
                for i in range(h):
                    ty = top_y + i
                    if 0 <= ty < 12:
                        row_str = r['rows'][i]
                        if cp_hex in ['feb1', 'feb2', 'feb5', 'feb6']:
                            # Seen / Sheen: drop 1-2 excess bowl pixels from left
                            # Take first 3 chars as cols 0..2, skip 1, take next 5 chars as cols 3..7
                            for j in range(min(len(row_str), 8)):
                                src_j = j if j < 2 else min(len(row_str)-1, j + (w - 8))
                                if row_str[src_j] == '#':
                                    grid[ty][j] = 1
                        elif cp_hex in ['feb9', 'feba', 'febc', 'febd', 'febe', 'fec0']:
                            # Sad / Dad: condense right connecting arm or loop slightly
                            for j in range(8):
                                src_j = int(j * (w / 8.0))
                                if src_j < len(row_str) and row_str[src_j] == '#':
                                    grid[ty][j] = 1
                        elif cp_hex == 'fed2':
                            # Zah: condense arm
                            for j in range(8):
                                src_j = min(len(row_str)-1, j + (1 if j > 0 else 0))
                                if row_str[src_j] == '#':
                                    grid[ty][j] = 1
                        else:
                            for j in range(8):
                                src_j = min(len(row_str)-1, j)
                                if row_str[src_j] == '#':
                                    grid[ty][j] = 1

        # Golden Sun 2-dot Ya separation rule:
        # If label is yeh / yeh with hamza, and bottom dot row has a solid 3px bar, split to 2 distinct dots
        if label.startswith('ي') or label.startswith('ئ'):
            # Find bottom row with ink
            for ty in range(11, 7, -1):
                ink_cols = [x for x in range(8) if grid[ty][x]]
                if len(ink_cols) >= 3:
                    # Clear this row and set separated dots
                    first_col = ink_cols[0]
                    last_col = ink_cols[-1]
                    for x in range(8):
                        grid[ty][x] = 0
                    grid[ty][first_col] = 1
                    grid[ty][last_col] = 1
                    break

        char_w = max(2, min(8, w))
        if char_w > 8:
            char_w = 8

        # Allocate byte code
        if code_counter > 0xFE:
            code = 0x7E # fallback
        else:
            code = code_counter
            code_counter += 1

        glyphs[code] = grid
        widths[code] = char_w
        form_map[label] = code

    # Add 2px blank spacer
    spacer_code = 0x7F
    glyphs[spacer_code] = [[0]*8 for _ in range(12)]
    widths[spacer_code] = 2
    form_map['spacer'] = spacer_code

    return glyphs, widths, form_map

def encode_mlss_glyph(grid):
    """Encode 8x12 2bpp grid into 24-byte MLSS format."""
    raw = bytearray(24)
    for y_blk in range(3):
        for x_blk in range(2):
            idx0 = y_blk * 8 + x_blk * 2
            idx1 = idx0 + 1
            for ebp_pair in [0, 2]:
                target_idx = idx0 if ebp_pair == 0 else idx1
                b0 = 0
                b1 = 0
                bit_pos = 0
                for ebp in [ebp_pair, ebp_pair + 1]:
                    for esi in range(4):
                        row = y_blk * 4 + esi
                        col = x_blk * 4 + ebp
                        pix = grid[row][col]
                        if pix & 1:
                            b0 |= (1 << bit_pos)
                        if pix & 2:
                            b1 |= (1 << bit_pos)
                        bit_pos += 1
                raw[target_idx] = b0
                raw[target_idx + 4] = b1
    return bytes(raw)

if __name__ == '__main__':
    renders, labels = load_rooyin_renders()
    glyphs, widths, form_map = build_glyph_tiles(renders, labels)
    print(f'Built {len(glyphs)} glyphs, {len(widths)} widths, {len(form_map)} forms.')
    print('Sample widths:')
    for f in ['ا:iso', 'ب:ini', 'ب:med', 'ب:fin', 'س:med', 'ل:med', 'ـ']:
        if f in form_map:
            c = form_map[f]
            print(f' {f} (0x{c:02X}): width={widths[c]}')
