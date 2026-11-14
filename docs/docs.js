/* ndhmdSuite 문서 쪽 스크립트: 전체 문서 검색, 목차 강조, 좁은 화면 목차 토글 */
(function () {
  'use strict';

  // ── 좁은 화면에서 목차 열고 닫기
  var side = document.getElementById('side');
  var tog = document.getElementById('sideToggle');
  if (side && tog) tog.addEventListener('click', function () { side.classList.toggle('open'); });

  // ── 현재 위치 강조 (scrollspy)
  var links = {};
  document.querySelectorAll('.toc a[href^="#"]').forEach(function (a) { links[a.getAttribute('href').slice(1)] = a; });
  var heads = Array.prototype.filter.call(document.querySelectorAll('.doc h1[id],.doc h2[id],.doc h3[id]'),
    function (h) { return links[h.id]; });
  var current = null;
  function setCurrent(id) {
    if (id === current) return;
    if (current && links[current]) links[current].classList.remove('on');
    current = id;
    var a = links[id];
    if (!a) return;
    a.classList.add('on');
    var det = a.closest('details');
    if (det) det.open = true;
    var box = document.querySelector('.side');
    if (box && window.innerWidth > 900) {
      var r = a.getBoundingClientRect(), b = box.getBoundingClientRect();
      if (r.top < b.top + 20 || r.bottom > b.bottom - 20) a.scrollIntoView({ block: 'center' });
    }
  }
  if (heads.length && 'IntersectionObserver' in window) {
    var onScreen = new Set();
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { e.isIntersecting ? onScreen.add(e.target) : onScreen.delete(e.target); });
      var pick = heads.filter(function (h) { return onScreen.has(h); })[0];
      if (!pick) {
        // 화면 위쪽에 이미 지나간 마지막 헤딩
        for (var i = heads.length - 1; i >= 0; i--) {
          if (heads[i].getBoundingClientRect().top < 80) { pick = heads[i]; break; }
        }
      }
      if (pick) setCurrent(pick.id);
    }, { rootMargin: '-60px 0px -70% 0px' });
    heads.forEach(function (h) { io.observe(h); });
  }

  // ── 전체 문서 검색
  var input = document.getElementById('q');
  var box = document.getElementById('results');
  if (!input || !box) return;
  var DOCS = {
    'quickstart': '빠른 시작',
    'ndhmdwriter-manual': 'ndhmdWriter 설명서',
    'ndhmd4tex-dialect-guide': 'ndhmd4tex 방언 사양서',
    'ndhmdwriter-changelog': 'ndhmdwriter 변경 이력',
    'ndhmd4tex-changelog': 'ndhmd4tex 변경 이력'
  };
  var index = null, loading = null, sel = -1, timer = null;

  function load() {
    if (index) return Promise.resolve(index);
    if (!loading) {
      loading = fetch('search-index.json').then(function (r) { return r.json(); }).then(function (j) {
        j.forEach(function (s) { s.lt = s.t.toLowerCase(); s.lx = s.x.toLowerCase(); });
        index = j; return j;
      }).catch(function () { loading = null; return []; });
    }
    return loading;
  }
  function esc(s) { return s.replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function hl(text, terms) {
    var out = esc(text);
    terms.forEach(function (t) {
      if (!t) return;
      var re = new RegExp('(' + esc(t).replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
      out = out.replace(re, '<mark>$1</mark>');
    });
    return out;
  }
  function snippet(s, terms) {
    var pos = -1;
    for (var i = 0; i < terms.length; i++) { pos = s.lx.indexOf(terms[i]); if (pos >= 0) break; }
    if (pos < 0) return s.x.slice(0, 110);
    var a = Math.max(0, pos - 40), b = Math.min(s.x.length, pos + 90);
    return (a > 0 ? '…' : '') + s.x.slice(a, b) + (b < s.x.length ? '…' : '');
  }
  function search(q) {
    var terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) { box.hidden = true; return; }
    load().then(function (idx) {
      var hits = [];
      idx.forEach(function (s) {
        var score = 0, ok = true;
        for (var i = 0; i < terms.length; i++) {
          var inT = s.lt.indexOf(terms[i]) >= 0, inX = s.lx.indexOf(terms[i]) >= 0;
          if (!inT && !inX) { ok = false; break; }
          score += inT ? 10 : 1;
        }
        if (ok) hits.push({ s: s, score: score });
      });
      hits.sort(function (a, b) { return b.score - a.score; });
      hits = hits.slice(0, 25);
      sel = -1;
      if (!hits.length) { box.innerHTML = '<div class="none">찾는 내용이 없습니다.</div>'; box.hidden = false; return; }
      box.innerHTML = hits.map(function (h) {
        var s = h.s;
        return '<a href="' + s.d + '.html#' + s.i + '"><div class="src">' + esc(DOCS[s.d] || s.d) + '</div>' +
          '<div class="ttl">' + hl(s.t, terms) + '</div>' +
          '<div class="snip">' + hl(snippet(s, terms), terms) + '</div></a>';
      }).join('');
      box.hidden = false;
    });
  }
  input.addEventListener('focus', load);
  input.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () { search(input.value.trim()); }, 120);
  });
  input.addEventListener('keydown', function (e) {
    var items = box.querySelectorAll('a');
    if (e.key === 'Escape') { box.hidden = true; input.blur(); return; }
    if (!items.length || box.hidden) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      items.forEach(function (a, i) { a.classList.toggle('sel', i === sel); });
      items[sel].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter' && sel >= 0) {
      e.preventDefault(); items[sel].click();
    }
  });
  document.addEventListener('click', function (e) {
    if (!box.contains(e.target) && e.target !== input) box.hidden = true;
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== input && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) {
      e.preventDefault(); input.focus();
    }
  });
})();
