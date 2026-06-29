# -*- coding: utf-8 -*-
"""
연락처 셀프수정값 동기화 (KV → cards/*.json)

직원이 폰에서 셀프 수정한 연락처(전화·이메일·한글주소)는 Cloudflare KV(contact:<slug>)에
쌓인다. 이 스크립트는 그 값을 원본 cards/*.json 으로 되돌려쓴다.
→ 관리자가 build_card.py 로 재빌드해도 셀프수정이 사라지지 않게(원본 이원화/덮어쓰기 방지).

운영 규칙: **관리자 재빌드 전에 항상 먼저 실행**한다.
    python sync_contacts.py            # 전체 동기화 후 차이 출력
    python sync_contacts.py --dry-run  # 변경 미리보기만

직책·부서·이름은 셀프수정 대상이 아니므로 건드리지 않는다.
영문(뒷면) 주소도 자동변환 부정확으로 그대로 둔다(전화/이메일만 영문면 반영).
"""
import json, glob, os, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
WORKER = "https://simpleline-card-photos.jh-kim-28b.workers.dev"
DRY = "--dry-run" in sys.argv


def intl(p):
    """010-1234-5678 → +82-10-1234-5678 (이미 +로 시작하면 그대로)."""
    d = str(p).strip()
    if d.startswith("+"):
        return d
    d = d.replace(" ", "")
    if d.startswith("0"):
        d = d[1:]
    return "+82-" + d


def fetch_override(slug):
    url = f"{WORKER}/contact/{slug}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except (urllib.error.URLError, ValueError, TimeoutError) as e:
        print(f"  ! {slug}: 조회 실패 ({e})")
        return None


def apply_override(data, ov):
    """ov(KV 셀프수정값)를 card data dict 에 반영. 바뀐 항목 라벨 리스트 반환."""
    changed = []
    f, b, vc = data["front"], data["back"], data["vcard"]
    phones = [p for p in (ov.get("phones") or []) if str(p).strip()]
    if phones:
        if f.get("phones") != phones:
            f["phones"] = phones
            b["phones"] = [intl(p) for p in phones]
            vc["cell"] = intl(phones[0])
            vc["work_tel"] = intl(phones[1]) if len(phones) > 1 else vc.get("work_tel", "")
            changed.append("전화")
    email = (ov.get("email") or "").strip()
    if email and not (f.get("email") == b.get("email") == vc.get("email") == email):
        f["email"] = b["email"] = vc["email"] = email
        changed.append("이메일")
    addr = [a for a in (ov.get("addr") or []) if str(a).strip()]
    if addr:
        if f.get("addresses") != addr:
            f["addresses"] = addr
            vc["adr"] = " ".join(addr)
            changed.append("주소(한글)")
    return changed


def main():
    total = 0
    for jp in sorted(glob.glob(os.path.join(ROOT, "cards", "*.json"))):
        slug = os.path.splitext(os.path.basename(jp))[0]
        ov = fetch_override(slug)
        if not ov or not (ov.get("phones") or ov.get("email") or ov.get("addr")):
            continue
        with open(jp, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        changed = apply_override(data, ov)
        if not changed:
            continue
        total += 1
        print(f"  ✎ {slug}: {', '.join(changed)} 갱신")
        if not DRY:
            with open(jp, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
                fp.write("\n")
    if total == 0:
        print("동기화할 셀프수정 없음.")
    else:
        print(f"\n{'[미리보기] ' if DRY else ''}{total}개 카드 갱신{' 예정' if DRY else ' 완료'}.")
        if not DRY:
            print("→ 이제 build_card.py 로 재빌드 후 commit/push 하세요.")


if __name__ == "__main__":
    main()
