export async function onRequest(context) {
  const url = new URL(context.request.url);
  const code = url.searchParams.get('code');
  const error = url.searchParams.get('error');

  if (error) {
    return new Response(`<h1>OAuth Error: ${error}</h1>`, {
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
      status: 400
    });
  }

  if (!code) {
    return new Response('<h1>Missing code parameter</h1>', {
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
      status: 400
    });
  }

  // Show code on page so user can use it manually if needed
  const html = `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>TikTok OAuth Callback</title>
<style>
body{font-family:system-ui,sans-serif;background:#0f172a;color:#fff;padding:40px;max-width:720px;margin:0 auto;line-height:1.6}
h1{color:#22c55e}
.code{background:#1e293b;padding:16px;border-radius:8px;font-family:monospace;word-break:break-all;font-size:14px;margin:16px 0;border:1px solid #334155}
button{background:#0ea5e9;color:#fff;border:0;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:14px}
</style>
</head>
<body>
<h1>TikTok OAuth Code 수신</h1>
<p>이 코드를 복사해서 자동화 시스템에 입력하세요:</p>
<div class="code" id="code">${code}</div>
<button onclick="navigator.clipboard.writeText(document.getElementById('code').textContent)">복사</button>
<p style="color:#94a3b8;margin-top:24px">또는 <code>callback.investiqs.net</code> tunnel이 작동 중이면 자동으로 처리됩니다.</p>
</body>
</html>`;

  return new Response(html, {
    headers: { 'Content-Type': 'text/html; charset=utf-8' }
  });
}
