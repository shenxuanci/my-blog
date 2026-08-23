# News serif font subset

`news-serif-sc.txt` is the **first-paint hot set** for the news page's self-hosted Noto Serif SC 700 webfont — printable ASCII, common full-width punctuation, and every Han character that appears in the committed news UI and report corpus.

It is **not** a coverage contract. `tools/generate-news-font.cjs` runs with `subsetRemainChars`, so every glyph outside this list stays available in auto-chunked tail files and is fetched on demand through `unicode-range`. Nothing falls back to the system serif. The list only decides how many chunks a typical page has to download, so a growing corpus never causes missing glyphs and the list does **not** need periodic regeneration.

Regenerate it (optional, to re-tune first-paint bytes) from a fixed repository state:

```powershell
node tools/font-subsets/build-news-serif-chars.cjs
```

Output is sorted by code point, so the same repository state always produces the same bytes.

**Regenerating this list without regenerating the font is a trap.** The list and the WOFF2 chunks are two halves of one artifact: rewrite the list against a newer corpus and it will name characters that the shipped chunks distribute differently, so first-paint bytes shift even though no font file changed. Measured on 2026-08-07, regenerating against the then-current corpus (2605 → 2687 characters) moved the first-paint set from 38 chunks to 72. If you regenerate the list, regenerate the font in the same commit — or don't regenerate at all, which is the normal case, since coverage never depends on this list.

For the same reason the cold-transfer guardrail in `news-pipeline/tests/test_news_frontend.mjs` deliberately does **not** read this file; it partitions chunks using a hardcoded copy of the page's own constant text. Don't "simplify" it to read `news-serif-sc.txt` — that reintroduces a test that fails when this list drifts while the font is byte-identical. See `docs/adr/0013-serif-font-full-coverage-chunking.md`.

The webfont itself is generated with `cn-font-split@7.4.3` through `tools/generate-news-font.cjs`. Keep only the resulting WOFF2 chunks and `result.css` beside `OFL.txt`; the source OTF, `index.proto`, previews, and temporary dependencies are build inputs and must not be committed. The current regeneration procedure is in `docs/news-maintenance.md`; the font version, coverage strategy, and cold-load budget rationale are in `docs/adr/0013-serif-font-full-coverage-chunking.md`.
