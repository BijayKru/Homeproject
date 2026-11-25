"""Bend the boy's rope arm at the elbow: forearm stays across his chest (nothing to repaint),
wrist+fist rotate upward and grip the real Ritikam bottle next to his face."""
import sys, math, numpy as np, cv2
from PIL import Image

C = sys.argv[1]
ROT = float(sys.argv[2])            # rotation of the hand segment (deg, image coords, +=clockwise on screen)
MIRROR = int(sys.argv[3])           # mirror the hand segment first
BOT_H = float(sys.argv[4])
BOT_TILT = float(sys.argv[5])
JX = float(sys.argv[6]) if len(sys.argv) > 6 else 968.0

T = np.array(Image.open(C + 'trio.png').convert('RGBA'))
H, W = T.shape[:2]
yy, xx = np.mgrid[0:H, 0:W]

arm_poly = np.array([(1052, 893), (1000, 903), (960, 906), (934, 910), (912, 919), (886, 917),
                     (878, 926), (884, 941), (905, 948), (935, 946), (962, 942), (1000, 939), (1052, 932)], np.int32)
arm_m = np.zeros((H, W), np.uint8); cv2.fillPoly(arm_m, [arm_poly], 255)
arm_m = cv2.dilate(arm_m, np.ones((3, 3), np.uint8)) > 0

J = (JX, 926.0)                                       # elbow joint on the forearm's centre line
hand_m = arm_m & (xx < J[0] + 10)                     # wrist + fist (+ overlap for the joint)
# soft joint: feather the segment's right end
fe = np.clip((J[0] + 10 - xx) / 10.0, 0, 1)

hand = T.copy().astype(np.float32)
hand[..., 3] = np.where(hand_m, T[..., 3] * fe, 0)
hsv = cv2.cvtColor(T[..., :3], cv2.COLOR_RGB2HSV)
rope = (hsv[..., 0] >= 10) & (hsv[..., 0] <= 22) & (hsv[..., 1] > 110) & (xx < 893)
hand[rope, 3] = 0
hand = hand.astype(np.uint8)

# figure without the hand segment (left of the joint the arm vanishes -> background / the other hand stays)
base = T.copy()
base[arm_m & (xx < J[0]), 3] = 0

# transform the hand segment about the joint
M = np.eye(3)
if MIRROR:
    M = np.array([[1, 0, 0], [0, -1, 2 * J[1]], [0, 0, 1]], float) @ M   # flip across the forearm axis
c, s = math.cos(math.radians(ROT)), math.sin(math.radians(ROT))
R = np.array([[c, -s, J[0] - c * J[0] + s * J[1]], [s, c, J[1] - s * J[0] - c * J[1]], [0, 0, 1]], float)
M = (R @ M)[:2]
hand2 = cv2.warpAffine(hand, M, (W, H), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0, 0))
fist0 = np.array([903.0, 930.0, 1.0]); fist = M @ fist0

# bottle through the fist
B = Image.open(C + 'bottle.png').convert('RGBA')
bw = BOT_H * B.width / B.height
B = B.resize((round(bw), round(BOT_H)), Image.LANCZOS).rotate(-BOT_TILT, expand=True, resample=Image.BICUBIC)
Bn = np.array(B)
t = math.radians(BOT_TILT); d = (0.62 - 0.5) * BOT_H
cx = fist[0] - d * math.sin(t); cy = fist[1] - d * math.cos(t)
bx, by = int(round(cx - Bn.shape[1] / 2)), int(round(cy - Bn.shape[0] / 2))

def comp(dst, src, x, y):
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    s_ = src[y0 - y:y1 - y, x0 - x:x1 - x].astype(float); a = s_[..., 3:4] / 255.
    d_ = dst[y0:y1, x0:x1].astype(float); da = d_[..., 3:4] / 255.
    oa = a + da * (1 - a)
    rgb = (s_[..., :3] * a + d_[..., :3] * da * (1 - a)) / np.maximum(oa, 1e-6)
    dst[y0:y1, x0:x1, :3] = np.clip(rgb, 0, 255).astype(np.uint8); dst[y0:y1, x0:x1, 3:4] = (oa * 255).astype(np.uint8)

out = base.copy()
comp(out, Bn, bx, by)
comp(out, hand2, 0, 0)
Image.fromarray(out).save(C + 'trio_bottle.png')
open(C + 'bottle_pos.txt', 'w').write(f'{cx} {cy} {bw} {BOT_H} {BOT_TILT}')
print('fist', fist.round(1), 'bottle centre', round(cx), round(cy))
crop = Image.fromarray(out).crop((800, 620, 1200, 1000))
bg = Image.new('RGBA', crop.size, (247, 236, 224, 255)); bg.alpha_composite(crop)
bg.resize((crop.width * 2, crop.height * 2), Image.LANCZOS).save(C + 'arm_check.png')
