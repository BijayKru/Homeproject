"""Dad raises the real Ritikam bottle (pose from the user's reference).
- removes his upper rope forearm (only background behind it)
- bends that forearm up at the elbow
- grafts the reference hand (fingers + thumb) at the wrist, wrapped around the real bottle"""
import sys, math, numpy as np, cv2
from PIL import Image

C = sys.argv[1]
REF = '/root/.claude/uploads/aaa58fb8-ffff-5188-977f-fef18267f6c9/57d30e3d-image.png'
ROT = float(sys.argv[2]) if len(sys.argv) > 2 else 85.0      # forearm rotation about the elbow
K = float(sys.argv[3]) if len(sys.argv) > 3 else 1.15        # reference -> source scale
BW = float(sys.argv[4]) if len(sys.argv) > 4 else 50.0       # bottle width in reference px
TILT = float(sys.argv[5]) if len(sys.argv) > 5 else 15.0     # bottle lean (top to the right)
BC = (float(sys.argv[7]) if len(sys.argv) > 7 else 87.0, float(sys.argv[6]) if len(sys.argv) > 6 else 525.0)  # bottle centre in reference px

T = np.array(Image.open(C + 'trio.png').convert('RGBA'))
H, W = T.shape[:2]; yy, xx = np.mgrid[0:H, 0:W]

def poly(pts, shape):
    m = np.zeros(shape, np.uint8); cv2.fillPoly(m, [np.array(pts, np.int32)], 255); return m > 0

# 1) dad's upper forearm + the fingertips of that hand on the rope
up = poly([(499, 832), (470, 837), (440, 845), (410, 852), (380, 859), (352, 863), (345, 870),
           (352, 876), (380, 876), (415, 874), (440, 876), (470, 872), (499, 869)], (H, W))
up = cv2.dilate(up.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
J = (488.0, 853.0)                                            # elbow, just inside the rolled cuff
fore = up & (xx > 398) & (xx < 497) & (yy < 873)                          # forearm only (no hand), runs into the cuff
piece = T.copy().astype(np.float32)
fe = np.clip((xx - 398) / 6.0, 0, 1)
piece[..., 3] = np.where(fore, T[..., 3] * fe, 0); piece = piece.astype(np.uint8)
base = T.copy(); base[up & (xx < 474), 3] = 0     # keep a short stub: the elbow

c, s = math.cos(math.radians(ROT)), math.sin(math.radians(ROT))
R = np.array([[c, -s, J[0] - c * J[0] + s * J[1]], [s, c, J[1] - s * J[0] - c * J[1]]], float)
fore2 = cv2.warpAffine(piece, R, (W, H), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0, 0))
wrist = R @ np.array([404.0, 857.0, 1.0])                      # far end of the forearm after the bend

# 2) hand from the reference: fingers + thumb (ref coords), drawn over the real bottle
ref = np.array(Image.open(REF).convert('RGB'))
rh, rw = ref.shape[:2]
fingers = [(54, 515), (63, 513), (71, 519), (73, 535), (71, 560), (69, 585), (61, 589), (48, 587),
           (42, 576), (43, 560), (45, 545), (47, 530)]
thumb = [(101, 535), (109, 530), (116, 533), (118, 543), (113, 552), (104, 554), (99, 546)]
palm = [(58, 584), (70, 588), (96, 588), (97, 596), (66, 597), (59, 592)]
hm = (poly(fingers, (rh, rw)) | poly(thumb, (rh, rw))).astype(np.float32)
hm = cv2.GaussianBlur(hm, (0, 0), 0.8)
# clean the white halo the reference has around the hand: drop near-background pixels
bgd = np.abs(ref.astype(int) - np.array([248, 236, 224])).sum(2) < 40
hm[bgd] = 0
rr, gg, bb = ref[..., 0].astype(int), ref[..., 1].astype(int), ref[..., 2].astype(int)
maroon = (rr < 150) & (rr - gg > 35) & (gg < 90) & (np.mgrid[0:rh, 0:rw][1] > 96)
hm[maroon] = 0
handA = np.dstack([ref, (hm * 255).astype(np.uint8)])

# assemble hand + bottle on a working canvas in reference coordinates, then map to source
CW, CH = 220, 330; ox, oy = -10, 360                          # canvas covers ref x -10..210, y 360..690
canvas = np.zeros((CH, CW, 4), np.uint8)
def comp(dst, src, x, y):
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x1 <= x0 or y1 <= y0: return
    s_ = src[y0 - y:y1 - y, x0 - x:x1 - x].astype(float); a = s_[..., 3:4] / 255.
    d_ = dst[y0:y1, x0:x1].astype(float); da = d_[..., 3:4] / 255.
    oa = a + da * (1 - a)
    rgb = (s_[..., :3] * a + d_[..., :3] * da * (1 - a)) / np.maximum(oa, 1e-6)
    dst[y0:y1, x0:x1, :3] = np.clip(rgb, 0, 255).astype(np.uint8); dst[y0:y1, x0:x1, 3:4] = (oa * 255).astype(np.uint8)

Bt = Image.open(C + 'bottle.png').convert('RGBA')
bl = BW * Bt.height / Bt.width
Bt = Bt.resize((round(BW * 2), round(bl * 2)), Image.LANCZOS).rotate(-TILT, expand=True, resample=Image.BICUBIC)
Bt = Bt.resize((Bt.width // 2, Bt.height // 2), Image.LANCZOS)
Bn = np.array(Bt)
comp(canvas, Bn, int(round(BC[0] - ox - Bn.shape[1] / 2)), int(round(BC[1] - oy - Bn.shape[0] / 2)))
comp(canvas, handA[oy:oy + CH, max(ox, 0):ox + CW] if ox >= 0 else np.pad(handA, ((0, 0), (-ox, 0), (0, 0)))[oy:oy + CH, 0:CW], 0, 0)

# map canvas to source: reference wrist point (84, 596) lands on our forearm's end; slight lean to match the forearm
wr_ref = np.array([84.0 - ox, float(sys.argv[8]) - oy if len(sys.argv) > 8 else 596.0 - oy])
lean = -(ROT - 85.0) - 4.0
cl, sl = math.cos(math.radians(lean)), math.sin(math.radians(lean))
A = np.array([[K * cl, -K * sl, 0], [K * sl, K * cl, 0]], float)
A[:, 2] = wrist - A[:, :2] @ wr_ref
handbottle = cv2.warpAffine(canvas, A, (W, H), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0, 0))

out = base.copy()
comp(out, fore2, 0, 0)
# put the original rolled cuff back over the forearm's root
cb = np.zeros_like(T); bx_ = (xx >= 478) & (xx <= 520) & (yy >= 822) & (yy <= 884)
mr = (T[..., 0].astype(int) - T[..., 1].astype(int) > 40) & (T[..., 0] < 170) & (T[..., 3] > 200)
cb[bx_ & mr] = T[bx_ & mr]
comp(out, cb, 0, 0)
comp(out, handbottle, 0, 0)
Image.fromarray(out).save(C + 'trio_bottle.png')
bc = A @ np.array([BC[0] - ox, BC[1] - oy, 1.0])
top = A @ np.array([BC[0] - ox, BC[1] - oy - bl / 2, 1.0])
print('wrist', wrist.round(1), 'bottle centre', bc.round(1), 'bottle top y', round(top[1], 1))
crop = Image.fromarray(out).crop((300, 520, 760, 1000))
bg = Image.new('RGBA', crop.size, (247, 236, 224, 255)); bg.alpha_composite(crop)
bg.resize((crop.width * 2, crop.height * 2), Image.LANCZOS).save(C + 'arm_check.png')
