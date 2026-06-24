# -*- coding: utf-8 -*-
"""
디지털 명함 생성기 (공용)
사용법:
    python build_card.py cards/kjh.json --base-url https://aacbal22.github.io/simpleline-cards
    python build_card.py cards/*.json   --base-url https://aacbal22.github.io/simpleline-cards   # 전체 일괄

입력: cards/<slug>.json  (앞면 한글 + 뒷면 영문 + vCard 데이터)
출력:
    docs/card/<slug>/index.html   ← QR이 가리키는 디지털 명함 페이지
    docs/qr/<slug>.png            ← 인쇄/공유용 QR 이미지
"""
import json, sys, os, glob, argparse, html

ROOT = os.path.dirname(os.path.abspath(__file__))


def esc(s):
    return html.escape(str(s), quote=True)


def build_vcard(v):
    """vCard 3.0 문자열 생성 (UTF-8). 스캔/저장 시 폰 연락처에 들어감."""
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{v.get('last_name','')};{v.get('first_name','')};;;",
        f"FN:{v.get('full_name_kr') or (v.get('first_name','')+' '+v.get('last_name','')).strip()}",
        f"ORG:{v.get('org','')}",
        f"TITLE:{v.get('title','')}",
    ]
    if v.get("cell"):
        lines.append(f"TEL;TYPE=CELL:{v['cell']}")
    if v.get("work_tel"):
        lines.append(f"TEL;TYPE=WORK,VOICE:{v['work_tel']}")
    if v.get("email"):
        lines.append(f"EMAIL;TYPE=WORK:{v['email']}")
    if v.get("url"):
        lines.append(f"URL:{v['url']}")
    if v.get("adr"):
        lines.append(f"ADR;TYPE=WORK:;;{v['adr']};;;;")
    lines.append("END:VCARD")
    return "\r\n".join(lines)


def render_html(data, base_url):
    slug = data["slug"]
    brand = data.get("brand_color", "#B0481F")
    f, b = data["front"], data["back"]
    vcard = build_vcard(data["vcard"])
    # JS 문자열 안전 삽입을 위해 \r\n 을 \\n 으로
    vcard_js = vcard.replace("\r\n", "\\n")
    page_url = f"{base_url}/card/{slug}/"

    def phone_links(phones):
        out = []
        for p in phones:
            tel = p.replace(" ", "").replace("-", "")
            out.append(f'<a href="tel:{esc(tel)}" class="row"><span class="ico">☎</span>{esc(p)}</a>')
        return "\n".join(out)

    front_phones = phone_links(f["phones"])
    back_phones = phone_links(b["phones"])
    front_addr = "<br>".join(esc(a) for a in f["addresses"])
    back_addr = "<br>".join(esc(a) for a in b["addresses"])

    tpl = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>%%FN%% · %%COMPANY_KR%% 디지털 명함</title>
<meta name="description" content="%%FN%% %%TITLE%% — %%COMPANY_KR%% 디지털 명함">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
:root{ --brand:%%BRAND%%; --ink:#1a1a1a; --muted:#6b6b6b; --line:#ececec; }
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{height:100%}
body{font-family:'Pretendard',-apple-system,'Apple SD Gothic Neo',sans-serif;background:#f1f0ee;color:var(--ink);
  display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100dvh;padding:18px;gap:14px}
.tabs{display:flex;gap:6px;background:#e3e1de;padding:4px;border-radius:999px}
.tab{border:0;background:transparent;font:inherit;font-size:14px;font-weight:600;color:var(--muted);
  padding:8px 20px;border-radius:999px;cursor:pointer;transition:.18s}
.tab.active{background:#fff;color:var(--brand);box-shadow:0 1px 4px rgba(0,0,0,.08)}
.card{width:100%;max-width:380px;aspect-ratio:1.75/1;border-radius:18px;overflow:hidden;
  box-shadow:0 12px 34px rgba(0,0,0,.16);position:relative;display:none}
.card.show{display:block}
/* FRONT (KR) */
.front{background:#fbfaf8;padding:24px 24px 20px}
.front .logo{font-size:21px;font-weight:800;color:var(--brand);letter-spacing:-.5px}
.front .logo small{font-size:13px;font-weight:700;vertical-align:6px;margin-right:2px}
.front .who{position:absolute;top:24px;right:24px;text-align:right}
.front .who .nm{font-size:19px;font-weight:800;letter-spacing:-.3px}
.front .who .nm em{font-size:12px;font-weight:600;font-style:normal;margin-left:4px;color:var(--muted)}
.front .who .dp{font-size:12px;color:var(--muted);margin-top:1px}
.front .info{position:absolute;left:24px;right:24px;bottom:18px;text-align:right;font-size:11.5px;line-height:1.55;color:#333}
.front .info .em{color:var(--brand);font-weight:600}
/* BACK (EN) */
.back{background:var(--brand);color:#fff;padding:24px}
.back .vbrand{position:absolute;left:20px;top:0;bottom:0;display:flex;align-items:center}
.back .vbrand span{writing-mode:vertical-rl;transform:rotate(180deg);font-size:17px;font-weight:800;letter-spacing:1px}
.back .who{text-align:right}
.back .who .nm{font-size:18px;font-weight:800;letter-spacing:.5px}
.back .who .dp{font-size:12px;opacity:.92;margin-top:2px}
.back .info{position:absolute;right:24px;bottom:18px;text-align:right;font-size:11px;line-height:1.55;opacity:.95}
/* actions */
.actions{display:flex;flex-direction:column;gap:8px;width:100%;max-width:380px}
.btn{display:flex;align-items:center;justify-content:center;gap:8px;border:0;border-radius:12px;
  font:inherit;font-size:15px;font-weight:700;padding:14px;cursor:pointer;text-decoration:none}
.btn-primary{background:var(--brand);color:#fff}
.btn-row{display:flex;gap:8px}
.btn-row .btn{flex:1;background:#fff;color:var(--ink);border:1px solid var(--line);font-size:14px}
.hint{font-size:11px;color:#9a9a9a;text-align:center}
.row{display:block;color:inherit;text-decoration:none}
.ico{display:inline-block;width:14px;opacity:.6;margin-right:4px}
</style>
</head>
<body>
  <div class="tabs">
    <button class="tab active" data-side="front">한글</button>
    <button class="tab" data-side="back">English</button>
  </div>

  <!-- 앞면 (한글) -->
  <div class="card front show" id="front">
    <div class="logo"><small>%%MARK%%</small>%%COMPANY_KR%%</div>
    <div class="who">
      <div class="nm">%%F_NAME%%<em>%%F_TITLE%%</em></div>
      <div class="dp">%%F_DEPT%%</div>
    </div>
    <div class="info">
      %%F_PHONES%%
      <a href="mailto:%%EMAIL%%" class="row"><span class="ico">✉</span><span class="em">%%EMAIL%%</span></a>
      <div style="margin-top:4px">%%F_ADDR%%</div>
      <a href="http://%%WEB%%" class="row" style="color:var(--brand);font-weight:600">%%WEB%%</a>
    </div>
  </div>

  <!-- 뒷면 (영문) -->
  <div class="card back" id="back">
    <div class="vbrand"><span>%%COMPANY_EN%%</span></div>
    <div class="who">
      <div class="nm">%%B_NAME%%</div>
      <div class="dp">%%B_TITLE%%</div>
    </div>
    <div class="info">
      %%B_PHONES%%
      <a href="mailto:%%EMAIL%%" class="row" style="color:#fff"><span class="ico" style="opacity:.8">✉</span>%%EMAIL%%</a>
      <div style="margin-top:4px">%%B_ADDR%%</div>
      <div>%%WEB%%</div>
    </div>
  </div>

  <div class="actions">
    <button class="btn btn-primary" id="save">📇 연락처 저장 / Save Contact</button>
    <div class="btn-row">
      <a class="btn" href="tel:%%CELL%%">☎ 전화</a>
      <a class="btn" href="sms:%%CELL%%">💬 문자</a>
      <a class="btn" href="mailto:%%EMAIL%%">✉ 메일</a>
    </div>
    <div class="hint">QR 스캔 → 이 명함 · 탭으로 한글/영문 전환</div>
  </div>

<script>
  // 탭 전환
  var tabs=document.querySelectorAll('.tab');
  tabs.forEach(function(t){t.onclick=function(){
    tabs.forEach(function(x){x.classList.remove('active')});t.classList.add('active');
    var s=t.dataset.side;
    document.getElementById('front').classList.toggle('show',s==='front');
    document.getElementById('back').classList.toggle('show',s==='back');
  }});
  // vCard 다운로드
  var VCARD="%%VCARD_JS%%";
  document.getElementById('save').onclick=function(){
    var blob=new Blob([VCARD],{type:'text/vcard;charset=utf-8'});
    var a=document.createElement('a');
    a.href=URL.createObjectURL(blob);a.download='%%SLUG%%.vcf';
    document.body.appendChild(a);a.click();a.remove();
  };
</script>
</body>
</html>
"""
    repl = {
        "%%FN%%": esc(data["vcard"].get("full_name_kr", f["name"])),
        "%%BRAND%%": brand,
        "%%MARK%%": esc(data.get("company_mark", "")),
        "%%COMPANY_KR%%": esc(data.get("company_kr", "")),
        "%%COMPANY_EN%%": esc(data.get("company_en", "")),
        "%%F_NAME%%": esc(f["name"]),
        "%%F_TITLE%%": esc(f.get("title", "")),
        "%%F_DEPT%%": esc(f.get("dept", "")),
        "%%F_PHONES%%": front_phones,
        "%%F_ADDR%%": front_addr,
        "%%B_NAME%%": esc(b["name"]),
        "%%B_TITLE%%": esc(b.get("title", "")),
        "%%B_PHONES%%": back_phones,
        "%%B_ADDR%%": back_addr,
        "%%TITLE%%": esc(f.get("title", "")),
        "%%EMAIL%%": esc(f["email"]),
        "%%WEB%%": esc(f["web"]),
        "%%CELL%%": esc(data["vcard"].get("cell", "").replace(" ", "")),
        "%%VCARD_JS%%": vcard_js,
        "%%SLUG%%": slug,
    }
    out = tpl
    for k, val in repl.items():
        out = out.replace(k, val)
    return out, page_url


def make_qr(url, out_path):
    import qrcode
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a1a1a", back_color="white")
    img.save(out_path)


def process(json_path, base_url):
    with open(json_path, encoding="utf-8") as fp:
        data = json.load(fp)
    slug = data["slug"]
    html_out, page_url = render_html(data, base_url)
    card_dir = os.path.join(ROOT, "docs", "card", slug)
    os.makedirs(card_dir, exist_ok=True)
    with open(os.path.join(card_dir, "index.html"), "w", encoding="utf-8") as fp:
        fp.write(html_out)
    qr_dir = os.path.join(ROOT, "docs", "qr")
    os.makedirs(qr_dir, exist_ok=True)
    make_qr(page_url, os.path.join(qr_dir, f"{slug}.png"))
    print(f"[OK] {slug}")
    print(f"     page : {page_url}")
    print(f"     html : docs/card/{slug}/index.html")
    print(f"     qr   : docs/qr/{slug}.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", help="cards/*.json")
    ap.add_argument("--base-url", required=True, help="GitHub Pages 베이스 URL")
    args = ap.parse_args()
    files = []
    for pat in args.inputs:
        files.extend(glob.glob(pat))
    if not files:
        print("입력 JSON을 찾지 못함:", args.inputs); sys.exit(1)
    for jp in files:
        process(jp, args.base_url.rstrip("/"))


if __name__ == "__main__":
    main()
