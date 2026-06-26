# -*- coding: utf-8 -*-
"""
직원 명함 사진 '셀프 업로드' 개인 링크 발급기

slug 하나로 고유 토큰을 만들어 Cloudflare KV(CARD_SELF)에 저장하고,
직원에게 카톡으로 보낼 업로드 링크를 출력한다.
토큰은 public 저장소(cards/*.json, git)에 절대 남기지 않는다 — KV에만 존재.

사용법:
    python make_token.py <slug>
    예) python make_token.py cem

전제: cards/<slug>.json 명함이 이미 있어야 함. wrangler 로그인 상태.
"""
import os, sys, json, secrets, tempfile, subprocess, argparse

try:
    sys.stdout.reconfigure(encoding="utf-8")  # 한글/특수문자 콘솔 출력 안전
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))
NS_ID = "04014805e6a44adab2044d037676c2ce"            # KV CARD_SELF
WORKER = "https://simpleline-card-photos.jh-kim-28b.workers.dev"


def kv_put(key, value):
    """한글 값도 안전하게 들어가도록 --path(UTF-8 파일) 방식으로 KV 저장."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as t:
        t.write(value)
        tmp = t.name
    try:
        subprocess.run(
            ["npx", "wrangler", "kv", "key", "put", key, "--path", tmp,
             "--namespace-id", NS_ID, "--remote"],
            cwd=ROOT, check=True, shell=(os.name == "nt"),
        )
    finally:
        os.unlink(tmp)


def issue_token(slug, name):
    """slug 에 대한 새 업로드 토큰을 KV에 저장하고 업로드 링크를 반환."""
    token = secrets.token_urlsafe(12)
    kv_put(f"token:{token}", slug)
    kv_put(f"name:{token}", name)
    return f"{WORKER}/u/{token}"


def set_pin(slug, phone):
    """명함에서 사진 변경 시 본인 확인용 PIN(휴대폰 뒷 4자리)을 KV에 저장."""
    digits = "".join(c for c in str(phone) if c.isdigit())
    pin = digits[-4:]
    kv_put(f"pin:{slug}", pin)
    return pin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="직원 약자 (cards/<slug>.json 과 일치)")
    args = ap.parse_args()

    jp = os.path.join(ROOT, "cards", f"{args.slug}.json")
    if not os.path.exists(jp):
        print(f"[ERR] cards/{args.slug}.json 이 없습니다 — 명함을 먼저 만들어야 합니다.")
        sys.exit(1)
    with open(jp, encoding="utf-8") as f:
        data = json.load(f)
    name = data["front"]["name"]

    link = issue_token(args.slug, name)
    print("\n" + "=" * 56)
    print(f"  {name} ({args.slug}) 사진 업로드 링크")
    print("=" * 56)
    print(f"  {link}")
    print("=" * 56)
    print("  이 링크를 직원에게 카톡으로 보내세요.")
    print("  직원이 폰에서 열어 사진을 올리면 명함에 바로 반영됩니다.")
    print("  (토큰은 KV에만 저장 - git/공개 저장소에 남지 않음)\n")


if __name__ == "__main__":
    main()
