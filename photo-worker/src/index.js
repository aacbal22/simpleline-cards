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
        // 사진 바꾸면 상대방도 새로고침 시 즉시 최신 보이게 — 캐시 금지(아바타는 작아 부담 적음)
        headers: { "Content-Type": "image/jpeg", "Cache-Control": "no-cache, no-store, must-revalidate", ...cors() },
      });
    }

    // 연락처 오버라이드 조회 (명함이 로드 시 fetch → 전화/이메일/주소 덮어쓰기)
    if (request.method === "GET" && path.startsWith("/contact/")) {
      const slug = decodeURIComponent(path.slice(9));
      const raw = await env.CARD_SELF.get(`contact:${slug}`);
      return new Response(raw || "{}", {
        headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=20", ...cors() },
      });
    }

    // 연락처 셀프 수정 저장 (전화·이메일·한글주소만. 직책·부서·이름은 관리자 전용 → 받지 않음)
    if (request.method === "POST" && path === "/contact") {
      const slug = await authSlug(request, env, url);
      if (!slug) return json({ ok: false, error: "본인 확인 실패 — 휴대폰 뒷 4자리를 확인해 주세요." }, 403);
      let body;
      try { body = await request.json(); } catch (e) { return json({ ok: false, error: "형식 오류" }, 400); }
      const out = {};
      // 전화: 최대 2개, 각 숫자/하이픈/공백/+ 만, 8~20자
      if (Array.isArray(body.phones)) {
        const ph = body.phones.map((p) => String(p || "").trim()).filter(Boolean)
          .filter((p) => /^[0-9+\-\s]{8,20}$/.test(p)).slice(0, 2);
        if (ph.length) out.phones = ph;
      }
      // 이메일: @ 포함, 100자 이하
      if (body.email != null) {
        const em = String(body.email).trim();
        if (em && em.length <= 100 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)) out.email = em;
        else if (em) return json({ ok: false, error: "이메일 형식을 확인하세요." }, 400);
      }
      // 한글 주소: 최대 3줄, 각 120자 이하
      if (Array.isArray(body.addr)) {
        const ad = body.addr.map((a) => String(a || "").trim()).filter(Boolean)
          .map((a) => a.slice(0, 120)).slice(0, 3);
        if (ad.length) out.addr = ad;
      }
      if (!Object.keys(out).length) return json({ ok: false, error: "변경할 내용이 없습니다." }, 400);
      out._at = "self"; // 출처 표시(동기화 스크립트용)
      await env.CARD_SELF.put(`contact:${slug}`, JSON.stringify(out));
      return json({ ok: true, slug, contact: out });
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
      const slug = await authSlug(request, env, url);
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

// 인증: X-Token(편집링크) 또는 X-Slug+X-Pin(휴대폰 뒷4자리) → slug 반환, 실패 시 null
async function authSlug(request, env, url) {
  const token = request.headers.get("X-Token") || url.searchParams.get("t");
  if (token) return await env.CARD_SELF.get(`token:${token}`);
  const s = request.headers.get("X-Slug");
  const pin = request.headers.get("X-Pin");
  if (s && pin) {
    const real = await env.CARD_SELF.get(`pin:${s}`);
    if (real && String(pin) === String(real)) return s;
  }
  return null;
}

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
