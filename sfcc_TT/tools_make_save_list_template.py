import cv2

SRC = r"E:\sfcc_TT\logs\debug_20260320_151327\20260320_151427_434409_save_list_back_last_capture.png"
DST = r"E:\sfcc_TT\template_save_list_title.png"

img = cv2.imread(SRC)
if img is None:
    raise SystemExit(f"missing source image: {SRC}")

crop = img[10:72, 60:300]
if not cv2.imwrite(DST, crop):
    raise SystemExit(f"failed to write template: {DST}")

print(crop.shape)
