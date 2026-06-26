// 직원 디지털명함 프로필 사진 셀프 업로드 Worker
//  - GET  /u/<token>     : 직원 본인용 업로드 페이지 (폰 친화)
//  - POST /upload?t=<token> : 정사각 크롭된 jpeg 업로드 → KV 저장
//  - GET  /photo/<slug>  : 저장된 사진 서빙 (명함이 이 URL을 img src 로 사용)
// KV CARD_SELF:  token:<token> = slug   /   photo:<slug> = jpeg 바이너리

const BRAND = "#B0481F";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // 사진 서빙
    if (request.method === "GET" && path.startsWith("/photo/")) {
      const slug = decodeURIComponent(path.slice(7));
      const data = await env.CARD_SELF.get(`photo:${slug}`, "arrayBuffer");
      if (!data) return new Response("no photo", { status: 404, headers: cors() });
      return new Response(data, {
        headers: {
          "Content-Type": "image/jpeg",
          // 사진 교체 시 빨리 반영되도록 짧은 캐시
          "Cache-Control": "public, max-age=30",
          ...cors(),
        },
      });
    }

    // 업로드 페이지
    if (request.method === "GET" && path.startsWith("/u/")) {
      const token = decodeURIComponent(path.slice(3));
      const slug = await env.CARD_SELF.get(`token:${token}`);
      if (!slug) return html(pageInvalid(), 404);
      const name = await env.CARD_SELF.get(`name:${token}`);
      return html(pageUpload(token, slug, name || slug, env.CARD_BASE));
    }

    // 업로드 처리
    if (request.method === "POST" && path === "/upload") {
      const token = url.searchParams.get("t") || "";
      const slug = await env.CARD_SELF.get(`token:${token}`);
      if (!slug) return json({ ok: false, error: "유효하지 않은 링크입니다." }, 403);
      const buf = await request.arrayBuffer();
      if (!buf || buf.byteLength === 0) return json({ ok: false, error: "이미지가 비어 있습니다." }, 400);
      if (buf.byteLength > 3 * 1024 * 1024) return json({ ok: false, error: "이미지가 너무 큽니다. (3MB 이하)" }, 413);
      await env.CARD_SELF.put(`photo:${slug}`, buf, { metadata: { ct: "image/jpeg" } });
      return json({ ok: true, slug });
    }

    if (path === "/") return new Response("SIMPLELINE digital card photo service", { status: 200 });
    return new Response("not found", { status: 404 });
  },
};

function cors() {
  return { "Access-Control-Allow-Origin": "*" };
}
function html(body, status = 200) {
  return new Response(body, { status, headers: { "Content-Type": "text/html; charset=utf-8" } });
}
function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json; charset=utf-8" } });
}

function pageInvalid() {
  return `<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>링크 오류</title>
<style>body{font-family:-apple-system,'Apple SD Gothic Neo',sans-serif;background:#f1f0ee;color:#1a1a1a;
display:flex;min-height:100dvh;align-items:center;justify-content:center;text-align:center;padding:24px}
.box{max-width:340px}.t{font-size:18px;font-weight:800;margin-bottom:8px}.s{font-size:14px;color:#6b6b6b;line-height:1.6}</style>
</head><body><div class="box"><div class="t">유효하지 않은 링크예요</div>
<div class="s">링크가 만료되었거나 잘못되었습니다.<br>관리자(실장님)에게 본인 업로드 링크를 다시 요청해 주세요.</div></div></body></html>`;
}

function pageUpload(token, slug, name, base) {
  const cardUrl = `${base}/card/${slug}/`;
  return `<!DOCTYPE html><html lang="ko"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>${esc(name)} 명함 사진 등록</title>
<meta name="theme-color" content="${BRAND}">
<style>
:root{--brand:${BRAND};--ink:#1a1a1a;--muted:#6b6b6b;--line:#e5e3e0}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,'Apple SD Gothic Neo','Segoe UI',sans-serif;background:#f1f0ee;color:var(--ink);
  min-height:100dvh;display:flex;flex-direction:column;align-items:center;padding:28px 20px 40px}
.head{text-align:center;margin-bottom:22px}
.head .nm{font-size:20px;font-weight:800}
.head .sub{font-size:13px;color:var(--muted);margin-top:6px;line-height:1.5}
.preview{width:230px;height:230px;border-radius:50%;background:#e3e1de;border:4px solid #fff;
  box-shadow:0 8px 22px rgba(0,0,0,.16);overflow:hidden;display:flex;align-items:center;justify-content:center;margin-bottom:8px}
.preview canvas{width:100%;height:100%;object-fit:cover;display:none}
.preview .ph{font-size:13px;color:#9a9a9a;text-align:center;padding:0 20px;line-height:1.5}
.hint{font-size:12px;color:var(--muted);margin-bottom:22px}
.actions{width:100%;max-width:340px;display:flex;flex-direction:column;gap:10px}
.btn{display:flex;align-items:center;justify-content:center;gap:8px;border:0;border-radius:13px;
  font:inherit;font-size:16px;font-weight:700;padding:15px;cursor:pointer;text-decoration:none;color:#fff;background:var(--brand)}
.btn.ghost{background:#fff;color:var(--ink);border:1px solid var(--line)}
.btn:disabled{opacity:.45;cursor:default}
.msg{margin-top:16px;font-size:14px;font-weight:700;text-align:center;min-height:20px}
.msg.ok{color:#1a7a3c}.msg.err{color:#c0392b}
.done{display:none;margin-top:6px;text-align:center}
.done a{color:var(--brand);font-weight:700;font-size:14px;text-decoration:none}
input[type=file]{display:none}
</style></head><body>
  <div class="head">
    <div class="nm">${esc(name)} 님</div>
    <div class="sub">명함에 쓸 <b>프로필 사진</b>을 올려주세요.<br>얼굴이 가운데 오도록 자동으로 동그랗게 맞춰집니다.</div>
  </div>
  <div class="preview"><canvas id="cv" width="512" height="512"></canvas><div class="ph" id="ph">아래 버튼으로<br>사진을 선택하세요</div></div>
  <div class="hint">JPG·PNG · 정사각으로 잘려요</div>
  <div class="actions">
    <label class="btn ghost" for="file">📷 사진 선택 / 다시 찍기</label>
    <input type="file" id="file" accept="image/*">
    <button class="btn" id="up" disabled>이 사진으로 등록</button>
  </div>
  <div class="msg" id="msg"></div>
  <div class="done" id="done"><a href="${cardUrl}" target="_blank">→ 내 명함에서 확인하기</a></div>
<script>
  var TOKEN=${JSON.stringify(token)};
  var cv=document.getElementById('cv'),ctx=cv.getContext('2d');
  var fileIn=document.getElementById('file'),upBtn=document.getElementById('up');
  var ph=document.getElementById('ph'),msg=document.getElementById('msg'),done=document.getElementById('done');
  var hasImg=false;
  fileIn.onchange=function(e){
    var f=e.target.files[0];if(!f)return;
    var img=new Image();
    img.onload=function(){
      // 정사각 cover 크롭 (얼굴이 보통 위쪽이라 세로 기준 위쪽 비중)
      var s=Math.min(img.width,img.height);
      var sx=(img.width-s)/2;
      var sy=(img.height-s)*0.38;
      ctx.clearRect(0,0,512,512);
      ctx.drawImage(img,sx,sy,s,s,0,0,512,512);
      cv.style.display='block';ph.style.display='none';
      hasImg=true;upBtn.disabled=false;msg.textContent='';msg.className='msg';done.style.display='none';
      URL.revokeObjectURL(img.src);
    };
    img.src=URL.createObjectURL(f);
  };
  upBtn.onclick=function(){
    if(!hasImg)return;
    upBtn.disabled=true;msg.className='msg';msg.textContent='업로드 중…';
    cv.toBlob(function(blob){
      fetch('/upload?t='+encodeURIComponent(TOKEN),{method:'POST',headers:{'Content-Type':'image/jpeg'},body:blob})
      .then(function(r){return r.json()})
      .then(function(j){
        if(j.ok){msg.className='msg ok';msg.textContent='✅ 등록 완료! 명함에 반영됐어요.';done.style.display='block';}
        else{msg.className='msg err';msg.textContent='⚠ '+(j.error||'업로드 실패');upBtn.disabled=false;}
      })
      .catch(function(){msg.className='msg err';msg.textContent='⚠ 네트워크 오류. 다시 시도해 주세요.';upBtn.disabled=false;});
    },'image/jpeg',0.88);
  };
</script>
</body></html>`;
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
