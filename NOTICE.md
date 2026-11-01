# Notices

> **Draft. Requires legal review before publication.** Prepared from the files in this
> repository on 2026-10-16; it does not replace a full dependency license audit.

Socrat-original material is covered by [LICENSE](LICENSE). This file lists third-party
material that ships with Socrat or that Socrat depends on.

## Fonts shipped with the web app

| Font | License | Where |
|---|---|---|
| JetBrains Mono | SIL Open Font License 1.1 | `apps/web/src/fonts/jetbrains-mono-latin-wght.woff2`, license text `apps/web/src/fonts/JetBrainsMono-OFL.txt` |
| Delicious Handrawn (handwritten notes) | SIL Open Font License 1.1 | `apps/web/src/fonts/delicious-handrawn-latin-400.woff2`, license text `apps/web/src/fonts/DeliciousHandrawn-OFL.txt` |
| Geist | SIL Open Font License 1.1 | npm package `geist`, license text `node_modules/geist/LICENSE.txt`; vendored copy for visual explainers `apps/web/src/fonts/geist-wght.woff2`, license text `apps/web/src/fonts/Geist-OFL.txt` |

## Software dependencies

Python dependencies are pinned in `uv.lock` (exported to `requirements.lock.txt`) and
JavaScript dependencies in `package-lock.json`. Each package is distributed under its own
license, recorded in its package metadata. A complete dependency license report has not
yet been produced; generating one (for example with `pip-licenses` and `license-checker`)
is part of the legal review.

## External problem and resource metadata

`content/practice/` stores titles, links, tags and difficulty for problems on LeetCode,
Codeforces and CSES, and links to TheAlgorithms implementations. Problem statements,
editorials and solutions are not stored. Codeforces data comes from its public API.
Socrat links to these sites; their content belongs to their owners.

Learning resources linked from lessons are listed in [ATTRIBUTION.md](ATTRIBUTION.md).
