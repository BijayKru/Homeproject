# Ritikam Copper Bottle: 10-second reel

**File:** `Ritikam_Copper_Bottle_Reel_1080x1920_10s.mp4`
1080 × 1920 (9:16) · 10.0 s · 30 fps · H.264 High, yuv420p, faststart · 4.8 MB · no audio track

Works as-is for Instagram Reels and Stories, YouTube Shorts, Facebook Reels, WhatsApp Status and Shopify video sections. Add music in-app.

## Script

| Time | Visual | Small heading (Afacad, Copper) | Headline (Playfair Display) | Supporting line (Afacad) |
|---|---|---|---|---|
| 0.0–3.2 s | Water splashing around the bottle, slow push-in | PURE COPPER | Water, the way *tradition* intended. | Handcrafted copper, made for the modern home. |
| 2.8–6.2 s | Crossfade: pouring from the hammered jug, slow pull-out | THE DAILY RITUAL | Fill it the *night before.* | An age-old Indian ritual, made beautiful again. |
| 5.8–8.8 s | Crossfade: closing the cap, push-in towards the hand | MADE TO CARRY | Sip *slow*, all day long. | Brushed copper body · hand-hammered base |
| 8.5–10 s | Heritage Brown end card | — | **RITIKAM** | *Copper, brass & bronze — warm heritage for the home.* · SHOP NOW · RITHIKAM.COM |

A small RITIKAM wordmark stays at the bottom throughout.

### Optional voice-over (about 9 s at a calm pace)
> Water, the way tradition intended.
> Fill it the night before…
> …and sip slow, all day long.
> Ritikam. Warm heritage for the home.

### Suggested caption
Some rituals are worth keeping. 🫗 Fill your Ritikam copper bottle the night before, and carry a little tradition through your day.
Shop now at rithikam.com
#Ritikam #CopperBottle #TamraJal #CopperWaterBottle #HandcraftedInIndia #MindfulLiving

## Design
- Brand palette: Warm Ivory `#F7F1E8` frame, Heritage Brown `#5F3916` headlines, Rich Copper `#B5652A` accents, Peach Gold `#F1A56C` on the end card.
- Typography: Playfair Display 500 and Italic for headlines and the wordmark; Afacad 400 and 600 for the small headings, supporting lines and button.
- The photos are shown at their natural colours (no grading). The square photos fill the middle 1080 × 1080 area with an ivory band above and below. Text stays inside the 9:16 safe areas: nothing important sits in the top ~250 px or bottom ~300 px that the Instagram interface covers, apart from the small wordmark.

## Re-render
```bash
cd source
node layers.js                      # renders the text layers L_*.png (Playwright)
python3 compose.py . ../reel.mp4    # Ken Burns motion, crossfades and text, piped into ffmpeg
```
Copy lives in the `S` object in `text.html`; timings live in `SC` in `compose.py`. The source photos are read from the upload paths set in `compose.py` (the `U` variable); change it to your own folder.
