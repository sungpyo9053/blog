// ko.html의 계산기 <script>를 그대로 뽑아 node에서 실행하는 검산
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'ko.html'), 'utf8');
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
if (src.indexOf('&') >= 0) throw new Error('& found in script');
if (src.indexOf('<') >= 0) throw new Error('< found in script');
if (/\n\s*\n/.test(src)) throw new Error('blank line in script');
const ld = html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1];
if (/[&<]/.test(ld)) throw new Error('& or < in JSON-LD');
const faq = JSON.parse(ld); assert.ok(faq.mainEntity.length >= 6); console.log('PASS JSON-LD 파싱, 질문', faq.mainEntity.length, '개');
global.window = {};
global.document = { getElementById: () => null };
eval(src);
const G = window.hxGrade, I = window.hxInfo;
const gc = [
  ['심화 80 -> 1급', 'deep', 80, { grade: 1 }], ['심화 79 -> 2급', 'deep', 79, { grade: 2 }],
  ['심화 70 -> 2급', 'deep', 70, { grade: 2 }], ['심화 69 -> 3급', 'deep', 69, { grade: 3 }],
  ['심화 60 -> 3급', 'deep', 60, { grade: 3 }], ['심화 59 -> 없음, 1점 부족', 'deep', 59, { grade: 0, need: 1 }],
  ['심화 100 -> 1급', 'deep', 100, { grade: 1 }],
  ['기본 85 -> 4급', 'basic', 85, { grade: 4 }], ['기본 72 -> 5급', 'basic', 72, { grade: 5 }],
  ['기본 60 -> 6급', 'basic', 60, { grade: 6 }], ['기본 40 -> 없음 20점 부족', 'basic', 40, { grade: 0, need: 20 }],
  ['101 오류', 'deep', 101, { ok: false }], ['음수 오류', 'deep', -1, { ok: false }], ['빈칸 오류', 'basic', NaN, { ok: false }],
];
for (const [name, t, s, exp] of gc) { const r = G(t, s); for (const k of Object.keys(exp)) assert.strictEqual(r[k], exp[k], name + ' ' + k + '=' + r[k]); console.log('PASS', name, JSON.stringify(r)); }
const ic = [
  ['확인일 10-29, 81회: 접수 시작까지 5일, 시험 D-30', '81', '2026-10-29', r => r.apply.state === 'before' && r.apply.days === 5 && r.exam.days === 30 && r.result.days === 43],
  ['발행일 11-12, 81회: 정기 종료, 취소좌석 진행 중 1일, D-16', '81', '2026-11-12', r => r.apply.state === 'past' && r.extra.state === 'open' && r.extra.days === 1 && r.exam.days === 16],
  ['11-10 마감일: 정기 진행 중 0일', '81', '2026-11-10', r => r.apply.state === 'open' && r.apply.days === 0 && r.extra.state === 'before' && r.extra.days === 1],
  ['11-28 시험 당일', '81', '2026-11-28', r => r.exam.state === 'today' && r.result.days === 13],
  ['12-12 81회 발표 하루 지남', '81', '2026-12-12', r => r.result.state === 'past' && r.result.days === 1],
  ['80회 10-29: 결과 발표 D-1', '80', '2026-10-29', r => r.result.state === 'before' && r.result.days === 1 && r.exam.state === 'past' && r.exam.days === 12],
  ['77회 2026-01-01: 접수 시작까지 5일', '77', '2026-01-01', r => r.apply.days === 5 && r.kind === '심화·기본'],
  ['79회 8-9 일요일 당일', '79', '2026-08-09', r => r.exam.state === 'today'],
];
for (const [name, no, d, f] of ic) { const r = I(no, d); assert.ok(f(r), name + ' ' + JSON.stringify(r)); console.log('PASS', name, JSON.stringify(r)); }
// 본문 일정표와 스크립트 배열 대조
const rows = [...html.matchAll(/<tr><td>제(\d\d)회<\/td><td>(\d+)\.(\d+)\.\(.\)<\/td><td>[^<]+<\/td><td>(\d+)\.(\d+)\.~(\d+)\.(\d+)\.<\/td><td>(\d+)\.(\d+)\.~(\d+)\.(\d+)\.<\/td><td>(\d+)\.(\d+)\.\(.\)<\/td><\/tr>/g)];
assert.strictEqual(rows.length, 5);
const iso = (m, d) => "'2026-" + m.padStart(2, '0') + '-' + d.padStart(2, '0') + "'";
for (const m of rows) {
  const line = src.match(new RegExp(m[1] + ':\\[([^\\]]*)\\]'))[1];
  const want = [iso(m[2], m[3]), iso(m[4], m[5]), iso(m[6], m[7]), iso(m[8], m[9]), iso(m[10], m[11]), iso(m[12], m[13])].join(',');
  assert.ok(line.startsWith(want), '제' + m[1] + '회 불일치 ' + line + ' vs ' + want);
}
console.log('PASS 본문 2026 일정표 5회차 = 스크립트 배열(시험일·접수·취소좌석·발표)');
// UI 기본값 렌더(기준일 2026-11-12, 81회, 심화 72점)
const vals = { 'hx-round': '81', 'hx-date': '2026-11-12', 'hx-type': 'deep', 'hx-score': '72' };
const outs = { 'hx-out1': [], 'hx-out2': [] };
const mk = id => ({ value: vals[id], style: {}, addEventListener() {}, set innerHTML(v) { if (outs[id]) outs[id].length = 0; }, appendChild(p) { outs[id].push(p.textContent); } });
const els = {}; ['hx-out1', 'hx-out2', 'hx-today', ...Object.keys(vals)].forEach(id => els[id] = mk(id));
global.document = { getElementById: id => els[id], createElement: () => ({ style: {} }) };
eval(src);
console.log('UI 출력1:', outs['hx-out1'].join(' | '));
console.log('UI 출력2:', outs['hx-out2'].join(' | '));
assert.ok(outs['hx-out1'].join().includes('16일 남음'));
assert.ok(outs['hx-out2'].join().includes('2급'));
console.log('ALL PASS');
