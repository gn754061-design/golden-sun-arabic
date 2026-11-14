# Golden Sun: The Lost Age - Arabic Glyph and Injection Tooling

Original tooling for the Arabic translation of *Golden Sun: The Lost Age* (GBA):
font analysis, Arabic glyph generation, shaping previews, text injection, BPS
patch creation and emulator-based visual QA.

## What is here

- `analyze_font*.py` - nine iterations of the stock font analysis.
- `generate_arabic_glyphs*.py` / `refined_glyphs.py` - Arabic glyph bitmap generation.
- `rooyin_font_builder.py` - builds the game font from the Rooyin pixel font.
- `build_arabic_map*.py` - codepoint to glyph mapping.
- `inject_arabic*.py` / `reinject_with_glyphs.py` - text injection into the ROM.
- `create_bps_patch.py` - builds the BPS delta patch.
- `run_mgba_qa.py` / `verify_*.py` - automated emulator screenshots and checks.
- `test_arabic_shaping_preview.py` - shaping and joining verification.

## What is not here

The ROM, extracted English script, the Arabic translation text and the built
patch are not distributed in this repository. It contains tooling only.

The companion repository `arabic-gba-glyphs` holds the reusable glyph pipeline.

*Golden Sun* is a trademark of Nintendo and Camelot Software Planning. This is a
non-commercial fan project.

