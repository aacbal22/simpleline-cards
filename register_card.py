# -*- coding: utf-8 -*-
"""
새 직원 명함 한 번에 등록: 템플릿 생성 → (정보 입력) → 빌드 + 배포 + 사진 업로드링크 발급

사용법:
    1) python register_card.py <slug>          # cards/<slug>.json 템플릿 생성(회사 공통값은 채워짐)
    2) (생성된 json 의 개인정보 — 이름/직함/부서/전화/이메일 — 를 채운다)
    3) python register_card.py <slug> --push    # 빌드 + 배포 + 업로드링크 발급

cards/<slug>.json 이 이미 있으면 1단계는 건너뛰고 바로 빌드 + 발급.
"""
import os, sys, glob, json, argparse, subprocess
import build_card as bc
import make_token as mt

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://aacbal22.github.io/simpleline-cards"


def make_template(slug):
    """kjh.json 을 기반으로 회사 공통값(회사명·주소·웹)은 유지하고 개인정보만 비운 템플릿 생성."""
    with open(os.path.join(ROOT, "cards", "kjh.json"), encoding="utf-8") as f:
        t = json.load(f)
    t["slug"] = slug
    t.pop("photo", None)
    t.pop("tagline", None)
    f_, b, v = t["front"], t["back"], t["vcard"]
    for k in ("name", "title", "dept", "email"):
        f_[k] = ""
    f_["phones"] = ["", ""]
    for k in ("name", "title", "email"):
        b[k] = ""
    b["phones"] = ["", ""]
    for k in ("last_name", "first_name", "full_name_kr", "title", "cell", "work_tel", "email"):
        v[k] = ""
    out = os.path.join(ROOT, "cards", f"{slug}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(t, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return out


def rebuild(base):
    bc.make_brand_icons()
    for j in sorted(glob.glob(os.path.join(ROOT, "cards", "*.json"))):
        bc.process(j, base)
    bc.build_index(base)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="직원 약자 (영문 소문자 권장)")
    ap.add_argument("--push", action="store_true", help="빌드 후 git 커밋·푸시까지")
    args = ap.parse_args()
    jp = os.path.join(ROOT, "cards", f"{args.slug}.json")

    # 1) 템플릿 생성 단계
    if not os.path.exists(jp):
        make_template(args.slug)
        print(f"\n[템플릿 생성] cards/{args.slug}.json")
        print("  회사 공통값(회사명·주소·웹)은 채워져 있습니다.")
        print("  → 이름·직함·부서·전화·이메일(앞면/뒷면/vcard)을 채운 뒤 다시 실행하세요:")
        print(f"     python register_card.py {args.slug} --push\n")
        return

    # 2) 빌드 + 배포 + 링크 발급 단계
    with open(jp, encoding="utf-8") as f:
        data = json.load(f)
    name = data["front"].get("name", "").strip()
    if not name:
        print(f"[중단] cards/{args.slug}.json 의 이름이 비어 있습니다. 정보를 먼저 채우세요.")
        return

    rebuild(BASE_URL)
    print(f"[빌드] {name}({args.slug}) 명함 + 갤러리 재생성 완료")

    if args.push:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-m", f"card: {name}({args.slug}) 명함 등록"], cwd=ROOT, check=True)
        subprocess.run(["git", "push"], cwd=ROOT, check=True)
        print("[배포] git push 완료 — 1~2분 내 반영")
    else:
        print("  (배포하려면 --push 를 붙여 다시 실행하거나, 직접 git push)")

    link = mt.issue_token(args.slug, name)
    print("\n" + "=" * 56)
    print(f"  {name}({args.slug}) 사진 업로드 링크")
    print("=" * 56)
    print(f"  {link}")
    print("=" * 56)
    print("  이 링크를 직원에게 카톡으로 보내면 본인이 폰에서 사진을 올립니다.\n")


if __name__ == "__main__":
    main()
