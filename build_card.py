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

# 직원 셀프 업로드 사진 서빙 Worker (사진만 동적, 명함 본체는 GitHub Pages 유지)
PHOTO_WORKER = "https://simpleline-card-photos.jh-kim-28b.workers.dev"
# 사진 로드 폴백: Worker사진 실패 → 정적 assets 사진 → 둘 다 없으면 숨김
_AVATAR_ONERR = ("this.onerror=null;var s=this.dataset.static;"
                 "if(s){this.src=s;this.onerror=function(){this.style.display='none'};}"
                 "else{this.style.display='none';}")


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

    # 사진: 셀프업로드(Worker) 우선, 폴백으로 정적 assets 사진(있으면), 둘 다 없으면 숨김
    photo = data.get("photo")
    static_src = f"../../assets/{esc(photo)}" if photo else ""
    avatar_html = (f'<img class="avatar" src="{PHOTO_WORKER}/photo/{slug}" alt="{esc(f["name"])}" '
                   f'data-static="{static_src}" onerror="{_AVATAR_ONERR}">')

    tagline = f.get("tagline") or data.get("tagline") or ""
    tagline_html = f'<div class="tagline">{esc(tagline)}</div>' if tagline else ""

    # 홈화면 아이콘: 사진 있으면 본인 얼굴, 없으면 공용 브랜드 아이콘
    icon_rel = f"../../assets/{esc(photo)}" if photo else "../../assets/icon-180.png"

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
<!-- 항상 최신을 받도록 캐시 최소화 -->
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<!-- 폰 홈화면 추가용 아이콘/테마 -->
<meta name="theme-color" content="%%BRAND%%">
<link rel="apple-touch-icon" href="%%ICON%%">
<link rel="icon" type="image/png" href="%%ICON%%">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="%%FN%%">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
:root{ color-scheme:light dark; --brand:%%BRAND%%; --ink:#1a1a1a; --muted:#6b6b6b; --line:#ececec;
  --bg:#f1f0ee; --surface:#ffffff; --tab-bg:#e3e1de; --shadow:rgba(0,0,0,.16); }
@media (prefers-color-scheme:dark){
  :root{ --ink:#ededed; --muted:#a3a3a3; --line:#3a3836;
    --bg:#161514; --surface:#222120; --tab-bg:#2c2b29; --shadow:rgba(0,0,0,.55); }
}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{height:100%}
body{font-family:'Pretendard',-apple-system,'Apple SD Gothic Neo',sans-serif;background:var(--bg);color:var(--ink);
  display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100dvh;padding:18px;gap:14px}
.avatar{width:156px;height:156px;border-radius:50%;object-fit:cover;border:4px solid var(--surface);box-shadow:0 6px 18px var(--shadow);margin-bottom:2px}
.tabs{display:flex;gap:6px;background:var(--tab-bg);padding:4px;border-radius:999px}
.tab{border:0;background:transparent;font:inherit;font-size:14px;font-weight:600;color:var(--muted);
  padding:8px 20px;border-radius:999px;cursor:pointer;transition:.18s}
.tab.active{background:var(--surface);color:var(--brand);box-shadow:0 1px 4px rgba(0,0,0,.08)}
/* 명함 3D 플립 */
.flip{width:100%;max-width:380px;aspect-ratio:1.75/1;perspective:1600px}
.flip-inner{position:relative;width:100%;height:100%;transition:transform .65s cubic-bezier(.4,.1,.2,1);transform-style:preserve-3d}
.flip-inner.flipped{transform:rotateY(180deg)}
.card{position:absolute;inset:0;border-radius:18px;overflow:hidden;
  box-shadow:0 12px 34px var(--shadow);backface-visibility:hidden;-webkit-backface-visibility:hidden}
.card.back{transform:rotateY(180deg)}
/* FRONT (KR) */
.front{background:#fbfaf8;padding:24px 24px 20px}
.front .logo{font-size:21px;font-weight:800;color:var(--brand);letter-spacing:-.5px}
.front .logo small{font-size:13px;font-weight:700;vertical-align:6px;margin-right:2px}
.front .tagline{position:absolute;left:24px;top:54px;right:120px;font-size:11px;font-style:italic;
  color:#6b6b6b;line-height:1.4;letter-spacing:-.2px}
.front .who{position:absolute;top:24px;right:24px;text-align:right}
/* 명함은 항상 밝은 종이 → 글자색은 다크모드와 무관하게 진한 고정색 */
.front .who .nm{font-size:19px;font-weight:800;letter-spacing:-.3px;color:#111}
.front .who .nm em{font-size:12px;font-weight:600;font-style:normal;margin-left:4px;color:#6b6b6b}
.front .who .dp{font-size:12px;color:#6b6b6b;margin-top:1px}
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
.btn-row .btn{flex:1;background:var(--surface);color:var(--ink);border:1px solid var(--line);font-size:14px}
.btn-ghost{background:var(--surface);color:var(--ink);border:1px solid var(--line)}
.hint{font-size:11px;color:#9a9a9a;text-align:center}
.row{display:block;color:inherit;text-decoration:none}
.ico{display:inline-block;width:14px;opacity:.6;margin-right:4px}
/* QR 보여주기 오버레이 — 스캔 화면은 항상 밝게(다크모드 비의존) */
.qr-overlay{position:fixed;inset:0;background:#fff;display:none;flex-direction:column;
  align-items:center;justify-content:center;gap:18px;z-index:99;padding:24px}
.qr-overlay.on{display:flex}
.qr-overlay img{width:min(78vw,360px);height:auto;border:1px solid #ececec;border-radius:12px}
.qr-overlay .cap{font-size:15px;font-weight:700;color:#1a1a1a}
.qr-overlay .sub{font-size:13px;color:#6b6b6b;margin-top:-10px}
.qr-overlay .close{border:1px solid #ececec;background:#fff;color:#1a1a1a;border-radius:12px;
  font:inherit;font-weight:700;padding:12px 28px;cursor:pointer}
</style>
</head>
<body>
  %%AVATAR%%
  <div class="tabs">
    <button class="tab active" data-side="front">한글</button>
    <button class="tab" data-side="back">English</button>
  </div>

  <div class="flip">
   <div class="flip-inner" id="flip">
    <!-- 앞면 (한글) -->
    <div class="card front" id="front">
      <div class="logo"><small>%%MARK%%</small>%%COMPANY_KR%%</div>
      %%TAGLINE%%
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
   </div>
  </div>

  <div class="actions">
    <button class="btn btn-primary" id="save">📇 연락처 저장 / Save Contact</button>
    <button class="btn btn-ghost" id="share">🔗 명함 링크 공유 / Share</button>
    <button class="btn btn-ghost" id="showqr">📲 상대에게 내 QR 보여주기</button>
    <div class="btn-row">
      <a class="btn" href="tel:%%CELL%%">☎ 전화</a>
      <a class="btn" href="sms:%%CELL%%">💬 문자</a>
      <a class="btn" href="mailto:%%EMAIL%%">✉ 메일</a>
    </div>
    <div class="hint">QR 스캔 → 이 명함 · 탭/명함 터치로 한글↔영문 전환</div>
  </div>

  <!-- 내 QR 전체화면 (상대가 스캔하도록 보여주기) -->
  <div class="qr-overlay" id="qrov">
    <div class="cap">%%FN%% · %%COMPANY_KR%%</div>
    <img src="../../qr/%%SLUG%%.png" alt="내 명함 QR">
    <div class="sub">이 QR을 스캔하면 제 명함이 열립니다</div>
    <button class="close" id="closeqr">닫기</button>
  </div>

<script>
  // 탭 / 명함 터치로 앞뒤 3D 플립
  var tabs=document.querySelectorAll('.tab'),flip=document.getElementById('flip');
  function setSide(s){
    tabs.forEach(function(x){x.classList.toggle('active',x.dataset.side===s)});
    flip.classList.toggle('flipped',s==='back');
  }
  tabs.forEach(function(t){t.onclick=function(){setSide(t.dataset.side)}});
  flip.addEventListener('click',function(e){
    if(e.target.closest('a,button')) return;   // 링크/버튼 탭은 플립하지 않음
    setSide(flip.classList.contains('flipped')?'front':'back');
  });
  // 명함 링크 공유 (카톡·문자 등) — 미지원 브라우저는 클립보드 복사
  var PAGE="%%PAGE_URL%%";
  document.getElementById('share').onclick=function(){
    if(navigator.share){
      navigator.share({title:"%%FN%% · %%COMPANY_KR%%",text:"%%FN%% 디지털 명함",url:PAGE}).catch(function(){});
    }else{
      navigator.clipboard.writeText(PAGE).then(function(){alert('명함 링크가 복사되었습니다\n'+PAGE)});
    }
  };
  // 내 QR 보여주기
  var ov=document.getElementById('qrov');
  document.getElementById('showqr').onclick=function(){ov.classList.add('on')};
  document.getElementById('closeqr').onclick=function(){ov.classList.remove('on')};
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
        "%%AVATAR%%": avatar_html,
        "%%TAGLINE%%": tagline_html,
        "%%PAGE_URL%%": page_url,
        "%%ICON%%": icon_rel,
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


def make_brand_icons(brand="#B0481F", text="SL"):
    """폰 홈화면용 공용 브랜드 아이콘. 브랜드 컬러 배경 + 흰 모노그램.
    docs/assets/icon-180.png (Apple touch icon) · icon-512.png 생성."""
    from PIL import Image, ImageDraw, ImageFont
    assets = os.path.join(ROOT, "docs", "assets")
    os.makedirs(assets, exist_ok=True)
    for size in (180, 512):
        img = Image.new("RGB", (size, size), brand)
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", int(size * 0.44))
        except Exception:
            font = ImageFont.load_default()
        tb = d.textbbox((0, 0), text, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        d.text(((size - tw) / 2 - tb[0], (size - th) / 2 - tb[1]), text, font=font, fill="white")
        img.save(os.path.join(assets, f"icon-{size}.png"))
    print("[ICON] docs/assets/icon-180.png · icon-512.png")


def make_share(data, page_url, out_path):
    """카톡 '나와의 채팅' 등에 보내기 좋은, 이름표 들어간 공유용 QR 이미지."""
    import qrcode
    from PIL import Image, ImageDraw, ImageFont

    brand = data.get("brand_color", "#B0481F")
    f = data["front"]
    name = f["name"]
    title = f.get("title", "")
    dept = f.get("dept", "")
    company = (data.get("company_mark", "") + data.get("company_kr", "")).strip()
    web = f.get("web", "")

    W, H = 820, 1080
    canvas = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(canvas)

    FB = "C:/Windows/Fonts/malgunbd.ttf"
    FR = "C:/Windows/Fonts/malgun.ttf"
    f_company = ImageFont.truetype(FB, 30)
    f_name = ImageFont.truetype(FB, 52)
    f_title = ImageFont.truetype(FB, 30)
    f_dept = ImageFont.truetype(FR, 26)
    f_cap = ImageFont.truetype(FB, 30)
    f_url = ImageFont.truetype(FR, 22)

    # 상단 브랜드 바
    d.rectangle([0, 0, W, 12], fill=brand)

    # 회사명 (브랜드 컬러)
    d.text((60, 56), company, font=f_company, fill=brand)

    # 이름 + 직함
    name_y = 100
    d.text((60, name_y), name, font=f_name, fill="#1a1a1a")
    nbox = d.textbbox((60, name_y), name, font=f_name)
    d.text((nbox[2] + 12, name_y + 18), title, font=f_title, fill="#6b6b6b")
    if dept:
        d.text((60, name_y + 66), dept, font=f_dept, fill="#6b6b6b")

    # QR (중앙)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=14, border=1)
    qr.add_data(page_url)
    qr.make(fit=True)
    qimg = qr.make_image(fill_color="#1a1a1a", back_color="white").convert("RGB")
    QS = 600
    qimg = qimg.resize((QS, QS), Image.NEAREST)
    qx = (W - QS) // 2
    qy = 250
    canvas.paste(qimg, (qx, qy))

    # 캡션 (중앙)
    cap = "스캔하면 디지털 명함이 열립니다"
    cbox = d.textbbox((0, 0), cap, font=f_cap)
    d.text(((W - (cbox[2] - cbox[0])) // 2, qy + QS + 36), cap, font=f_cap, fill="#1a1a1a")

    # URL (중앙, 연한색)
    ubox = d.textbbox((0, 0), page_url, font=f_url)
    d.text(((W - (ubox[2] - ubox[0])) // 2, qy + QS + 84), page_url, font=f_url, fill="#9a9a9a")

    # 하단 브랜드 바
    d.rectangle([0, H - 12, W, H], fill=brand)

    canvas.save(out_path)


def build_index(base_url):
    """cards/*.json 전체를 읽어 관리용 명함 갤러리(docs/index.html) 생성."""
    items = []
    for jp in sorted(glob.glob(os.path.join(ROOT, "cards", "*.json"))):
        with open(jp, encoding="utf-8") as fp:
            dd = json.load(fp)
        f = dd["front"]
        items.append({
            "slug": dd["slug"],
            "name": f["name"],
            "title": f.get("title", ""),
            "dept": f.get("dept", ""),
            "photo": dd.get("photo", ""),
            "company": (dd.get("company_mark", "") + dd.get("company_kr", "")).strip(),
            "url": f"{base_url}/card/{dd['slug']}/",
        })
    depts = sorted({it["dept"] for it in items if it.get("dept")})
    dept_chips = "".join(
        f'<button class="chip" data-dept="{esc(dp)}">{esc(dp)}</button>' for dp in depts
    )
    cards_html = []
    for it in items:
        gava_static = f'assets/{esc(it["photo"])}' if it.get("photo") else ""
        avatar = (f'<img class="gava" src="{PHOTO_WORKER}/photo/{esc(it["slug"])}" alt="{esc(it["name"])}" '
                  f'data-static="{gava_static}" loading="lazy" onerror="{_AVATAR_ONERR}">')
        search_key = f"{it['name']} {it['title']} {it['dept']}".strip()
        cards_html.append(f"""
      <div class="card" data-key="{esc(search_key)}" data-dept="{esc(it['dept'])}">
        <a class="qr" href="card/{esc(it['slug'])}/" title="명함 열기">
          <img src="qr/{esc(it['slug'])}.png" alt="{esc(it['name'])} QR" loading="lazy">
        </a>
        <div class="meta">
          {avatar}
          <div class="nm">{esc(it['name'])} <em>{esc(it['title'])}</em></div>
          <div class="dp">{esc(it['dept'])}</div>
        </div>
        <div class="acts">
          <a class="b prim" href="card/{esc(it['slug'])}/">명함 열기</a>
          <a class="b" href="qr/{esc(it['slug'])}_share.png" download>카톡 공유이미지</a>
          <button class="b" data-url="{esc(it['url'])}" onclick="cp(this)">링크 복사</button>
        </div>
      </div>""")
    page = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>심플라인 디지털 명함 관리</title>
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<meta name="theme-color" content="#B0481F">
<link rel="apple-touch-icon" href="assets/icon-180.png">
<link rel="icon" type="image/png" href="assets/icon-180.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="심플라인 명함">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
:root{color-scheme:light;--brand:#B0481F;--ink:#1a1a1a;--muted:#6b6b6b;--line:#ececec}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{font-family:'Pretendard',-apple-system,sans-serif;background:#f1f0ee;color:var(--ink);padding:24px 16px 48px}
.wrap{max-width:920px;margin:0 auto}
header{border-top:4px solid var(--brand);padding:18px 0 16px}
header h1{font-size:21px;font-weight:800;letter-spacing:-.3px}
header p{font-size:13px;color:var(--muted);margin-top:4px}
.count{font-size:12px;color:var(--brand);font-weight:700;margin-top:8px}
.controls{margin-top:14px;display:flex;flex-direction:column;gap:10px}
.search{width:100%;font:inherit;font-size:14px;padding:11px 14px;border:1px solid var(--line);
  border-radius:11px;background:#fff;color:var(--ink);outline:none}
.search:focus{border-color:var(--brand)}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font:inherit;font-size:12.5px;font-weight:700;padding:7px 14px;border-radius:999px;
  border:1px solid var(--line);background:#fff;color:var(--muted);cursor:pointer;transition:.15s}
.chip.active{background:var(--brand);color:#fff;border-color:var(--brand)}
.empty{text-align:center;color:var(--muted);font-size:14px;padding:40px 0;display:none}
.card.hide{display:none}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;margin-top:18px}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px;display:flex;flex-direction:column;align-items:center;gap:10px;box-shadow:0 2px 10px rgba(0,0,0,.04)}
.card .qr{display:block}
.card .qr img{width:148px;height:148px;border:1px solid var(--line);border-radius:8px;display:block}
.meta{text-align:center}
.gava{width:54px;height:54px;border-radius:50%;object-fit:cover;border:2px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.15);margin-bottom:4px}
.meta .nm{font-size:16px;font-weight:800;color:#111}
.meta .nm em{font-size:12px;font-weight:600;font-style:normal;color:#6b6b6b;margin-left:3px}
.meta .dp{font-size:12px;color:#6b6b6b;margin-top:1px}
.acts{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;width:100%}
.b{flex:1;min-width:84px;text-align:center;font-size:12px;font-weight:700;padding:8px 6px;border-radius:9px;
  border:1px solid var(--line);background:#fff;color:var(--ink);cursor:pointer;text-decoration:none}
.b.prim{background:var(--brand);color:#fff;border-color:var(--brand)}
.toast{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);background:var(--ink);color:#fff;
  padding:10px 18px;border-radius:999px;font-size:13px;opacity:0;transition:.2s;pointer-events:none}
.toast.on{opacity:1}
footer{text-align:center;font-size:11px;color:#9a9a9a;margin-top:28px}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>심플라인 디지털 명함 관리</h1>
      <p>명함을 누르면 페이지가 열립니다 · QR/링크/공유이미지를 한곳에서 관리</p>
      <div class="count" id="count">총 %%COUNT%%명</div>
      <div class="controls">
        <input class="search" id="search" type="search" placeholder="🔍 이름·직함·부서 검색" autocomplete="off">
        <div class="chips" id="chips">
          <button class="chip active" data-dept="">전체</button>
          %%DEPTCHIPS%%
        </div>
      </div>
    </header>
    <div class="grid">%%CARDS%%
    </div>
    <div class="empty" id="empty">검색 결과가 없습니다</div>
    <footer>SIMPLELINE · GitHub Pages 호스팅 (PC 꺼져도 항상 열림)</footer>
  </div>
  <div class="toast" id="toast">링크가 복사되었습니다</div>
<script>
  function cp(btn){
    var u=btn.dataset.url;
    navigator.clipboard.writeText(u).then(function(){
      var t=document.getElementById('toast');t.classList.add('on');
      setTimeout(function(){t.classList.remove('on')},1500);
    });
  }
  // 검색 + 부서 필터
  var search=document.getElementById('search'),
      chips=document.querySelectorAll('.chip'),
      cards=document.querySelectorAll('.grid .card'),
      countEl=document.getElementById('count'),
      emptyEl=document.getElementById('empty'),
      curDept='';
  function apply(){
    var q=(search.value||'').trim().toLowerCase(),shown=0;
    cards.forEach(function(c){
      var okQ=!q||(c.dataset.key||'').toLowerCase().indexOf(q)>=0;
      var okD=!curDept||c.dataset.dept===curDept;
      var show=okQ&&okD;
      c.classList.toggle('hide',!show);
      if(show)shown++;
    });
    countEl.textContent='총 '+shown+'명';
    emptyEl.style.display=shown?'none':'block';
  }
  search.addEventListener('input',apply);
  chips.forEach(function(ch){ch.onclick=function(){
    chips.forEach(function(x){x.classList.remove('active')});ch.classList.add('active');
    curDept=ch.dataset.dept;apply();
  }});
</script>
</body>
</html>
"""
    page = (page.replace("%%COUNT%%", str(len(items)))
                .replace("%%DEPTCHIPS%%", dept_chips)
                .replace("%%CARDS%%", "".join(cards_html)))
    with open(os.path.join(ROOT, "docs", "index.html"), "w", encoding="utf-8") as fp:
        fp.write(page)
    print(f"[INDEX] docs/index.html ({len(items)}명)  →  {base_url}/")


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
    make_share(data, page_url, os.path.join(qr_dir, f"{slug}_share.png"))
    print(f"[OK] {slug}")
    print(f"     page  : {page_url}")
    print(f"     html  : docs/card/{slug}/index.html")
    print(f"     qr    : docs/qr/{slug}.png")
    print(f"     share : docs/qr/{slug}_share.png  (카톡 공유용)")


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
    base = args.base_url.rstrip("/")
    make_brand_icons()  # 폰 홈화면용 공용 브랜드 아이콘 (사진 없는 명함 + 갤러리)
    for jp in files:
        process(jp, base)
    build_index(base)  # 명함 추가/수정 시 관리 갤러리도 항상 갱신


if __name__ == "__main__":
    main()
