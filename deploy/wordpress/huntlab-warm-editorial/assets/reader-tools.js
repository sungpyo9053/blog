/* Pure checks: no network, telemetry, storage or rendering of raw input. */
(function (root) {
  'use strict';
  const positiveId = value => Number.isSafeInteger(value) && value > 0;
  function rest(input) {
    const status = Number(input.status);
    if (!Number.isInteger(status) || status < 200 || status >= 300) return {ok:false, code:'http', message:'HTTP 성공 응답이 아닙니다. 401·403은 인증과 권한, 429는 제한, 5xx는 서버 오류부터 확인하세요.'};
    if (String(input.type).split(';')[0].trim().toLowerCase() !== 'application/json') return {ok:false, code:'type', message:'JSON 응답이 아닙니다. 로그인 HTML, 프록시·WAF 차단 페이지, 리다이렉트를 확인하세요. 성공 처리하지 마세요.'};
    let body;
    try { body = JSON.parse(input.body); } catch (_) { return {ok:false, code:'json', message:'본문을 JSON으로 읽을 수 없습니다. 응답이 잘렸거나 HTML이 섞였는지 확인하세요.'}; }
    if (!body || Array.isArray(body) || !positiveId(body.id)) return {ok:false, code:'id', message:'양의 정수인 글 ID가 없습니다. 글 생성·수정 API가 반환한 객체인지 확인하세요.'};
    if (String(input.expected || '').trim() && (!positiveId(Number(input.expected)) || Number(input.expected) !== body.id)) return {ok:false, code:'identity', message:'예상한 글 ID와 다릅니다. 다른 글의 응답을 성공으로 처리하지 마세요.'};
    if (body.status !== 'publish') return {ok:false, code:'publication', message:'글 객체는 있지만 공개 발행 상태가 아닙니다. draft·pending·future 여부와 예정 시각을 확인하세요.'};
    return {ok:true, code:'valid', message:'JSON 글 객체와 publish 상태가 확인됐습니다. 다음으로 이 ID를 다시 조회하고 공개 URL의 제목·본문을 확인하세요. 이 검사만으로 실제 사이트 발행을 보장하지 않습니다.'};
  }
  function retry(input) {
    const value = String(input.retry).trim(), nowText = String(input.now).trim();
    if (!/(Z|[+-]\d{2}:\d{2})$/i.test(nowText) || !Number.isFinite(Date.parse(nowText))) return {ok:false, code:'clock', message:'현재 시각에 시간대를 포함하세요. 예: 2026-09-15T12:00:00Z'};
    let seconds;
    if (/^\d+$/.test(value)) seconds = Number(value);
    else if (/^(Mon|Tue|Wed|Thu|Fri|Sat|Sun), \d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2} GMT$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toUTCString() === value) seconds = Math.max(0, Math.ceil((Date.parse(value) - Date.parse(nowText)) / 1000));
    else return {ok:false, code:'invalid', message:'음이 아닌 정수 초 또는 GMT HTTP 날짜를 입력하세요. 잘못된 값은 그대로 재시도 간격으로 쓰지 마세요.'};
    if (!Number.isSafeInteger(seconds)) return {ok:false, code:'range', message:'대기 시간이 계산 가능한 범위를 벗어났습니다.'};
    return {ok:true, code:'delay', seconds, message:`입력 시각 기준 최소 ${seconds}초 대기입니다. 운영 작업의 시간 제한과 최대 재시도 횟수를 별도로 두세요. POST 재전송 전에는 중복 여부를 확인하세요.`};
  }
  function inventory(input) {
    const total = Number(input.total), perPage = Number(input.perPage);
    if (!String(input.total).trim() || !Number.isSafeInteger(total) || total < 0 || !Number.isInteger(perPage) || perPage < 1 || perPage > 100) return {ok:false, code:'input', message:'전체 건수는 0 이상, 페이지당 항목 수는 1~100 정수로 입력하세요.'};
    const tokens = String(input.ids).trim().split(/[\s,]+/).filter(Boolean);
    if (tokens.some(x => !/^\d+$/.test(x) || !positiveId(Number(x)))) return {ok:false, code:'ids', message:'글 ID에는 양의 정수만 입력하세요.'};
    const unique = new Set(tokens.map(Number)), duplicates = tokens.length - unique.size, pages = Math.ceil(total / perPage);
    const ok = unique.size === total && duplicates === 0;
    return {ok, code:ok ? 'count_matches' : 'incomplete', unique:unique.size, duplicates, pages, message:`예상 ${pages}페이지 / 전체 ${total}건 / 고유 ID ${unique.size}건 / 중복 ${duplicates}건. ` + (ok ? '건수가 일치합니다. 수집 도중 글이 바뀌었거나 서로 다른 조회 조건을 섞었다면 같은 건수여도 완전한 목록이라고 단정할 수 없습니다.' : '목록이 일치하지 않습니다. 페이지 누락, 중복 응답, 상태·검색 조건과 수집 중 변경 여부를 확인하세요.')};
  }
  const api = {rest, retry, inventory};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof document === 'undefined') return;
  document.querySelectorAll('[data-huntlab-diagnostics]').forEach(container => {
    // Isolate these diagnostic jumps from Kadence's CSS-margin-blind handler.
    const jumps = container.querySelector('.huntlab-tool-jumps');
    if (jumps && jumps.addEventListener) jumps.addEventListener('click', event => {
      const link = event.target.closest && event.target.closest('a[href^="#"]');
      if (!link || !jumps.contains(link)) return;
      let heading;
      try { heading = document.getElementById(decodeURIComponent(link.hash.slice(1))); }
      catch (_) { return; }
      if (!heading || !container.contains(heading)) return;
      event.stopPropagation();
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey ||
          event.shiftKey || event.altKey || link.hasAttribute('download') ||
          (link.target && link.target !== '_self')) return;
      event.preventDefault();
      const view = document.defaultView;
      const margin = parseFloat(view.getComputedStyle(heading).scrollMarginTop) || 0;
      const top = Math.max(0, view.scrollY + heading.getBoundingClientRect().top - margin);
      if (view.location.hash !== link.hash) view.history.pushState(view.history.state, '', link.hash);
      if (!heading.hasAttribute('tabindex')) {
        heading.setAttribute('tabindex', '-1');
        heading.addEventListener('blur', () => heading.removeAttribute('tabindex'), {once:true});
      }
      heading.focus({preventScroll:true});
      view.scrollTo({top, left:view.scrollX,
        behavior:view.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
    }, true);
    const now = container.querySelector('[name="now"]');
    now.value = new Date().toISOString();
    container.querySelectorAll('form[data-check]').forEach(form => form.addEventListener('submit', event => {
      event.preventDefault();
      const result = api[form.dataset.check](Object.fromEntries(new FormData(form)));
      const output = form.querySelector('[role="status"]');
      output.textContent = result.message;
      output.dataset.ok = String(result.ok);
    }));
    // A verdict belongs to the submitted values, not later edits. Leaving a
    // green publish verdict beside a newly edited draft response is misleading.
    container.querySelectorAll('form[data-check]').forEach(form => form.addEventListener('input', () => {
      const output = form.querySelector('[role="status"]');
      if (output.textContent) {
        output.textContent = '입력이 바뀌었습니다. 다시 검사하세요.';
        delete output.dataset.ok;
      }
    }));
    container.querySelectorAll('[data-example]').forEach(button => button.addEventListener('click', () => {
      const form = button.closest('form'), html = button.dataset.example === 'html';
      form.elements.status.value = html ? '200' : '201';
      form.elements.type.value = html ? 'text/html; charset=UTF-8' : 'application/json';
      form.elements.expected.value = '';
      form.elements.body.value = html ? '<html><body>Login required</body></html>' : '{"id":123,"status":"publish"}';
      form.requestSubmit();
    }));
    container.querySelector('[data-clear]').addEventListener('click', () => {
      container.querySelectorAll('input,textarea').forEach(field => { field.value = ''; });
      container.querySelectorAll('[role="status"]').forEach(output => { output.textContent = ''; delete output.dataset.ok; });
      now.value = new Date().toISOString();
    });
  });
})(typeof globalThis === 'undefined' ? this : globalThis);
