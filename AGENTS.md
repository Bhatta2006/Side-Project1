# Socrat: instructions for any coding agent

Start with `docs/implementation/HANDOFF.md`. It holds the owner's rules, the environment quirks that
cost time on this machine (Windows, CRLF, running tests from the repo root), what has been built,
what has not been verified, the remaining work in order, and how to commit and push.

Then read `docs/implementation/universal-engine-plan.md` (strategy, phase table, progress log).

Short version of the rules:
- Work on branch `feat/universal-engine`. Push with `git push origin feat/universal-engine`.
  Never force-push, never push to `main`, never merge `main` into the branch.
- Stage specific paths only; never commit keys, `.env` files or `apps/web/next-env.d.ts`.
- Models explain; deterministic code verifies. New features default off behind a flag, migrations are
  additive with a tested downgrade.
- Say what is not verified. Ask the owner for keys, reviewers and legal decisions instead of guessing.
- Next.js in `apps/web` is a newer major version with breaking changes: read
  `apps/web/AGENTS.md` and `node_modules/next/dist/docs/` before writing web code.
