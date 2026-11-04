/*
 * Switch the reveal.js theme from inside a running presentation.
 *
 *   T          cycle to the next theme
 *   ?theme=X   in the URL picks a theme on load (e.g. 01logic.html?theme=black)
 *
 * On dark themes, images are inverted and their (formerly white) background
 * made transparent, so black-on-white TikZ drawings show up light-on-dark; give an image class "no-invert" (org: #+ATTR_HTML:
 * :class no-invert) to leave it alone, e.g. for photos.
 *
 * The last choice is remembered per browser. Include it from the org preamble:
 *   #+HTML_HEAD_EXTRA: <script src="theme-switcher.js" defer></script>
 */
(function () {
  // "bath" is the white theme with bath.css layered on top; the others are
  // stock reveal.js themes with bath.css switched off. "dark" themes get
  // their images inverted.
  var THEMES = [
    { name: "bath",      base: "white",     bath: true  },
    { name: "white",     base: "white",     bath: false },
    { name: "simple",    base: "simple",    bath: false },
    { name: "beige",     base: "beige",     bath: false },
    { name: "solarized", base: "solarized", bath: false },
    { name: "black",     base: "black",     bath: false, dark: true },
    { name: "night",     base: "night",     bath: false, dark: true },
    { name: "moon",      base: "moon",      bath: false, dark: true }
  ];
  var STORAGE_KEY = "reveal-theme";

  var themeLink = document.getElementById("theme");
  if (!themeLink) return;
  var themeDir = themeLink.getAttribute("href").replace(/[^\/]*\.css$/, "");
  var bathLink = document.querySelector('link[href$="bath.css"]');
  var current = 0;

  // After inverting, make dark pixels transparent in proportion to their
  // brightness (alpha = 3 * luminance + alpha - 1), so a former white
  // background vanishes into the slide colour. A CSS blend mode can't do this
  // because reveal paints slide backgrounds outside the slides' stacking context.
  var svgNS = "http://www.w3.org/2000/svg";
  var svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("aria-hidden", "true");
  svg.style.cssText = "position:absolute;width:0;height:0";
  svg.innerHTML =
    '<filter id="theme-dark-knockout" color-interpolation-filters="sRGB">' +
    '<feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0' +
    '  0.6375 2.1462 0.2163 1 -1"/></filter>';
  document.body.appendChild(svg);

  var style = document.createElement("style");
  style.textContent =
    "html.theme-dark .reveal .slides img:not(.no-invert) {" +
    " filter: invert(1) hue-rotate(180deg) url(#theme-dark-knockout); }";
  document.head.appendChild(style);

  function indexOf(name) {
    for (var i = 0; i < THEMES.length; i++) {
      if (THEMES[i].name === name) return i;
    }
    return -1;
  }

  function apply(i, announce) {
    current = (i + THEMES.length) % THEMES.length;
    var theme = THEMES[current];
    themeLink.onload = function () { Reveal.layout(); };
    themeLink.setAttribute("href", themeDir + theme.base + ".css");
    if (bathLink) bathLink.disabled = !theme.bath;
    document.documentElement.classList.toggle("theme-dark", !!theme.dark);
    // The preamble's inline "body {color: black; background: white}" would
    // otherwise show through around the slides on dark themes.
    document.body.style.background = "var(--r-background-color, var(--background-color))";
    try { localStorage.setItem(STORAGE_KEY, theme.name); } catch (e) {}
    if (announce) toast(theme.name);
  }

  var toastEl, toastTimer;
  function toast(text) {
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.style.cssText =
        "position:fixed;top:12px;right:12px;z-index:1000;padding:6px 12px;" +
        "font:14px sans-serif;color:#fff;background:rgba(0,0,0,.7);" +
        "border-radius:4px;pointer-events:none;transition:opacity .3s";
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = "Theme: " + text;
    toastEl.style.opacity = "1";
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.style.opacity = "0"; }, 1500);
  }

  var initial = new URLSearchParams(location.search).get("theme");
  if (initial === null) {
    try { initial = localStorage.getItem(STORAGE_KEY); } catch (e) {}
  }
  if (indexOf(initial) >= 0) apply(indexOf(initial), false);

  Reveal.addKeyBinding({ keyCode: 84, key: "T", description: "Cycle theme" }, function () {
    apply(current + 1, true);
  });
})();
