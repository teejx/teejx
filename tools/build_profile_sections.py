#!/usr/bin/env python3
"""Build palette-specific README cards and linked badges from source SVG templates."""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'src/components/sections'
ASSETS = ROOT / 'assets'
PALETTE_FILE = ROOT / 'src/themes/teejx-palettes.json'
PROFILE_FILE = ROOT / 'profile.json'
SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG)

def q(tag: str) -> str:
    return f'{{{SVG}}}{tag}'


def recolor(root: ET.Element, palette: dict) -> None:
    roles = {
        'panel-bg': ('fill', palette['card']),
        'panel-bg-alt': ('fill', palette['card_alt']),
        'button-bg': ('fill', palette['button']),
        'button-label': ('fill', palette['button_ink']),
        'separator': ('fill', palette['icon']),
        'button-ink': ('fill', palette['button_ink']),
        'button-icon-bg': ('fill', palette['button_icon']),
        'button-icon-ink': ('fill', palette['button_icon_ink']),
        'category-pills': ('fill', palette['button']),
        'category-labels': ('fill', palette['button_ink']),
        'tech-pills': ('fill', palette['tech']),
        'tech-labels': ('fill', palette['tech_ink']),
        'stat-number': ('fill', palette['button_ink']),
        'stat-label': ('fill', palette['muted']),
        'stat-ring': ('stroke', palette['icon']),
        'divider': ('stroke', palette['line']),
        'ornament-fill': ('fill', palette['sparkle']),
        'shadow-color': ('flood-color', palette['shadow']),
    }
    for element in root.iter():
        for cls in element.attrib.get('class', '').split():
            if cls in roles:
                attr, value = roles[cls]
                if cls in {'button-ink', 'button-icon-ink'} and element.attrib.get('fill') == 'none' and 'stroke' in element.attrib:
                    element.set('stroke', value)
                else:
                    element.set(attr, value)
                # Category and skill groups inherit their pill fill and text colors.
                if cls in {'category-pills','category-labels','tech-pills','tech-labels'}:
                    element.set('fill', value)


def render_variant(palette_id: str, palette: dict) -> Path:
    """Build cards/buttons into the palette asset directory and return its folder."""
    out = ASSETS / 'palettes' / palette_id / 'sections'
    (out / 'contact-links').mkdir(parents=True, exist_ok=True)
    for name in ('roles-card.svg','tech-stack-card.svg','streak-stats-placeholder.svg'):
        root = ET.parse(TEMPLATES / name).getroot()
        recolor(root, palette)
        (out / name).write_text(ET.tostring(root, encoding='unicode') + '\n', encoding='utf-8')
    for path in sorted((TEMPLATES / 'contact-links').glob('*.svg')):
        root = ET.parse(path).getroot()
        recolor(root, palette)
        (out / 'contact-links' / path.name).write_text(ET.tostring(root, encoding='unicode') + '\n', encoding='utf-8')
    return out


def update_streak_url(text: str, palette: dict) -> str:
    colors = {
        'background': palette['card'], 'ring': palette['icon'], 'fire': palette['sparkle'],
        'currStreakLabel': palette['button_ink'], 'sideLabels': palette['muted'],
        'dates': palette['muted'], 'currStreakNum': palette['button_ink'],
        'sideNums': palette['button_ink'], 'stroke': palette['line'],
    }
    for key, value in colors.items():
        text = re.sub(r'([?&](?:amp;)?' + re.escape(key) + r'=)[0-9A-Fa-f]{6}', lambda m: m.group(1) + value.lstrip('#'), text)
    # The profile views counter uses Komarev's `color` parameter; keep it in palette sync.
    text = re.sub(r'([?&](?:amp;)?color=)[0-9A-Fa-f]{6}',
                  lambda m: m.group(1) + palette.get('profile_views', palette['button']).lstrip('#'), text)
    return text


def activate(palette_id: str, palette: dict) -> None:
    variant = ASSETS / 'palettes' / palette_id / 'sections'
    sections = ASSETS / 'sections'
    for name in ('roles-card.svg','tech-stack-card.svg','streak-stats-placeholder.svg'):
        shutil.copyfile(variant / name, sections / name)
    links = sections / 'contact-links'
    links.mkdir(parents=True, exist_ok=True)
    for path in (variant / 'contact-links').glob('*.svg'):
        shutil.copyfile(path, links / path.name)
    for name in ('README.md','README-preview.md','README-preview.html'):
        p = ROOT / name
        if p.exists(): p.write_text(update_streak_url(p.read_text(encoding='utf-8'),palette), encoding='utf-8')
    # Match the local preview canvas to the active palette and rerender its image.
    preview_svg = ROOT / 'README-preview.svg'
    if preview_svg.exists():
        root=ET.parse(preview_svg).getroot()
        for element in root.iter(q('rect')):
            if element.attrib.get('x') is None and element.attrib.get('width')=='900':
                element.set('fill', palette['page_bg'])
        for element in root.iter(q('rect')):
            classes = element.attrib.get('class', '').split()
            if 'profile-views-fill' in classes:
                element.set('fill', palette.get('profile_views', palette['button']))
            elif 'profile-views-label' in classes:
                element.set('fill', palette['card'])
        ET.ElementTree(root).write(preview_svg, encoding='unicode', xml_declaration=False)
        if shutil.which('rsvg-convert'):
            fontconf=Path('/tmp/teejx-profile-fonts.conf')
            fontconf.write_text(f'''<?xml version=\"1.0\"?>\n<!DOCTYPE fontconfig SYSTEM \"urn:fontconfig:fonts.dtd\">\n<fontconfig><dir>{ASSETS / 'fonts'}</dir><cachedir>/tmp/teejx-profile-font-cache</cachedir></fontconfig>\n''',encoding='utf-8')
            env=os.environ.copy(); env['FONTCONFIG_FILE']=str(fontconf)
            subprocess.run(['rsvg-convert','-o',str(ROOT/'README-preview.png'),str(preview_svg)],check=True,env=env)
    preview_html=ROOT/'README-preview.html'
    if preview_html.exists():
        html=preview_html.read_text(encoding='utf-8')
        html=re.sub(r'--bg:#[0-9A-Fa-f]{6}',f"--bg:{palette['page_bg']}",html)
        html=html.replace('color-scheme:dark;', 'color-scheme:light;' if palette_id=='light' else 'color-scheme:dark;')
        preview_html.write_text(html,encoding='utf-8')
    # Keep the local README copy and the future-upload staging copy on the active palette.
    for name in ('README.md','README-preview.md'):
        p=ROOT/name
        if p.exists():
            lines=p.read_text(encoding='utf-8').splitlines()
            if lines and lines[0].startswith('<!-- Active banner palette:'):
                lines[0]=f'<!-- Active banner palette: {palette_id}. Switch with python3 tools/animate_teejx.py --palette {palette_id}. -->'
                p.write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main() -> None:
    parser=argparse.ArgumentParser(description='Build all README card and button palette variants.')
    parser.add_argument('--palette', choices=('palette1','palette2','light','monochrome'))
    parser.add_argument('--all-palettes', action='store_true')
    args=parser.parse_args()
    palettes=json.loads(PALETTE_FILE.read_text(encoding='utf-8'))
    profile=json.loads(PROFILE_FILE.read_text(encoding='utf-8'))
    ids=list(palettes) if args.all_palettes else [args.palette or profile.get('active_palette','palette1')]
    for pid in ids: render_variant(pid,palettes[pid])
    active=args.palette or profile.get('active_palette','palette1')
    if args.palette:
        profile['active_palette']=active
        PROFILE_FILE.write_text(json.dumps(profile,indent=2)+'\n',encoding='utf-8')
    activate(active,palettes[active])

if __name__=='__main__': main()
