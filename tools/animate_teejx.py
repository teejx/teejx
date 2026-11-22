#!/usr/bin/env python3
"""Build switchable palette variants for the animated teejx README banner."""
from __future__ import annotations
import argparse
import base64
import copy
import io
import json
import shutil
import sys
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image
from build_profile_sections import render_variant as render_section_variant, activate as activate_section_palette

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/teejx.svg'
ASSETS = ROOT / 'assets'
PALETTE_FILE = ROOT / 'src/themes/teejx-palettes.json'
PROFILE_FILE = ROOT / 'profile.json'
SVG = 'http://www.w3.org/2000/svg'
XLINK = '{http://www.w3.org/1999/xlink}href'
ET.register_namespace('', SVG)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')


def q(tag: str) -> str:
    return f'{{{SVG}}}{tag}'


def wrap_range(root: ET.Element, start: int, end: int, cls: str) -> None:
    children = list(root)
    wrapper = ET.Element(q('g'), {'class': cls})
    for child in children[start:end]:
        wrapper.append(child)
        root.remove(child)
    root.insert(start, wrapper)


STAR_PATH = (
    'M 0 -34 C 2.2 -34 3.5 -32.2 4.1 -29.4 '
    'C 7 -13.5 13.5 -7 29.4 -4.1 '
    'C 32.2 -3.5 34 -2.2 34 0 C 34 2.2 32.2 3.5 29.4 4.1 '
    'C 13.5 7 7 13.5 4.1 29.4 '
    'C 3.5 32.2 2.2 34 0 34 C -2.2 34 -3.5 32.2 -4.1 29.4 '
    'C -7 13.5 -13.5 7 -29.4 4.1 '
    'C -32.2 3.5 -34 2.2 -34 0 C -34 -2.2 -32.2 -3.5 -29.4 -4.1 '
    'C -13.5 -7 -7 -13.5 -4.1 -29.4 C -3.5 -32.2 -2.2 -34 0 -34 Z'
)
FLOWER_PATH = (
    'M409 295.9a79 79 0 0 1 .7-112.5A80 80 0 0 0 296.6 70.3 '
    'a79 79 0 0 1-112.6.7 80.7 80.7 0 0 0-113.4-1.1C39 101 39 152 '
    '70.3 183.4s30.5 82.7.7 112.5a80.7 80.7 0 0 0-1.1 113.4 '
    'a80 80 0 0 0 113.5.4 79 79 0 0 1 113.2 0 80 80 0 0 0 '
    '113.5-.4c31-31.4 30-82.2-1.1-113.4Z'
)


def recolor_badge_image(image_el: ET.Element, palette: dict) -> None:
    """Recolor the badge's embedded bitmap while preserving antialiased edges."""
    uri = image_el.get(XLINK, '')
    if not uri.startswith('data:image/png;base64,'):
        return
    raw = base64.b64decode(uri.split(',', 1)[1])
    im = Image.open(io.BytesIO(raw)).convert('RGBA')
    px = im.load()
    old_bg = (115.0, 120.0, 166.0)
    old_ink = (228.0, 228.0, 228.0)
    new_bg = tuple(int(palette['chip'][i:i + 2], 16) for i in (1, 3, 5))
    new_ink = tuple(int(palette['ink'][i:i + 2], 16) for i in (1, 3, 5))
    bg_vec = old_bg
    ink_vec = tuple(old_ink[i] - old_bg[i] for i in range(3))
    ink_len2 = sum(v * v for v in ink_vec)
    bg_len2 = sum(v * v for v in bg_vec)
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            color = (float(r), float(g), float(b))
            # Keep the black mask/shadow pixels. Recolor only pixels lying close
            # to the badge-fill/text antialias ramps.
            from_bg = tuple(color[i] - old_bg[i] for i in range(3))
            t = sum(from_bg[i] * ink_vec[i] for i in range(3)) / ink_len2
            projected = tuple(old_bg[i] + t * ink_vec[i] for i in range(3))
            err = sum((color[i] - projected[i]) ** 2 for i in range(3))
            if -0.03 <= t <= 1.03 and err < 20 * 20:
                t = max(0.0, min(1.0, t))
                mapped = tuple(round(new_bg[i] + t * (new_ink[i] - new_bg[i])) for i in range(3))
                px[x, y] = (*mapped, a)
                continue
            bg_t = sum(color[i] * bg_vec[i] for i in range(3)) / bg_len2
            bg_proj = tuple(bg_t * bg_vec[i] for i in range(3))
            bg_err = sum((color[i] - bg_proj[i]) ** 2 for i in range(3))
            if 0 <= bg_t <= 1 and bg_err < 12 * 12:
                bg_t = max(0.0, min(1.0, bg_t))
                mapped = tuple(round(new_bg[i] * bg_t) for i in range(3))
                px[x, y] = (*mapped, a)
    out = io.BytesIO()
    im.save(out, format='PNG', optimize=True)
    image_el.set(XLINK, 'data:image/png;base64,' + base64.b64encode(out.getvalue()).decode('ascii'))


def add_soft_shapes(root: ET.Element, palette: dict) -> None:
    """Replace source ornaments with palette-tinted, softly rounded accents."""
    for index in (6, 7, 8):
        root[index].set('display', 'none')
    group = ET.SubElement(root, q('g'), {
        'class': 'soft-decorations', 'clip-path': 'url(#f8616e7e2c)',
    })

    def flower(cls: str, x: float, y: float, scale: float, fill: str) -> None:
        anchor = ET.SubElement(group, q('g'), {'transform': f'translate({x} {y})'})
        spinner = ET.SubElement(anchor, q('g'), {'class': f'petal-spin {cls}'})
        ET.SubElement(spinner, q('path'), {
            'd': FLOWER_PATH, 'fill': fill, 'transform': f'scale({scale})',
        })

    def star(cls: str, x: float, y: float, scale: float, fill: str) -> None:
        anchor = ET.SubElement(group, q('g'), {'transform': f'translate({x} {y})'})
        spinner = ET.SubElement(anchor, q('g'), {'class': f'sparkle-spin {cls}'})
        ET.SubElement(spinner, q('path'), {
            'd': STAR_PATH, 'fill': fill, 'transform': f'scale({scale})',
        })

    flower('flower-upper-right', 543, 8, .16, palette['flower_top'])
    flower('flower-bottom-left', -20, 104, .22, palette['flower_bottom'])
    star('sparkle-upper-left', 31, 60, .52, palette['sparkle'])


def source_with_wrappers(palette: dict) -> ET.Element:
    root = ET.parse(SOURCE).getroot()
    for el in root.iter():
        fill = el.get('fill', '').lower()
        color_map = {
            '#474a64': palette['background'],
            '#e4e4e4': palette['ink'],
            '#b8bfff': palette['icon'],
        }
        if fill in color_map:
            el.set('fill', color_map[fill])
    # The label and pill backgrounds are raster artwork embedded in the source.
    for index in (2, 4):
        image_el = next((e for e in root[index].iter() if e.tag == q('image')), None)
        if image_el is not None:
            recolor_badge_image(image_el, palette)
    add_soft_shapes(root, palette)
    for start, end, cls in [(54, 73, 'subtitle-entry'), (52, 54, 'name-entry'),
                            (4, 6, 'builder-entry'), (2, 4, 'ph-entry')]:
        wrap_range(root, start, end, cls)
    return root


CSS = '''
<style type="text/css"><![CDATA[
  .name-entry, .subtitle-entry, .ph-entry, .builder-entry { transform-box: fill-box; transform-origin: center; }
  .name-entry { animation: enter-name 760ms cubic-bezier(.18,.72,.22,1) 120ms both, idle-name 6s ease-in-out 1s infinite alternate; }
  .subtitle-entry { animation: enter-soft 720ms cubic-bezier(.18,.72,.22,1) 280ms both, idle-subtitle 6s ease-in-out 1.2s infinite alternate; }
  .ph-entry { animation: enter-soft 680ms cubic-bezier(.18,.72,.22,1) 420ms both, idle-pill 6s ease-in-out 1.4s infinite alternate; }
  .builder-entry { animation: enter-soft 680ms cubic-bezier(.18,.72,.22,1) 540ms both, idle-pill 6s ease-in-out 1.7s infinite alternate; }
  .sparkle-spin, .petal-spin { transform-box: fill-box; transform-origin: center; }
  .flower-upper-right { animation: ornament-turn 52s linear infinite; }
  .flower-bottom-left { animation: ornament-turn 58s linear infinite reverse; }
  .sparkle-upper-left { animation: ornament-turn 42s linear infinite; }
  @keyframes ornament-turn { to { transform: rotate(360deg); } }
  @keyframes enter-name { 0% { opacity: 0; transform: translateY(5px) scale(.985); } 72% { opacity: 1; transform: translateY(-.4px) scale(1.002); } 100% { opacity: 1; transform: translateY(0) scale(1); } }
  @keyframes enter-soft { 0% { opacity: 0; transform: translateY(4px); } 100% { opacity: 1; transform: translateY(0); } }
  @keyframes idle-name { from { transform: translateY(0); } to { transform: translateY(-.55px); } }
  @keyframes idle-subtitle { from { transform: translateY(0); } to { transform: translateY(-.35px); } }
  @keyframes idle-pill { from { transform: translateY(0); } to { transform: translateY(-.65px); } }
  @media (prefers-reduced-motion: reduce) {
    .name-entry, .subtitle-entry, .ph-entry, .builder-entry { animation: none !important; opacity: 1; transform: none; }
    .sparkle-spin, .petal-spin { animation: none !important; transform: none; }
  }
]]></style>
'''


def build_variant(palette_id: str, palette: dict) -> None:
    outdir = ASSETS / 'palettes' / palette_id
    outdir.mkdir(parents=True, exist_ok=True)
    base_root = source_with_wrappers(palette)
    static_path = outdir / 'teejx-static.svg'
    static_path.write_text(ET.tostring(base_root, encoding='unicode') + '\n', encoding='utf-8')
    animated_root = copy.deepcopy(base_root)
    animated_root.insert(0, ET.fromstring(CSS))
    (outdir / 'teejx-animated.svg').write_text(ET.tostring(animated_root, encoding='unicode') + '\n', encoding='utf-8')

    # The README uses native animated SVGs; build one clean static preview per palette.
    legacy_gif = outdir / 'teejx-motion.gif'
    legacy_gif.unlink(missing_ok=True)
    preview_path = ROOT / f'preview-{palette_id}.png'
    subprocess.run(['rsvg-convert', '-w', '960', '-o', str(preview_path), str(static_path)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description='Build the teejx README with a switchable palette.')
    parser.add_argument('--palette', choices=('palette1', 'palette2', 'light', 'monochrome'),
                        help='set and activate a palette')
    parser.add_argument('--all-palettes', action='store_true',
                        help='build and preview all four saved palettes')
    args = parser.parse_args()
    palettes = json.loads(PALETTE_FILE.read_text(encoding='utf-8'))
    profile = json.loads(PROFILE_FILE.read_text(encoding='utf-8'))
    if args.palette:
        profile['active_palette'] = args.palette
        PROFILE_FILE.write_text(json.dumps(profile, indent=2) + '\n', encoding='utf-8')
    active = profile.get('active_palette', 'palette1')
    if active not in palettes:
        raise ValueError(f'Unknown active palette: {active}')
    build_ids = list(palettes) if args.all_palettes else [active]
    for palette_id in build_ids:
        build_variant(palette_id, palettes[palette_id])
        render_section_variant(palette_id, palettes[palette_id])

    # Keep the original simple paths usable while exposing semantic README paths.
    active_dir = ASSETS / 'palettes' / active
    for name in ('teejx-static.svg', 'teejx-animated.svg'):
        shutil.copyfile(active_dir / name, ASSETS / name)
    sections_dir = ASSETS / 'sections'
    sections_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(active_dir / 'teejx-animated.svg', sections_dir / 'hero.svg')
    shutil.copyfile(active_dir / 'teejx-static.svg', sections_dir / 'hero-static.svg')
    shutil.copyfile(ROOT / f'preview-{active}.png', ROOT / 'preview-teejx.png')
    activate_section_palette(active, palettes[active])

    # Keep the authored multi-card README intact and only refresh its palette note.
    readme_path = ROOT / 'README.md'
    readme_lines = readme_path.read_text(encoding='utf-8').splitlines()
    if readme_lines and readme_lines[0].startswith('<!-- Active banner palette:'):
        readme_lines[0] = f'<!-- Active banner palette: {active}. Switch with python3 tools/animate_teejx.py --palette {active}. -->'
        readme_path.write_text('\n'.join(readme_lines) + '\n', encoding='utf-8')
    print(f'Active palette: {active}. Built {", ".join(build_ids)}.')
    if args.all_palettes:
        print('Previews: preview-palette1.png, preview-palette2.png, preview-light.png, preview-monochrome.png')


if __name__ == '__main__':
    main()
