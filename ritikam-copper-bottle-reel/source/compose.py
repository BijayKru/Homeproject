import subprocess, sys, numpy as np
from PIL import Image

D = sys.argv[1]            # working dir with L_*.png
OUT = sys.argv[2]
U = '/root/.claude/uploads/aaa58fb8-ffff-5188-977f-fef18267f6c9/'
W, H, FPS, DUR = 1080, 1920, 30, 10.0
IMG_Y, IMG_S = 430, 1080
IVORY = np.array([0xF7, 0xF1, 0xE8], np.float32)

def eo(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3          # ease-out cubic
def eio(t): t = min(max(t, 0), 1); return t * t * (3 - 2 * t)       # smoothstep

# (image, start, end, zoom_from, zoom_to, focus_x, focus_y, text id)
SC = [
    ('997a3337', 0.0, 3.2, 1.00, 1.08, .52, .50, 1),   # water splash
    ('900ba5d1', 2.8, 6.2, 1.10, 1.02, .50, .46, 2),   # pouring from the jug
    ('a6b9ffc0', 5.8, 8.8, 1.00, 1.09, .54, .40, 3),   # closing the cap
]
src = {s[0]: Image.open(U + s[0] + '-image.jpg').convert('RGB') for s in SC}

def layer(name):
    a = np.asarray(Image.open(f'{D}/L_{name}.png').convert('RGBA'), np.float32) / 255.
    return a[..., :3] * 255., a[..., 3:4]
LY = {n: layer(n) for n in ['top1', 'top2', 'top3', 'bot1', 'bot2', 'bot3', 'wm', 'end']}

def over(base, rgb, a, alpha, dy=0):
    if alpha <= 0: return
    if dy:
        rgb = np.roll(rgb, dy, axis=0); a = np.roll(a, dy, axis=0)
    k = a * alpha
    base *= (1 - k); base += rgb * k

def kenburns(img, z, fx, fy):
    w, h = img.size
    cw, ch = w / z, h / z
    x0 = min(max(fx * w - cw / 2, 0), w - cw); y0 = min(max(fy * h - ch / 2, 0), h - ch)
    return img.resize((IMG_S, IMG_S), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))

ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
    '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
    '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)

N = int(DUR * FPS)
for f in range(N):
    t = f / FPS
    fr = np.empty((H, W, 3), np.float32); fr[:] = IVORY
    for (k, s, e, z0, z1, fx, fy, tid) in SC:
        if t < s or t > e + 0.5: continue
        p = (t - s) / (e - s + 0.5)
        a = 1.0 if s == 0 else eio((t - s) / 0.45)
        im = np.asarray(kenburns(src[k], z0 + (z1 - z0) * eio(p), fx, fy), np.float32)
        reg = fr[IMG_Y:IMG_Y + IMG_S]; reg *= (1 - a); reg += im * a
    for (k, s, e, z0, z1, fx, fy, tid) in SC:
        ts = s + (0.2 if s == 0 else 0.35)
        if t < ts or t > e: continue
        ain = eo((t - ts) / 0.55); aout = 1 - eio((t - (e - 0.35)) / 0.35)
        al = min(ain, aout)
        over(fr, *LY[f'top{tid}'], al, int(26 * (1 - eo((t - ts) / 0.7))))
        tb = ts + 0.25
        if t >= tb:
            over(fr, *LY[f'bot{tid}'], min(eo((t - tb) / 0.55), aout), int(18 * (1 - eo((t - tb) / 0.7))))
    over(fr, *LY['wm'], eo(t / 0.6))
    if t >= 8.45:                                # brand end card
        over(fr, *LY['end'], eio((t - 8.45) / 0.55))
    ff.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
ff.stdin.close(); ff.wait()
print('done', OUT)
