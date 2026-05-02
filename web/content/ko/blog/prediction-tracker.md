---
title: "AI 분석 예측 트랙레코드"
description: "InvestIQs AI가 발행한 강세·약세·관망 분석 신호의 60일 후 실제 성과를 방향 정확도와 Wilson 신뢰구간으로 공개합니다."
date: 2026-04-30
ai_generated: false
draft: false
keywords:
  - "AI 예측 트랙레코드"
  - "분석 신호 검증"
  - "방향 정확도"
  - "투자 신호 성과"
  - "Wilson 신뢰구간"
  - "ETF 신호 추적"
reviewed: false
reviewedBy: "편집자 미검토 — AI 자동 발행"
analysis_confidence: "medium"
ai_models: ["claude-sonnet-4.6"]
data_source: "yfinance"
---

<div id="tracker-summary" style="background:#f0f4ff;border-radius:8px;padding:1.2em 1.5em;margin-bottom:1.5em;">
  <strong>로딩 중...</strong>
</div>

<table id="tracker-table" style="width:100%;border-collapse:collapse;font-size:0.9em;">
  <thead>
    <tr style="background:#1a1a2e;color:#fff;">
      <th style="padding:8px">날짜</th>
      <th>티커</th>
      <th>신호</th>
      <th>발행가</th>
      <th>검증가</th>
      <th>수익률</th>
      <th>결과</th>
    </tr>
  </thead>
  <tbody id="tracker-body">
    <tr><td colspan="7" style="text-align:center;padding:1em">로딩 중...</td></tr>
  </tbody>
</table>

<p style="font-size:0.8em;color:#888;margin-top:1em">
  ※ 발행 후 60일 경과 시 검증. 신호 방향(강세/약세/관망)의 정확도만 측정하며, 투자 권유가 아닙니다.
</p>

<script>
fetch('/data/prediction-accuracy.json')
  .then(r => r.json())
  .then(d => {
    const acc = d.direction_accuracy != null
      ? (d.direction_accuracy * 100).toFixed(1) + '%'
      : '—';
    document.getElementById('tracker-summary').innerHTML =
      '<strong>검증 완료:</strong> ' + (d.total_verified || 0) + '건 &nbsp;|&nbsp; ' +
      '<strong>방향 정확도:</strong> ' + acc + ' &nbsp;|&nbsp; ' +
      '<strong>검증 대기:</strong> ' + (d.pending_count || 0) + '건' +
      (d.last_updated ? ' &nbsp;|&nbsp; <span style="color:#888">업데이트: ' + d.last_updated + '</span>' : '');

    const rows = (d.records || []).map(r => {
      const ret = r.return_pct != null ? (r.return_pct > 0 ? '+' : '') + r.return_pct.toFixed(1) + '%' : '—';
      const retColor = r.return_pct > 0 ? '#16a34a' : r.return_pct < 0 ? '#dc2626' : '#555';
      const badge = r.direction_correct === 1 ? '✅' : r.direction_correct === 0 ? '❌' : '⏳';
      return '<tr style="border-bottom:1px solid #eee">' +
        '<td style="padding:6px 8px">' + (r.published_at || '') + '</td>' +
        '<td><strong>' + r.ticker + '</strong></td>' +
        '<td>' + r.signal + '</td>' +
        '<td>$' + (r.price_at_publish || '').toFixed ? Number(r.price_at_publish).toFixed(2) : r.price_at_publish + '</td>' +
        '<td>' + (r.price_at_verify ? '$' + Number(r.price_at_verify).toFixed(2) : '—') + '</td>' +
        '<td style="color:' + retColor + '">' + ret + '</td>' +
        '<td style="text-align:center">' + badge + '</td>' +
        '</tr>';
    }).join('');
    document.getElementById('tracker-body').innerHTML = rows || '<tr><td colspan="7" style="text-align:center;padding:1em;color:#888">아직 검증된 데이터가 없습니다.</td></tr>';
  })
  .catch(() => {
    document.getElementById('tracker-summary').innerHTML = '<span style="color:#888">데이터를 불러올 수 없습니다.</span>';
  });
</script>
