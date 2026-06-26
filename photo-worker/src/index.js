// 직원 디지털명함 프로필 사진 셀프 업로드 Worker
//  - GET  /photo/<slug>     : 저장된 사진 서빙 (명함이 img src 로 사용)
//  - GET  /u/<token>        : 토큰 링크 → 명함 편집모드(card/<slug>/?t=token)로 redirect
//  - POST /upload           : 사진 업로드. 인증 = X-Token  또는  X-Slug + X-Pin(휴대폰 뒷4자리)
// KV CARD_SELF:  token:<token>=slug · name:<token>=이름 · pin:<slug>=뒷4자리 · photo:<slug>=jpeg

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS preflight (명함 페이지=github.io 에서 cross-origin POST)
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors() });
    }

    // 사진 서빙
    if (request.method === "GET" && path.startsWith("/photo/")) {
      const slug = decodeURIComponent(path.slice(7));
      const data = await env.CARD_SELF.get(`photo:${slug}`, "arrayBuffer");
      if (!data) return new Response("no photo", { status: 404, headers: cors() });
      return new Response(data, {
        headers: { "Content-Type": "image/jpeg", "Cache-Control": "public, max-age=30", ...cors() },
      });
    }

    // 토큰 링크 → 명함 편집모드로 redirect (크롭 UI는 명함 페이지에 통합)
    if (request.method === "GET" && path.startsWith("/u/")) {
      const token = decodeURIComponent(path.slice(3));
      const slug = await env.CARD_SELF.get(`token:${token}`);
      if (!slug) return html(pageInvalid(), 404);
      const to = `${env.CARD_BASE}/card/${slug}/?t=${encodeURIComponent(token)}`;
      return Response.redirect(to, 302);
    }

    // 업로드: X-Token 또는 X-Slug+X-Pin 인증
    if (request.method === "POST" && path === "/upload") {
      const token = request.headers.get("X-Token") || url.searchParams.get("t");
      let slug = null;
      if (token) {
        slug = await env.CARD_SELF.get(`token:${token}`);
      } else {
        const s = request.headers.get("X-Slug");
        const pin = request.headers.get("X-Pin");
        if (s && pin) {
          const real = await env.CARD_SELF.get(`pin:${s}`);
          if (real && String(pin) === String(real)) slug = s;
        }
      }
      if (!slug) return json({ ok: false, error: "본인 확인 실패 — 휴대폰 뒷 4자리를 확인해 주세요." }, 403);
      const buf = await request.arrayBuffer();
      if (!buf || buf.byteLength === 0) return json({ ok: false, error: "이미지가 비어 있습니다." }, 400);
      if (buf.byteLength > 3 * 1024 * 1024) return json({ ok: false, error: "이미지가 너무 큽니다. (3MB 이하)" }, 413);
      await env.CARD_SELF.put(`photo:${slug}`, buf, { metadata: { ct: "image/jpeg" } });
      return json({ ok: true, slug });
    }

    if (path === "/") return new Response("SIMPLELINE digital card photo service", { status: 200 });
    return new Response("not found", { status: 404, headers: cors() });
  },
};

function cors() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Token, X-Slug, X-Pin",
    "Access-Control-Max-Age": "86400",
  };
}
function html(body, status = 200) {
  return new Response(body, { status, headers: { "Content-Type": "text/html; charset=utf-8" } });
}
function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...cors() },
  });
}

function pageInvalid() {
  return `<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>링크 오류</title>
<style>body{font-family:-apple-system,'Apple SD Gothic Neo',sans-serif;background:#f1f0ee;color:#1a1a1a;
display:flex;min-height:100dvh;align-items:center;justify-content:center;text-align:center;padding:24px}
.box{max-width:340px}.t{font-size:18px;font-weight:800;margin-bottom:8px}.s{font-size:14px;color:#6b6b6b;line-height:1.6}</style>
</head><body><div class="box"><div class="t">유효하지 않은 링크예요</div>
<div class="s">링크가 만료되었거나 잘못되었습니다.<br>본인 명함을 열어 <b>사진을 탭</b>하고 휴대폰 뒷 4자리로 변경하거나,<br>관리자(실장님)에게 문의해 주세요.</div></div></body></html>`;
}
