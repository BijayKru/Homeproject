# Ritikam — Dhanteras & Diwali Shopify Hero Banners

Two festive campaigns built to the Ritikam brand guidelines:

| | |
|---|---|
| **Palette** | Deep Heritage Brown `#5F3916` · Rich Copper `#B5652A` · Warm Ivory `#F7F1E8` · Soft Peach Gold `#F1A56C` (limited accent) |
| **Display type** | Playfair Display 500 (+ 500 Italic for the accent word) |
| **Supporting type** | Afacad 400 (body), 600 (eyebrow and CTA, tracked +0.22–0.34em, uppercase) |
| **Mood** | Thoughtful · elegant · royal. Ivory breathing space, copper/brass as hero, restrained ornament (mandala line-work at 9–16% opacity, a single arch frame, a thin rule-and-diamond divider) |

## Files

| File | Size (px) | Ratio | Weight | Use |
|---|---|---|---|---|
| `Ritikam_Dhanteras_Hero_Desktop_2880x1200.jpg` | 2880 × 1200 | 12:5 | ~310 KB | Desktop hero, text baked in |
| `Ritikam_Dhanteras_Hero_Mobile_1080x1350.jpg` | 1080 × 1350 | 4:5 | ~185 KB | Mobile hero, text baked in |
| `Ritikam_Diwali_Hero_Desktop_2880x1200.jpg` | 2880 × 1200 | 12:5 | ~245 KB | Desktop hero, text baked in |
| `Ritikam_Diwali_Hero_Mobile_1080x1350.jpg` | 1080 × 1350 | 4:5 | ~140 KB | Mobile hero, text baked in |
| `…_NoText.jpg` (×4) | same | same | lighter | Artwork only, for adding the copy as live Shopify text (recommended, see below) |

All images are exported as sRGB progressive JPEGs at quality 86. Each is well under Shopify's 20 MB / 5000 × 5000 px upload limit and under the ~500 KB target for a fast homepage LCP. Desktop images are 2× retina: the design canvas is 1440 × 600, rendered at 2880 × 1200.

## Shopify setup (Dawn and other Online Store 2.0 themes)

1. **Online Store → Themes → Customize → Home page → Add section → Image banner** (or edit the existing one).
2. **Image:** upload the desktop file. In themes that have a separate **Mobile image** field (Dawn's *Slideshow*, Sense, Craft, Prestige, Impulse, etc.), upload the matching `Mobile_1080x1350` file there.
3. **Banner height:** choose **"Adapt to first image"**. Fixed Small/Medium/Large heights crop the artwork with `object-fit: cover`.
4. **Pick one of these two options:**
   - **A: Baked-in text** (pixel-perfect). Use the files *with* text, delete the section's Heading, Text and Button blocks, and link the whole banner to the collection.
   - **B: Live text (recommended for SEO and accessibility).** Use the `_NoText` files and add the copy as blocks:
     - Desktop content position: **Middle left**. Mobile: **Top center** (the artwork leaves the top ~45% empty for it).
     - Show container on desktop: **off**. Colour scheme: Ivory background with Brown text (Dhanteras), or Brown background with Ivory text (Diwali).
     - Heading size: **Large**. In *Theme settings → Typography*, set Headings to **Playfair Display** and Body to **Afacad**. Both fonts are in Shopify's font library (Google Fonts).
5. **Button link:** `/collections/dhanteras` or `/collections/diwali` (or your equivalent collection handles).
6. **Image overlay opacity:** 0%. The artwork is already balanced for contrast.

### Safe zones (if your theme crops)
- **Desktop (2880 × 1200):** text sits at x 224–1350 px. The product still-life sits at x 1590–2700 px. Keep at least 120 px from the left and right edges clear. All key content stays inside the central 2640 × 1100 px.
- **Mobile (1080 × 1350):** copy is in the top 0–620 px and products in the bottom 680–1350 px. Side gutters are 60 px or more.

## Copy

| | Dhanteras | Diwali |
|---|---|---|
| Eyebrow | THE DHANTERAS EDIT | THE DIWALI EDIT |
| Headline | Bring home the auspicious *glow* of copper | Light up every *gathering* |
| Sub-line | Handcrafted copper, brass & bronze — heirlooms to welcome prosperity this Dhanteras. | Diyas, thalis & serveware in copper, brass & bronze — made for hosting the ones you love. |
| CTA | Shop the Dhanteras Edit → | Shop the Diwali Edit → |
| Alt text | Handcrafted copper kalash with mango leaves and coconut, copper lota, brass tumbler, brass coins and diyas framed in a heritage arch — Ritikam Dhanteras Edit | Brass thali of lit diyas between a copper lota and tumbler, with hanging brass lamps and marigold petals — Ritikam Diwali Edit |

**Scheduling (2026):** Dhanteras falls on Fri 6 Nov and Lakshmi Puja / Diwali on Sun 8 Nov. Swap the Dhanteras banner for the Diwali banner on the evening of 6 Nov. Dates are deliberately left out of the artwork so each banner can run for the full campaign window.

## Editing / re-rendering

`source/banner.html` builds each banner from vector illustration and live type. Parameters: `?v=dhanteras|diwali&l=desktop|mobile&t=1|0`. The copy lives in the `COPY` object, so you can change a headline or add an offer line there.

```bash
cd source && node render.js out   # needs Playwright + Chromium; writes all 8 PNGs
```

> **Photography note:** the guidelines prefer real product-in-use photography. These illustrated still-lifes are styled on Ritikam's category (hammered copper, brass). For the strongest result, keep this layout and type but replace the right-hand artwork with a lifestyle photo of your actual products in the same warm, low-key lighting.
