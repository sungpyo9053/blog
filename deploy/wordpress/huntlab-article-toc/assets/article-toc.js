(function () {
	'use strict';

	var toc = document.querySelector('.huntlab-article-toc');
	if (!toc) return;

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
	var headings = links.map(function (link) {
		return document.getElementById(decodeURIComponent(link.hash.slice(1)));
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
