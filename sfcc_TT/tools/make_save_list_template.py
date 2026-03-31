from pathlib import Path

import cv2

BASE_DIR = Path(__file__).resolve().parents[1]
SRC = BASE_DIR / "runtime" / "logs" / "debug" / "20260320_151327" / "20260320_151427_434409_save_list_back_last_capture.png"
DST = BASE_DIR / "assets" / "templates" / "template_save_list_title.png"

img = cv2.imread(str(SRC))
if img is None:
    raise SystemExit(f"missing source image: {SRC}")

crop = img[10:72, 60:300]
DST.parent.mkdir(parents=True, exist_ok=True)
if not cv2.imwrite(str(DST), crop):
    raise SystemExit(f"failed to write template: {DST}")

print(crop.shape)
