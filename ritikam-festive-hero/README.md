# Ritikam — Dhanteras & Diwali Hero Banner

**File:** `Ritikam_Dhanteras_Diwali_Hero_2880x1200.jpg`

| Spec | Value |
|---|---|
| Dimensions | **2880 × 1200 px** (12:5). 2× retina of a 1440 × 600 design |
| Format | JPEG, sRGB, progressive, quality 86 |
| File size | ~455 KB (Shopify limit is 20 MB / 5000 × 5000 px; keeping it under 500 KB helps homepage speed) |
| Products | Real Ritikam photography, cut out with AI background removal. Metal colour is **not** retouched. Hammered copper water dispenser with lid, copper bottle and hammered tumbler, hammered copper jug with brass handle, bronze (kansa) thali set |
| Palette | Heritage Brown `#5F3916` set · Ivory `#F7F1E8` headline and button · Peach Gold `#F1A56C` accents · Copper glow |
| Type | Playfair Display 500 (headline, italic accent) · Afacad 400/600 (eyebrow, body, CTA) |

**Copy on the banner**
- Eyebrow: DHANTERAS & DIWALI EDIT
- Headline: An auspicious beginning, in *pure copper*
- Sub-line: Handcrafted copper, brass & bronze — for an auspicious Dhanteras and a Diwali full of gatherings.
- Button: SHOP THE FESTIVE EDIT →

## Upload to Shopify
1. **Online Store → Themes → Customize → Home page → Image banner** (add the section if it isn't there).
2. **Image:** upload `Ritikam_Dhanteras_Diwali_Hero_2880x1200.jpg`.
3. **Banner height:** **Adapt to first image**, so nothing is cropped.
4. Image overlay opacity: **0%**. Delete the section's Heading, Text and Button blocks, because the text is already in the image.
5. Link the banner (or a single button) to your festive collection, e.g. `/collections/festive-edit`.
6. **Alt text:** *Ritikam handcrafted copper water dispenser, copper bottle and tumbler, hammered copper jug and bronze thali set with lit brass diyas — Dhanteras & Diwali Edit.*

Safe zone: the text sits at x 224–1120 px and the products at x 1210–2780 px of the 2880 px width. If a theme crops the sides, keep at least 100 px clear at each edge.

## Editing
`source/hero.html` holds the layout (real product cut-outs are in `source/img/`, fonts in `source/fonts/`). Edit the copy in the `.txt` block, then run `node render.js` (Playwright) to re-export. `?t=0` renders the image without text.
