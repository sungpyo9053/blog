(function () {
	'use strict';

	var toc = document.querySelector('.huntlab-article-toc');
	if (!toc) return;
	var disclosure = toc.querySelector('details');
	var compact = window.matchMedia('(max-width: 767px)');
	function syncDisclosure() {
		if (!disclosure) return;
		if (compact.matches) disclosure.removeAttribute('open');
		else disclosure.setAttribute('open', '');
	}
	syncDisclosure();
	if (compact.addEventListener) compact.addEventListener('change', syncDisclosure);
	else compact.addListener(syncDisclosure);

	// Kadence clips fixed descendants inside the article. Keep the mobile TOC in
	// the reading flow, but move the desktop navigation to the viewport layer.
	var placeholder = document.createComment('huntlab-article-toc');
	var desktop = window.matchMedia('(min-width: 1360px)');
	toc.parentNode.insertBefore(placeholder, toc);

	function placeToc() {
		if (desktop.matches) document.body.appendChild(toc);
		else if (placeholder.parentNode) placeholder.parentNode.insertBefore(toc, placeholder.nextSibling);
	}

	placeToc();
	if (desktop.addEventListener) desktop.addEventListener('change', placeToc);
	else desktop.addListener(placeToc);

	var links = Array.prototype.slice.call(toc.querySelectorAll('a[href^="#"]'));
	function headingFor(link) {
		try { return document.getElementById(decodeURIComponent(link.hash.slice(1))); }
		catch (error) { return null; }
	}
	// Kadence's anchor handler uses scrollBy without CSS scroll-margin. Handle
	// only this TOC in capture, before its per-link listener can scroll again.
	toc.addEventListener('click', function (event) {
		var link = event.target.closest && event.target.closest('a[href^="#"]');
		if (!link || links.indexOf(link) === -1) return;
		var heading = headingFor(link);
		if (!heading) return;
		event.stopPropagation();
		// Leave modified/new-tab/download navigation to the browser, not Kadence.
		if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey ||
			event.shiftKey || event.altKey || link.hasAttribute('download') ||
			(link.target && link.target !== '_self')) return;
		event.preventDefault();
		var margin = parseFloat(window.getComputedStyle(heading).scrollMarginTop) || 0;
		var top = Math.max(0, window.scrollY + heading.getBoundingClientRect().top - margin);
		if (window.location.hash !== link.hash) {
			window.history.pushState(window.history.state, '', link.hash);
		}
		if (!heading.hasAttribute('tabindex')) {
			heading.setAttribute('tabindex', '-1');
			heading.addEventListener('blur', function () { heading.removeAttribute('tabindex'); }, { once: true });
		}
		heading.focus({ preventScroll: true });
		window.scrollTo({ top: top, left: window.scrollX,
			behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
	}, true);
	var headings = links.map(function (link) {
		return headingFor(link);
	}).filter(Boolean);
	if (!headings.length || !('IntersectionObserver' in window)) return;

	function activate(id) {
		links.forEach(function (link) {
			var active = link.hash === '#' + id;
			link.classList.toggle('is-active', active);
			if (active) link.setAttribute('aria-current', 'location');
			else link.removeAttribute('aria-current');
		});
	}

	var visible = new Map();
	var observer = new IntersectionObserver(function (entries) {
		entries.forEach(function (entry) {
			if (entry.isIntersecting) visible.set(entry.target.id, entry.boundingClientRect.top);
			else visible.delete(entry.target.id);
		});
		var current = Array.from(visible.entries()).sort(function (a, b) { return a[1] - b[1]; })[0];
		if (current) activate(current[0]);
	}, { rootMargin: '-18% 0px -68% 0px', threshold: [0, 1] });

	headings.forEach(function (heading) { observer.observe(heading); });
	activate(headings[0].id);
}());
