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
VERSION = "V1.2.2"
# 사진 로드 폴백: Worker사진 실패 → 정적 assets 사진 → 둘 다 없으면 숨김
_AVATAR_ONERR = ("this.onerror=null;var s=this.dataset.static;"
                 "if(s){this.src=s;this.onerror=function(){this.style.display='none'};}"
                 "else{this.style.display='none';}")


def esc(s):
    return html.escape(str(s), quote=True)


def vcard_head_lines(v):
    """vCard 고정부(BEGIN·VERSION·N·FN·ORG·TITLE) 라인 리스트.
    연락처 이름은 한글로 저장 — full_name_kr 사용(없을 때만 영문 폴백).
    직책·부서·이름은 셀프수정 대상이 아니므로 '고정부'로 묶는다."""
    kr_full = (v.get("full_name_kr") or "").strip()
    kr_last = (v.get("kr_last") or "").strip()
    kr_first = (v.get("kr_first") or "").strip()
    # 한글 성/이름 분리: 명시(kr_last/kr_first) 우선, 없으면 첫 글자=성(단성 가정).
    # 복성(남궁·황보 등)은 카드 JSON 의 vcard 에 kr_last/kr_first 를 직접 지정.
    if not (kr_last or kr_first) and kr_full:
        if len(kr_full) >= 2 and " " not in kr_full:
            kr_last, kr_first = kr_full[0], kr_full[1:]
        else:
            kr_last = kr_full
    if kr_last or kr_first:
        n_line = f"N:{kr_last};{kr_first};;;"
        fn = kr_full or f"{kr_last}{kr_first}"
    else:
        n_line = f"N:{v.get('last_name','')};{v.get('first_name','')};;;"
        fn = (v.get("first_name", "") + " " + v.get("last_name", "")).strip()
    return ["BEGIN:VCARD", "VERSION:3.0", n_line, f"FN:{fn}",
            f"ORG:{v.get('org','')}", f"TITLE:{v.get('title','')}"]


def build_vcard(v):
    """vCard 3.0 문자열 생성 (UTF-8). 스캔/저장 시 폰 연락처에 들어감."""
    lines = list(vcard_head_lines(v))
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

    # 사진: 셀프업로드(Worker) 우선, 폴백으로 정적 assets 사진(있으면). 탭하면 변경 모달.
    photo = data.get("photo")
    static_src = f"../../assets/{esc(photo)}" if photo else ""
    avatar_html = (
        f'<button class="avatar-btn" id="avatarBtn" aria-label="프로필 사진 변경">'
        f'<img class="avatar" id="avatarImg" src="{PHOTO_WORKER}/photo/{slug}" '
        f'alt="{esc(f["name"])}" data-static="{static_src}">'
        f'<span class="avatar-empty" id="avatarEmpty">＋<small>사진</small></span>'
        f'<span class="avatar-edit">✎ 변경</span>'
        f'</button>'
    )

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
<!-- 카톡 등 링크 미리보기(Open Graph). 공유 시 이름·직함·사진 노출 -->
<meta property="og:type" content="profile">
<meta property="og:title" content="%%FN%% %%TITLE%% · %%COMPANY_KR%%">
<meta property="og:description" content="%%COMPANY_KR%% 디지털 명함 — 탭하면 연락처 저장">
<meta property="og:image" content="%%OG_IMAGE%%">
<meta property="og:url" content="%%PAGE_URL%%">
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
html,body{height:100%;overflow-x:clip;max-width:100%}
body{font-family:'Pretendard',-apple-system,'Apple SD Gothic Neo',sans-serif;background:var(--bg);color:var(--ink);
  display:flex;flex-direction:column;align-items:center;justify-content:safe center;min-height:100dvh;padding:12px 18px;gap:10px}
.avatar-btn{position:relative;width:130px;height:130px;flex:0 0 auto;aspect-ratio:1/1;border-radius:50%;border:4px solid var(--surface);padding:0;
  background:#e3e1de;cursor:pointer;margin-bottom:2px;box-shadow:0 6px 18px var(--shadow);overflow:hidden;display:block}
.avatar{width:100%;height:100%;border-radius:50%;object-fit:cover;display:block}
.avatar-empty{position:absolute;inset:0;display:none;flex-direction:column;align-items:center;justify-content:center;color:#9a9a9a;font-size:32px;font-weight:300}
.avatar-empty small{font-size:11px;font-weight:600;margin-top:1px}
.avatar-edit{position:absolute;left:0;right:0;bottom:0;background:rgba(0,0,0,.5);color:#fff;font-size:10.5px;font-weight:700;padding:5px 0;text-align:center;letter-spacing:.3px}
/* 편집 표시(사진 '변경'·'내 연락처 수정')는 기본 숨김 → 소유자 기기(.owner)에서만 노출. 상대방 명함엔 안 보임 */
.avatar-edit{display:none}
.avatar-btn{cursor:default}
#cEditBtn{display:none}
.owner .avatar-edit{display:block}
.owner .avatar-btn{cursor:pointer}
.owner #cEditBtn{display:flex}
.tabs{display:flex;gap:6px;background:var(--tab-bg);padding:4px;border-radius:999px;flex:0 0 auto}
.tab{border:0;background:transparent;font:inherit;font-size:14px;font-weight:600;color:var(--muted);
  padding:8px 20px;border-radius:999px;cursor:pointer;transition:.18s}
.tab.active{background:var(--surface);color:var(--brand);box-shadow:0 1px 4px rgba(0,0,0,.08)}
/* 명함 3D 플립 */
.flip{width:100%;max-width:380px;perspective:1600px;flex:0 0 auto}
.flip-inner{position:relative;width:100%;transition:transform .65s cubic-bezier(.4,.1,.2,1);transform-style:preserve-3d}
.flip-inner.flipped{transform:rotateY(180deg)}
.card{position:absolute;inset:0;border-radius:18px;overflow:hidden;
  box-shadow:0 12px 34px var(--shadow);backface-visibility:hidden;-webkit-backface-visibility:hidden}
.card.back{transform:rotateY(180deg)}
/* 명함 공통: 절대배치 대신 세로 flex로 상단(이름)·하단(연락처) 분배 → 브라우저 무관 동일 렌더.
   앞면이 흐름에 있어 높이를 결정(aspect-ratio는 최소 비율). 좁은 화면선 카드가 늘어나 항상 줄간격 확보.
   뒷면은 절대배치로 앞면 높이에 겹침. */
.card.front{position:relative;inset:auto;min-height:190px}
.card.front,.card.back{display:flex;flex-direction:column;justify-content:space-between;gap:20px}
/* FRONT (KR) */
.front{background:#fbfaf8;padding:18px 22px 16px}
.front .fhead{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;min-width:0}
.front .fhead .who{min-width:0}
.front .logo{font-size:21px;font-weight:800;color:var(--brand);letter-spacing:-.5px;white-space:nowrap}
.front .logo small{font-size:13px;font-weight:700;vertical-align:6px;margin-right:2px}
.front .tagline{position:absolute;left:24px;top:54px;right:120px;font-size:11px;font-style:italic;
  color:#6b6b6b;line-height:1.4;letter-spacing:-.2px}
.front .who{text-align:right}
/* 명함은 항상 밝은 종이 → 글자색은 다크모드와 무관하게 진한 고정색 */
.front .who .nm{font-size:19px;font-weight:800;letter-spacing:-.3px;color:#111}
.front .who .nm em{font-size:12px;font-weight:600;font-style:normal;margin-left:4px;color:#6b6b6b}
.front .who .dp{font-size:12px;color:#6b6b6b;margin-top:1px}
.front .info{text-align:right;font-size:11.5px;line-height:1.6;color:#333}
.front .info .em{color:var(--brand);font-weight:600}
.info .addr{margin-top:5px}
/* BACK (EN) */
.back{background:var(--brand);color:#fff;padding:18px 22px}
.back .vbrand{position:absolute;left:20px;top:0;bottom:0;display:flex;align-items:center}
.back .vbrand span{writing-mode:vertical-rl;transform:rotate(180deg);font-size:17px;font-weight:800;letter-spacing:1px}
.back .who{text-align:right}
.back .who .nm{font-size:18px;font-weight:800;letter-spacing:.5px}
.back .who .dp{font-size:12px;opacity:.92;margin-top:2px}
.back .info{text-align:right;font-size:11px;line-height:1.6;opacity:.95}
/* actions */
.actions{display:flex;flex-direction:column;gap:7px;width:100%;max-width:380px;flex:0 0 auto}
.btn{display:flex;align-items:center;justify-content:center;gap:8px;border:0;border-radius:12px;
  font:inherit;font-size:15px;font-weight:700;padding:12px;cursor:pointer;text-decoration:none}
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
/* 사진 변경 모달 */
.modal{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;align-items:center;justify-content:center;z-index:200;padding:20px}
.modal.on{display:flex}
.sheet{position:relative;background:var(--surface);border-radius:18px;width:100%;max-width:360px;padding:24px 22px 22px;text-align:center;color:var(--ink)}
.sheet h3{font-size:17px;font-weight:800;margin-bottom:5px}
.sheet .desc{font-size:13px;color:var(--muted);margin-bottom:16px;line-height:1.5}
.m-close{position:absolute;top:10px;right:14px;font-size:24px;line-height:1;color:var(--muted);background:0;border:0;cursor:pointer}
.pin-in{width:170px;font:inherit;font-size:22px;font-weight:800;letter-spacing:10px;text-align:center;padding:12px 12px 12px 22px;border:1px solid var(--line);border-radius:12px;background:var(--surface);color:var(--ink);outline:none}
.pin-in:focus{border-color:var(--brand)}
.crop-area{width:240px;height:240px;border-radius:50%;overflow:hidden;margin:4px auto 6px;background:#222;touch-action:none;position:relative}
.crop-area canvas{width:100%;height:100%;display:block;cursor:grab}
.crop-ph{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#aaa;font-size:13px}
.zoom{width:100%;margin:8px 0 2px;accent-color:var(--brand)}
.m-btn{display:block;width:100%;border:0;border-radius:12px;font:inherit;font-size:15px;font-weight:700;padding:13px;cursor:pointer;margin-top:9px}
.m-btn:disabled{opacity:.45;cursor:default}
.m-primary{background:var(--brand);color:#fff}
.m-ghost{background:var(--surface);color:var(--ink);border:1px solid var(--line)}
.m-msg{font-size:13px;font-weight:700;min-height:17px;margin-top:9px}
.m-msg.err{color:#c0392b}.m-msg.ok{color:#1a7a3c}
.step{display:none}.step.on{display:block}
input[type=file]{display:none}
.c-lab{display:block;text-align:left;font-size:12.5px;font-weight:700;color:var(--muted);margin:11px 0 4px}
.c-in{width:100%;font:inherit;font-size:15px;padding:11px 12px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--ink);outline:none;box-sizing:border-box}
.c-in:focus{border-color:var(--brand)}
textarea.c-in{resize:vertical;line-height:1.5}
.c-note{text-align:left;font-size:11.5px;color:var(--muted);line-height:1.5;margin:10px 0 2px}
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
      <div class="fhead">
        <div class="logo"><small>%%MARK%%</small>%%COMPANY_KR%%</div>
        <div class="who">
          <div class="nm">%%F_NAME%%<em>%%F_TITLE%%</em></div>
          <div class="dp">%%F_DEPT%%</div>
        </div>
      </div>
      %%TAGLINE%%
      <div class="info">
        <div id="fPhones" style="display:contents">%%F_PHONES%%</div>
        <a href="mailto:%%EMAIL%%" class="row" id="fEmail"><span class="ico">✉</span><span class="em">%%EMAIL%%</span></a>
        <div id="fAddr" class="addr">%%F_ADDR%%</div>
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
        <div id="bPhones" style="display:contents">%%B_PHONES%%</div>
        <a href="mailto:%%EMAIL%%" class="row" id="bEmail" style="color:#fff"><span class="ico" style="opacity:.8">✉</span>%%EMAIL%%</a>
        <div id="bAddr" class="addr">%%B_ADDR%%</div>
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
      <a class="btn" id="actCall" href="tel:%%CELL%%">☎ 전화</a>
      <a class="btn" id="actSms" href="sms:%%CELL%%">💬 문자</a>
      <a class="btn" id="actMail" href="mailto:%%EMAIL%%">✉ 메일</a>
    </div>
    <button type="button" class="btn btn-ghost" id="cEditBtn" style="font-size:13.5px;padding:11px">✎ 내 연락처 수정 (전화·이메일·주소)</button>
    <div class="hint">QR 스캔 → 이 명함 · 탭/명함 터치로 한글↔영문 전환</div>
  </div>

  <!-- 내 QR 전체화면 (상대가 스캔하도록 보여주기) -->
  <div class="qr-overlay" id="qrov">
    <div class="cap">%%FN%% · %%COMPANY_KR%%</div>
    <img src="../../qr/%%SLUG%%.png" alt="내 명함 QR">
    <div class="sub">이 QR을 스캔하면 제 명함이 열립니다</div>
    <button class="close" id="closeqr">닫기</button>
  </div>

  <!-- 사진 변경 모달 (사진 탭하면 열림) -->
  <div class="modal" id="photoModal">
    <div class="sheet">
      <button class="m-close" id="mClose">&times;</button>
      <!-- 1) 본인 확인 -->
      <div class="step on" id="stepPin">
        <h3>본인 확인</h3>
        <div class="desc">내 휴대폰 번호 <b>뒷 4자리</b>를 입력하세요.</div>
        <input class="pin-in" id="pinIn" type="tel" inputmode="numeric" maxlength="4" placeholder="0000">
        <div class="m-msg" id="pinMsg"></div>
        <button class="m-btn m-primary" id="pinNext">다음</button>
      </div>
      <!-- 2) 사진 편집 -->
      <div class="step" id="stepCrop">
        <h3>사진 편집</h3>
        <div class="desc">드래그로 위치, 슬라이더로 크기를 맞추세요.</div>
        <div class="crop-area"><canvas id="cropCv" width="512" height="512"></canvas><div class="crop-ph" id="cropPh">사진을 선택하세요</div></div>
        <input class="zoom" id="zoom" type="range" min="1" max="3" step="0.01" value="1" disabled>
        <label class="m-btn m-ghost" for="fileIn">📷 사진 선택 / 변경</label>
        <input type="file" id="fileIn" accept="image/*">
        <button class="m-btn m-primary" id="upBtn" disabled>이 사진으로 등록</button>
        <div class="m-msg" id="cropMsg"></div>
      </div>
    </div>
  </div>

  <!-- 연락처 수정 모달 (전화·이메일·주소만. 직책·부서·이름은 관리자 전용) -->
  <div class="modal" id="contactModal">
    <div class="sheet">
      <button class="m-close" id="cmClose">&times;</button>
      <!-- 1) 본인 확인 -->
      <div class="step on" id="cStepPin">
        <h3>본인 확인</h3>
        <div class="desc">내 휴대폰 번호 <b>뒷 4자리</b>를 입력하세요.</div>
        <input class="pin-in" id="cPinIn" type="tel" inputmode="numeric" maxlength="4" placeholder="0000">
        <div class="m-msg" id="cPinMsg"></div>
        <button class="m-btn m-primary" id="cPinNext">다음</button>
      </div>
      <!-- 2) 연락처 입력 -->
      <div class="step" id="cStepForm">
        <h3>연락처 수정</h3>
        <div class="desc">전화·이메일·주소만 바꿀 수 있어요. 직책·부서·이름 변경은 실장님께 요청하세요.</div>
        <label class="c-lab">휴대폰</label>
        <input class="c-in" id="cMobile" type="tel" inputmode="tel" placeholder="010-0000-0000">
        <label class="c-lab">직통(사무실) 전화 <span style="opacity:.55">— 선택</span></label>
        <input class="c-in" id="cTel" type="tel" inputmode="tel" placeholder="031-000-0000">
        <label class="c-lab">이메일</label>
        <input class="c-in" id="cEmail" type="email" inputmode="email" placeholder="name@simpleline.co.kr">
        <label class="c-lab">주소(한글) <span style="opacity:.55">— 줄바꿈으로 여러 줄</span></label>
        <textarea class="c-in" id="cAddr" rows="3" placeholder="경기도 양주시 …"></textarea>
        <div class="c-note">※ 주소는 회사 공용입니다. 바꾸면 내 명함에만 반영돼요. 영문(뒷면) 주소는 그대로 유지됩니다.</div>
        <button class="m-btn m-primary" id="cSave">이 내용으로 저장</button>
        <div class="m-msg" id="cFormMsg"></div>
      </div>
    </div>
  </div>

<script>
  // 소유자 기기 판별: 편집링크(?t) 또는 ?edit=1 로 한 번 열면 이 기기를 소유자로 기억.
  // 이후 그 기기에서만 사진'변경'·'내 연락처 수정'이 보임. 상대방(일반 URL)에겐 안 보임.
  (function(){
    var p=new URLSearchParams(location.search), k='sl_owner_%%SLUG%%', owner=false;
    try{
      if(p.get('t')||p.get('edit')==='1'){ localStorage.setItem(k,'1'); owner=true; }
      else if(localStorage.getItem(k)==='1'){ owner=true; }
    }catch(e){ owner=!!(p.get('t')||p.get('edit')==='1'); }
    if(owner) document.documentElement.classList.add('owner');
  })();
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
    // 공유 시 매번 고유 파라미터 → 카톡이 미리보기를 새로 생성(옛 사진 썸네일 캐시 우회). 카드는 파라미터 무시
    var SHARE=PAGE+(PAGE.indexOf('?')<0?'?':'&')+'s='+Date.now();
    if(navigator.share){
      navigator.share({title:"%%FN%% · %%COMPANY_KR%%",text:"%%FN%% 디지털 명함",url:SHARE}).catch(function(){});
    }else{
      navigator.clipboard.writeText(SHARE).then(function(){alert('명함 링크가 복사되었습니다\n'+SHARE)});
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

  // ===== 프로필 사진: 표시 + 탭하여 변경 =====
  (function(){
    var SLUG="%%SLUG%%", WORKER="%%WORKER%%";
    var urlToken=(new URLSearchParams(location.search)).get('t')||'';
    var pin='';
    var img=document.getElementById('avatarImg'), empty=document.getElementById('avatarEmpty');

    // 사진 로드: 성공→empty숨김 / 실패→정적폴백→그래도 실패면 +사진 표시
    img.addEventListener('load',function(){ empty.style.display='none'; img.style.display='block'; });
    img.addEventListener('error',function(){
      var s=img.getAttribute('data-static');
      if(s && img.src.indexOf(s)<0){ img.src=s; return; }
      img.style.display='none'; empty.style.display='flex';
    });
    // 항상 최신 사진: 열 때마다 캐시 우회(?t)로 재요청 → 사진 바꾸면 상대방도 즉시 새 사진(카톡 인앱 캐시까지 우회)
    img.src=WORKER+'/photo/'+SLUG+'?t='+Date.now();

    var modal=document.getElementById('photoModal');
    var stepPin=document.getElementById('stepPin'), stepCrop=document.getElementById('stepCrop');
    function showStep(s){ stepPin.classList.toggle('on',s==='pin'); stepCrop.classList.toggle('on',s==='crop'); }
    function openModal(){ if(!document.documentElement.classList.contains('owner')) return; modal.classList.add('on'); if(urlToken){ showStep('crop'); } else { showStep('pin'); document.getElementById('pinIn').focus(); } }
    function closeModal(){ modal.classList.remove('on'); }
    document.getElementById('avatarBtn').onclick=openModal;
    document.getElementById('mClose').onclick=closeModal;
    modal.addEventListener('click',function(e){ if(e.target===modal) closeModal(); });

    // 1) PIN
    var pinIn=document.getElementById('pinIn'), pinMsg=document.getElementById('pinMsg');
    document.getElementById('pinNext').onclick=function(){
      var v=(pinIn.value||'').trim();
      if(!/^[0-9]{4}$/.test(v)){ pinMsg.className='m-msg err'; pinMsg.textContent='숫자 4자리를 입력하세요.'; return; }
      pin=v; pinMsg.textContent=''; showStep('crop');
    };

    // 2) 크롭 편집
    var cv=document.getElementById('cropCv'), ctx=cv.getContext('2d',{willReadFrequently:true});
    var fileIn=document.getElementById('fileIn'), upBtn=document.getElementById('upBtn');
    var zoom=document.getElementById('zoom'), cropPh=document.getElementById('cropPh'), cropMsg=document.getElementById('cropMsg');
    var bmp=null, baseScale=1, ox=0, oy=0, drag=false, lx=0, ly=0;

    function loadBitmap(f){
      if(window.createImageBitmap) return createImageBitmap(f,{imageOrientation:'from-image'}).catch(function(){return createImageBitmap(f);});
      return new Promise(function(res,rej){ var im=new Image(); im.onload=function(){res(im)}; im.onerror=rej; im.src=URL.createObjectURL(f); });
    }
    function clamp(){
      var sc=baseScale*parseFloat(zoom.value), w=bmp.width*sc, h=bmp.height*sc;
      if(ox>0)ox=0; if(oy>0)oy=0; if(ox<512-w)ox=512-w; if(oy<512-h)oy=512-h;
    }
    function render(){
      if(!bmp)return; var sc=baseScale*parseFloat(zoom.value);
      ctx.clearRect(0,0,512,512); ctx.drawImage(bmp,ox,oy,bmp.width*sc,bmp.height*sc);
    }
    function isBlank(){
      try{ var dt=ctx.getImageData(0,0,512,512).data, first=null, diff=0;
        for(var i=0;i<dt.length;i+=3988){ var v=dt[i]+dt[i+1]+dt[i+2]; if(first===null)first=v; else if(Math.abs(v-first)>14)diff++; }
        return diff<2;
      }catch(e){ return false; }
    }
    fileIn.onchange=function(e){
      var f=e.target.files[0]; if(!f)return;
      cropMsg.className='m-msg'; cropMsg.textContent='불러오는 중…';
      loadBitmap(f).then(function(b){
        bmp=b; baseScale=Math.max(512/b.width,512/b.height); zoom.value=1; zoom.disabled=false;
        ox=(512-b.width*baseScale)/2; oy=(512-b.height*baseScale)*0.38; clamp(); render();
        cropPh.style.display='none';
        if(isBlank()){ cropMsg.className='m-msg err'; cropMsg.textContent='사진을 불러오지 못했어요. 다른 사진을 선택하세요.'; upBtn.disabled=true; return; }
        cropMsg.textContent=''; upBtn.disabled=false;
      }).catch(function(){ cropMsg.className='m-msg err'; cropMsg.textContent='사진 형식을 읽지 못했어요. (JPG·PNG)'; });
    };
    zoom.oninput=function(){ clamp(); render(); };
    cv.addEventListener('pointerdown',function(e){ if(!bmp)return; drag=true; lx=e.clientX; ly=e.clientY; cv.setPointerCapture(e.pointerId); });
    cv.addEventListener('pointermove',function(e){ if(!drag)return; var r=cv.getBoundingClientRect(), k=512/r.width; ox+=(e.clientX-lx)*k; oy+=(e.clientY-ly)*k; lx=e.clientX; ly=e.clientY; clamp(); render(); });
    cv.addEventListener('pointerup',function(){ drag=false; });
    cv.addEventListener('pointercancel',function(){ drag=false; });

    upBtn.onclick=function(){
      if(!bmp)return;
      if(isBlank()){ cropMsg.className='m-msg err'; cropMsg.textContent='사진이 비어 보여요. 다시 선택하세요.'; return; }
      upBtn.disabled=true; cropMsg.className='m-msg'; cropMsg.textContent='업로드 중…';
      cv.toBlob(function(blob){
        var headers={'Content-Type':'image/jpeg'};
        if(urlToken){ headers['X-Token']=urlToken; } else { headers['X-Slug']=SLUG; headers['X-Pin']=pin; }
        fetch(WORKER+'/upload',{method:'POST',headers:headers,body:blob})
          .then(function(r){return r.json()})
          .then(function(j){
            if(j.ok){
              cropMsg.className='m-msg ok'; cropMsg.textContent='✅ 변경됐어요!';
              img.style.display='block'; empty.style.display='none';
              img.src=WORKER+'/photo/'+SLUG+'?v='+Date.now();
              setTimeout(closeModal,900);
            } else {
              cropMsg.className='m-msg err'; cropMsg.textContent='⚠ '+(j.error||'실패했어요.'); upBtn.disabled=false;
              if(!urlToken){ showStep('pin'); pinMsg.className='m-msg err'; pinMsg.textContent='뒷 4자리를 다시 확인하세요.'; }
            }
          })
          .catch(function(){ cropMsg.className='m-msg err'; cropMsg.textContent='⚠ 네트워크 오류. 다시 시도하세요.'; upBtn.disabled=false; });
      },'image/jpeg',0.9);
    };
  })();

  // ===== 연락처(전화·이메일·주소) 셀프 수정 =====
  (function(){
    var SLUG="%%SLUG%%", WORKER="%%WORKER%%";
    var urlToken=(new URLSearchParams(location.search)).get('t')||'';
    var cpin='';
    var BASE=%%CONTACT_BASE%%;
    var VHEAD=%%VCARD_HEAD%%, VURL="%%VCARD_URL%%";
    var cur={phones:BASE.phones.slice(),email:BASE.email,faddr:BASE.faddr.slice(),
             vcell:BASE.vcell,vwork:BASE.vwork,vadr:BASE.vadr};

    function esc(s){return String(s).replace(/[&<>"]/g,function(c){return({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c];});}
    function bare(p){return String(p).replace(/[\s-]/g,'');}
    function intl(p){var d=String(p).trim();if(d.charAt(0)==='+')return d;d=d.replace(/\s/g,'');if(d.charAt(0)==='0')d=d.slice(1);return '+82-'+d;}
    function phoneRows(ph,useIntl){return ph.map(function(p){var v=useIntl?intl(p):p;return '<a href="tel:'+bare(v)+'" class="row"><span class="ico">☎</span>'+esc(v)+'</a>';}).join('');}
    function buildVcard(){
      var L=VHEAD.slice();
      if(cur.vcell)L.push('TEL;TYPE=CELL:'+cur.vcell);
      if(cur.vwork)L.push('TEL;TYPE=WORK,VOICE:'+cur.vwork);
      if(cur.email)L.push('EMAIL;TYPE=WORK:'+cur.email);
      if(VURL)L.push('URL:'+VURL);
      if(cur.vadr)L.push('ADR;TYPE=WORK:;;'+cur.vadr+';;;;');
      L.push('END:VCARD');return L.join('\r\n');
    }
    function setEl(id,fn){var e=document.getElementById(id);if(e)fn(e);}
    function applyOverride(ov){
      ov=ov||{};
      var hasP=ov.phones&&ov.phones.length, hasE=!!ov.email, hasA=ov.addr&&ov.addr.length;
      cur.phones=hasP?ov.phones:BASE.phones;
      cur.email =hasE?ov.email:BASE.email;
      cur.faddr =hasA?ov.addr:BASE.faddr;
      cur.vcell =hasP?intl(ov.phones[0]):BASE.vcell;
      cur.vwork =hasP?(ov.phones[1]?intl(ov.phones[1]):''):BASE.vwork;
      cur.vadr  =hasA?ov.addr.join(' '):BASE.vadr;
      setEl('fPhones',function(e){e.innerHTML=phoneRows(cur.phones,false);});
      setEl('bPhones',function(e){e.innerHTML=phoneRows(cur.phones,true);});
      setEl('fEmail',function(e){e.href='mailto:'+cur.email;e.innerHTML='<span class="ico">✉</span><span class="em">'+esc(cur.email)+'</span>';});
      setEl('bEmail',function(e){e.href='mailto:'+cur.email;e.innerHTML='<span class="ico" style="opacity:.8">✉</span>'+esc(cur.email);});
      setEl('fAddr',function(e){e.innerHTML=cur.faddr.map(esc).join('<br>');});
      setEl('actCall',function(e){if(cur.phones[0])e.href='tel:'+bare(cur.phones[0]);});
      setEl('actSms',function(e){if(cur.phones[0])e.href='sms:'+bare(cur.phones[0]);});
      setEl('actMail',function(e){e.href='mailto:'+cur.email;});
      VCARD=buildVcard();
    }

    // 로드 시 저장된 셀프수정값 반영 (없으면 기본 유지)
    fetch(WORKER+'/contact/'+encodeURIComponent(SLUG)).then(function(r){return r.ok?r.json():null;})
      .then(function(j){ if(j&&(j.phones||j.email||j.addr)) applyOverride(j); }).catch(function(){});

    var modal=document.getElementById('contactModal');
    var sPin=document.getElementById('cStepPin'), sForm=document.getElementById('cStepForm');
    function cStep(s){ sPin.classList.toggle('on',s==='pin'); sForm.classList.toggle('on',s==='form'); }
    function fillForm(){
      document.getElementById('cMobile').value=cur.phones[0]||'';
      document.getElementById('cTel').value=cur.phones[1]||'';
      document.getElementById('cEmail').value=cur.email||'';
      document.getElementById('cAddr').value=(cur.faddr||[]).join('\n');
    }
    function openC(){ modal.classList.add('on'); if(urlToken){ cStep('form'); fillForm(); } else { cStep('pin'); document.getElementById('cPinIn').focus(); } }
    function closeC(){ modal.classList.remove('on'); }
    setEl('cEditBtn',function(e){ e.onclick=openC; });
    document.getElementById('cmClose').onclick=closeC;
    modal.addEventListener('click',function(e){ if(e.target===modal) closeC(); });

    var cPinIn=document.getElementById('cPinIn'), cPinMsg=document.getElementById('cPinMsg');
    document.getElementById('cPinNext').onclick=function(){
      var v=(cPinIn.value||'').trim();
      if(!/^[0-9]{4}$/.test(v)){ cPinMsg.className='m-msg err'; cPinMsg.textContent='숫자 4자리를 입력하세요.'; return; }
      cpin=v; cPinMsg.textContent=''; cStep('form'); fillForm();
    };

    var cMsg=document.getElementById('cFormMsg');
    document.getElementById('cSave').onclick=function(){
      var mob=(document.getElementById('cMobile').value||'').trim();
      var tel=(document.getElementById('cTel').value||'').trim();
      var em=(document.getElementById('cEmail').value||'').trim();
      var ad=(document.getElementById('cAddr').value||'').split('\n').map(function(x){return x.trim();}).filter(Boolean);
      if(!mob){ cMsg.className='m-msg err'; cMsg.textContent='휴대폰 번호를 입력하세요.'; return; }
      if(!/^[0-9+\-\s]{8,20}$/.test(mob)){ cMsg.className='m-msg err'; cMsg.textContent='휴대폰 번호 형식을 확인하세요.'; return; }
      if(em && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)){ cMsg.className='m-msg err'; cMsg.textContent='이메일 형식을 확인하세요.'; return; }
      var phones=[mob]; if(tel) phones.push(tel);
      var body={phones:phones, email:em, addr:ad};
      var headers={'Content-Type':'application/json'};
      if(urlToken){ headers['X-Token']=urlToken; } else { headers['X-Slug']=SLUG; headers['X-Pin']=cpin; }
      cMsg.className='m-msg'; cMsg.textContent='저장 중…';
      fetch(WORKER+'/contact',{method:'POST',headers:headers,body:JSON.stringify(body)})
        .then(function(r){return r.json();})
        .then(function(j){
          if(j.ok){ applyOverride(j.contact||body); cMsg.className='m-msg ok'; cMsg.textContent='✅ 변경됐어요!'; setTimeout(closeC,900); }
          else { cMsg.className='m-msg err'; cMsg.textContent='⚠ '+(j.error||'실패했어요.');
                 if(!urlToken){ cStep('pin'); cPinMsg.className='m-msg err'; cPinMsg.textContent='뒷 4자리를 다시 확인하세요.'; } }
        })
        .catch(function(){ cMsg.className='m-msg err'; cMsg.textContent='⚠ 네트워크 오류. 다시 시도하세요.'; });
    };
  })();
</script>
</body>
</html>
"""
    # 연락처 셀프수정 모듈용 데이터: 표시 기본값 + vCard 고정부/편집부 분리
    vc = data["vcard"]
    contact_base = {
        "phones": f["phones"],        # 앞면(한글) 전화 — 셀프수정 기준
        "email": f["email"],
        "faddr": f["addresses"],      # 앞면(한글) 주소
        "vcell": vc.get("cell", ""),  # vCard 저장용(국제표기)
        "vwork": vc.get("work_tel", ""),
        "vadr": vc.get("adr", ""),
    }

    # 링크 미리보기(og:image): 명함형 공유이미지(_share: 이름·직함·QR, 사진 없음) → 명함처럼 보이고 절대 stale 안 됨
    # (실제 프로필 사진은 링크를 눌러 카드를 열면 항상 최신으로 보임)
    og_image = f"{base_url}/qr/{slug}_share.png"

    repl = {
        "%%OG_IMAGE%%": esc(og_image),
        "%%CONTACT_BASE%%": json.dumps(contact_base, ensure_ascii=False),
        "%%VCARD_HEAD%%": json.dumps(vcard_head_lines(vc), ensure_ascii=False),
        "%%VCARD_URL%%": esc(vc.get("url", "")),
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
        "%%WORKER%%": PHOTO_WORKER,
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
header h1 .ver{font-size:12px;font-weight:700;color:var(--brand);background:#fff;border:1px solid var(--line);border-radius:999px;padding:2px 9px;vertical-align:middle;margin-left:6px}
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
      <h1>심플라인 디지털 명함 관리 <span class="ver">%%VERSION%%</span></h1>
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
                .replace("%%VERSION%%", VERSION)
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
