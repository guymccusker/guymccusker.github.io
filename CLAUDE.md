# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Guy McCusker's personal academic homepage. The live site is authored entirely in org-mode and built with Emacs's built-in `org-publish` — no Hugo, no ox-hugo, no JS build toolchain. Deploys to GitHub Pages via GitHub Actions. `recovered site/` and the root-level `index.html`/`css/` are legacy material (an old Hugo-generated placeholder and a recovered 2011-era site) kept for reference/content-mining — not part of the live build.

## Commands

Build the site (from repo root, needs Emacs 27+ / org-mode 9.5+):

```sh
emacs --batch -l publish.el --eval '(org-publish "site" t)'
```

The `t` forces a full rebuild, ignoring org-publish's timestamp cache — required whenever `publish.el` itself changes, since the cache only tracks `.org` source mtimes, not the config file. If running `org-publish` interactively inside an already-open Emacs rather than via this batch command, reload `publish.el` first (`M-x eval-buffer` or `M-x load-file`), or it'll keep using whatever preamble/postamble functions were already in memory.

Output goes to `public/` (gitignored, not committed). Open `public/index.html` directly to check it.

Refresh the publications list from the Bath Research Portal:

```sh
pip install beautifulsoup4
python3 scripts/fetch_publications.py \
  --feed-url "https://researchportal.bath.ac.uk/en/persons/guy-mccusker/publications/?format=rss" \
  --out content/publications.org
```

`content/publications.org` is generated output, not something to hand-edit — `.github/workflows/build.yml` regenerates it on every push and weekly on a schedule.

I (Claude) don't have Emacs available in my sandbox, so I can't run the actual build myself — changes to `publish.el` or `assets/css/style.css` need the user to rebuild and confirm before assuming they render correctly.

## Architecture

**Build pipeline** (`publish.el`): three `org-publish` sub-projects combined into `"site"`:
- `site-pages`: `content/*.org` → `public/*.html`. Deliberately `:recursive nil` — see fragment includes below.
- `site-assets`: `assets/` → `public/assets/` (CSS, images), copied as-is.
- `site-talks`: the top-level `talks/` directory (pre-existing reveal.js decks, unrelated to this build otherwise) → `public/talks/`, copied as-is.

**Fragment includes (`content/inc/`) and relative links**: `content/index.org` pulls in `content/inc/news.org` and `content/inc/talks.org` via `#+INCLUDE`. This is not a plain text splice — org rewrites relative `file:` links inside included content by prepending the fragment's directory relative to the includer, at export time. So a fragment N directories below `content/` needs exactly N `../` prefixes on any link that should resolve the way it would if written directly in `index.org` (one `../` for `content/inc/*.org`, since `inc/` is one level down). Get the count wrong and links either point at a nonexistent `public/inc/...` path (too few `../`) or one level above `public/` into the source tree (too many). `site-pages` is `:recursive nil` specifically so `content/inc/` is invisible to the publisher without needing an exclude list to maintain — new fragments there just work.

Because that `../talks/...` link text has no corresponding real path from `content/inc/`'s actual filesystem location, `content/talks` is a symlink to `../talks`, purely so `org-open-at-point` still resolves locally while editing fragments — org-publish never traverses it.

**Two-column homepage layout** (`assets/css/style.css`): `#content:has(.masthead)` turns the homepage into a CSS grid (masthead spanning the top, Contact as a sidebar, other sections in a wider main column) — scoped with `:has()` so `publications.html` (no `.masthead`) stays a plain single-column reading layout. Every top-level `* Heading` in `content/index.org` needs a slot in `grid-template-areas` *and* a `grid-area` rule keyed to its `HTML_CONTAINER_CLASS`, in both the desktop grid and the `@media (max-width: 720px)` stacked version — it's easy to add one and forget the other, which has happened before (a section silently fell out of the layout).

org exports a top-level `* Heading` as `<h2>` inside `<div class="outline-N CLASS">` — heading level is off-by-one from `outline-N` (level 1 → `outline-2`/`h2`, level 2 → `outline-3`/`h3`, etc.), with the `HTML_CONTAINER_CLASS` property value appended to that div's classes. The CSS selectors throughout `style.css` depend on this mapping.

**Publications pipeline** (`scripts/fetch_publications.py`): parses the Bath Research Portal's Pure/CRIS RSS feed — each item's `<description>` is itself an HTML-escaped citation blob — into `content/publications.org`, grouped by year, newest first. Multiple entries for the same paper (e.g. a conference version and a later journal version) are expected from Pure/CRIS feeds and are kept as-is by design, not deduplicated. The "Subscribe via RSS" link/icon on the publications page is generated by this script (`--feed-link`, defaults to the real feed URL even when testing locally against a saved `--feed-file`).

**Email obfuscation**: numeric HTML character references in a `mailto:` link (a raw `@@html: ... @@` export snippet in `content/index.org`), not JavaScript — a mild deterrent, not a strong one.

## Status

Homepage (`content/index.org`) and publications page are built and working. Not yet migrated into org: `projects.html`, `sci.html`, teaching materials, `extensional.html`, `hybrid.html` — still legacy HTML at the repo root / in `recovered site/`. No git repo has been initialized in this working copy yet.
