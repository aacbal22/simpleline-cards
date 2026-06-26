# -*- coding: utf-8 -*-
"""
명함 프로필 사진 자동 등록 헬퍼 (공용)

직원이 사진만 보내주면, 사진 파일 하나로
  ① 정사각(얼굴 중심) 크롭 → docs/assets/<slug>.jpg
  ② cards/<slug>.json 에 "photo" 필드 자동 추가/갱신
  ③ 전체 명함 + 갤러리 재생성
까지 한 번에 끝낸다. (git push 는 확인 후 별도로 — 또는 --push)

사용법:
    python add_photo.py <slug> <사진파일경로>
    예) python add_photo.py cem "C:/Users/user/Downloads/채은미.jpg"
        python add_photo.py cem "C:/Users/user/Downloads/채은미.jpg" --push

전제: cards/<slug>.json 명함이 이미 있어야 함(새 직원은 명함부터 생성).
"""
import os, sys, json, glob, argparse, subprocess
from PIL import Image, ImageOps

import build_card as bc

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://aacbal22.github.io/simpleline-cards"


def crop_square(img_path, out_path, size=512, center_y=0.38):
    """폰 사진 회전 보정 후, 얼굴이 보통 상단~중앙인 점을 감안해
    살짝 위쪽 비중(center_y=0.38)으로 정사각 크롭 + 리사이즈."""
    im = ImageOps.exif_transpose(Image.open(img_path).convert("RGB"))
    sq = ImageOps.fit(im, (size, size), method=Image.LANCZOS, centering=(0.5, center_y))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sq.save(out_path, "JPEG", quality=88)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="직원 약자 (cards/<slug>.json 과 일치)")
    ap.add_argument("image", help="원본 사진 파일 경로")
    ap.add_argument("--base-url", default=BASE_URL)
    ap.add_argument("--center-y", type=float, default=0.38,
                    help="세로 크롭 기준(작을수록 위쪽 더 포함, 기본 0.38)")
    ap.add_argument("--push", action="store_true", help="재생성 후 git add/commit/push 까지")
    args = ap.parse_args()

    jp = os.path.join(ROOT, "cards", f"{args.slug}.json")
    if not os.path.exists(jp):
        print(f"[ERR] cards/{args.slug}.json 가 없습니다 — 명함을 먼저 만들어야 합니다.")
        sys.exit(1)
    if not os.path.exists(args.image):
        print(f"[ERR] 사진 파일을 찾을 수 없습니다: {args.image}")
        sys.exit(1)

    # ① 크롭
    out_img = os.path.join(ROOT, "docs", "assets", f"{args.slug}.jpg")
    crop_square(args.image, out_img, center_y=args.center_y)
    print(f"[1/3] 크롭 완료 → docs/assets/{args.slug}.jpg (512x512)")

    # ② JSON 갱신
    with open(jp, encoding="utf-8") as f:
        data = json.load(f)
    data["photo"] = f"{args.slug}.jpg"
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"[2/3] cards/{args.slug}.json 에 photo 추가")

    # ③ 전체 재생성
    base = args.base_url.rstrip("/")
    bc.make_brand_icons()
    for j in sorted(glob.glob(os.path.join(ROOT, "cards", "*.json"))):
        bc.process(j, base)
    bc.build_index(base)
    print("[3/3] 명함 + 갤러리 재생성 완료")

    if args.push:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-m", f"card: {args.slug} 프로필 사진 추가"], cwd=ROOT, check=True)
        subprocess.run(["git", "push"], cwd=ROOT, check=True)
        print("[PUSH] 배포 완료 — 1~2분 내 반영")
    else:
        print("\n다음으로 배포하려면:  git add -A && git commit -m \"...\" && git push")


if __name__ == "__main__":
    main()
