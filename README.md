# Learning platform monorepo

A personal monorepo for a web app and API, used for experiments with
learning tools, code execution and course content.

## Layout

```text
apps/web/        # Next.js web app
services/api/    # FastAPI service and worker
content/         # Course and practice content
contracts/       # Schemas and interface contracts
docs/            # Design notes and decisions
infra/           # Deployment configuration
scripts/         # Development and validation tooling
tests/           # Browser and visual tests
```

## Local development

Requires Node 22–24, Python 3.12 or 3.13, and `uv`
(`python -m pip install uv==0.12.20`). From the repository root:

```powershell
npm ci
./scripts/dev/doctor.ps1
npm run dev:demo
```

Then open http://localhost:3000. Configuration goes in an untracked `.env`
file; see `.env.example`.

## Tests

```powershell
npx playwright test
npm run test:visual
```

## License

See [LICENSE](LICENSE).
