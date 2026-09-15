(function (root) {
  'use strict';
  function enhance(doc, navigatorObject) {
    var codes = doc.querySelectorAll('.single-content pre > code, .entry-content pre > code');
    Array.prototype.forEach.call(codes, function (code, index) {
      var pre = code.parentNode;
      if (pre.hasAttribute('data-huntlab-code-tools')) return;
      pre.setAttribute('data-huntlab-code-tools', 'true');
      if (!pre.hasAttribute('tabindex')) pre.setAttribute('tabindex', '0');
      if (!pre.hasAttribute('role')) pre.setAttribute('role', 'region');
      if (!pre.hasAttribute('aria-label')) pre.setAttribute('aria-label', '예제 ' + (index + 1) + '. 긴 줄은 좌우 방향키로 이동할 수 있습니다.');
      var toolbar = doc.createElement('div');
      toolbar.className = 'huntlab-code-tools';
      var copy = doc.createElement('button');
      copy.type = 'button';
      copy.textContent = '복사';
      copy.setAttribute('aria-label', '예제 ' + (index + 1) + ' 복사');
      var select = doc.createElement('button');
      select.type = 'button';
      select.textContent = '전체 선택';
      select.setAttribute('aria-label', '예제 ' + (index + 1) + ' 전체 선택');
      var status = doc.createElement('span');
      status.setAttribute('role', 'status');
      status.setAttribute('aria-live', 'polite');
      status.setAttribute('aria-atomic', 'true');
      toolbar.appendChild(copy);
      toolbar.appendChild(select);
      toolbar.appendChild(status);
      pre.parentNode.insertBefore(toolbar, pre);
      var copying = false;
      var action = 0;
      copy.addEventListener('click', async function () {
        if (copying) return;
        copying = true;
        var currentAction = ++action;
        // aria-disabled keeps keyboard focus while the request is pending.
        copy.setAttribute('aria-disabled', 'true');
        status.textContent = '복사 중…';
        try {
          if (!navigatorObject.clipboard || !navigatorObject.clipboard.writeText) throw new Error('unavailable');
          // Keep exactly the rendered code, including whitespace. Never execute it.
          await navigatorObject.clipboard.writeText(code.textContent);
          if (action === currentAction) status.textContent = '복사했습니다.';
        } catch (_) {
          if (action === currentAction) status.textContent = '복사 권한을 사용할 수 없습니다. 전체 선택 후 직접 복사하세요.';
        } finally {
          copying = false;
          copy.setAttribute('aria-disabled', 'false');
        }
      });
      select.addEventListener('click', function () {
        ++action;
        try {
          var selection = doc.defaultView.getSelection();
          if (!selection) throw new Error('unavailable');
          pre.focus({preventScroll: true});
          var range = doc.createRange();
          range.selectNodeContents(code);
          selection.removeAllRanges();
          selection.addRange(range);
          status.textContent = '코드를 선택했습니다. Ctrl+C 또는 Command+C로 복사하세요. 터치 기기에서는 코드를 길게 눌러 복사 메뉴를 사용할 수 있습니다.';
        } catch (_) {
          status.textContent = '자동 선택을 사용할 수 없습니다. 마우스로 드래그하거나 터치 기기에서 코드를 길게 눌러 직접 선택하세요.';
        }
      });
    });
  }
  if (typeof module === 'object' && module.exports) module.exports = {enhance: enhance};
  else if (root.document) enhance(root.document, root.navigator);
}(typeof window === 'object' ? window : globalThis));
