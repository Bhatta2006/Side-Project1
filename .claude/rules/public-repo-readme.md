# Public repository: keep the README generic

Since 2026-11-13 this repository is public (it was renamed and made public to get free,
unlimited GitHub Actions minutes). The root `README.md` was deliberately rewritten as a
plain, generic monorepo readme so that search engines don't index the repository under the
product's name.

When writing code, docs or pull requests:

- Do not put the product name, branding, feature descriptions, milestone status or
  `SOCRAT_*` configuration back into the root `README.md`. Keep it to layout, local setup,
  tests and license.
- Put detailed documentation in `docs/` instead, and don't link it from the README.
- Code, env var names and package names may keep the existing name; renaming them is not
  required and should not be done as a side effect of other work.
- Keep pull request titles and descriptions focused on the change, without marketing copy
  about the product.
