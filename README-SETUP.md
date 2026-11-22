# README assets and palette workflow

The profile README is built from local assets under `assets/sections/`. The README uses those paths directly, so keep the `assets/` folder alongside `README.md` when preparing a profile-repository upload.

## Asset layout

- `assets/sections/hero.svg` and `hero-static.svg` are the active animated and reduced-motion hero.
- `assets/sections/contact-links/` contains one SVG per contact button. Each image is wrapped in a real `<a href>` in `README.md`, so each button opens its own destination.
- `assets/sections/roles-card.svg`, `tech-stack-card.svg`, and `streak-stats-placeholder.svg` are the active rounded cards.
- `assets/palettes/<palette>/` stores the hero and matching card/button variants for `palette1`, `palette2`, `light`, and `monochrome`.
- `src/components/sections/` contains editable SVG templates. `tools/build_profile_sections.py` builds the palette-specific copies in `assets/`.

The tech-stack card groups the tools into five rounded panels, each with a title pill and compact skill pills. It shares the same soft card shadow, rounded geometry, palette tokens, and entrance glide as the other sections. The decorative star remains still, and the hero keeps its existing animation.

## Change the active palette

From the project root, run:

```bash
python3 tools/animate_teejx.py --palette palette1
python3 tools/animate_teejx.py --palette palette2
python3 tools/animate_teejx.py --palette light
python3 tools/animate_teejx.py --palette monochrome
```

The command updates the hero, cards, linked contact buttons, stats colors, local preview, and `github-upload/` staging folder together. `--all-palettes` builds all four variants while keeping the current active palette.

GitHub READMEs do not run React, JavaScript, or arbitrary CSS. GitHub sanitizes inline styles and scripts from README markup. This README uses supported HTML anchors for working links and SVG images for the custom button artwork.

## Credits

The rounded petal ornament is adapted from “Flower Star Rectangle 8 Round” in the [SVGBackgrounds geometric shape library](https://www.svgbackgrounds.com/elements/svg-shapes-geometric/).

Concert One is distributed under the SIL Open Font License. Its license is included at `assets/fonts/ConcertOne-OFL.txt`.

