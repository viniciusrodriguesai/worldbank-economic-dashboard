# Continuous Integration Workflows

This directory contains the repository's GitHub Actions automation. Workflow definitions are executable project infrastructure: review changes here with the same care as application code.

The current workflow is `ci.yml`.

## What the workflow protects

Continuous integration verifies both application layers on every change targeting `main`:

- the FastAPI backend runs Ruff, Bandit, pip-audit, Pytest, and the coverage gate; and
- the React frontend performs a clean install, dependency audit, Oxlint, Vitest
  coverage, strict TypeScript validation, and a Vite production build.

The backend and frontend jobs run independently. A failure in one does not hide the result of the other, and GitHub can execute them concurrently.

## Triggers

`ci.yml` runs for:

| Event | Scope | Purpose |
| --- | --- | --- |
| `push` | Branch `main` | Verifies the exact revision published to the primary branch. |
| `pull_request` | Pull requests targeting `main` | Detects integration problems before a proposed change is merged. |

Documentation-only commits currently run the full pipeline. This is deliberate: it keeps the workflow simple and confirms that every published revision remains buildable.

## Permissions

The workflow declares:

```yaml
permissions:
  contents: read
```

Jobs can read the checked-out repository but do not receive write access to contents, pull requests, packages, deployments, or other GitHub resources. No repository secrets are required by the current test and build process.

Preserve least privilege. If a future job needs another permission, grant only the specific capability and access level required, preferably at job scope.

## Backend job

The `backend` job runs on GitHub's current Ubuntu runner and uses Python 3.11.

| Step | Action |
| --- | --- |
| Checkout | Retrieves the revision with credentials disabled and a reviewed action SHA. |
| Python setup | Installs Python 3.11 through a reviewed action SHA. |
| Dependency cache | Keys pip's cache from both backend requirement files. |
| Installation | Installs `backend/requirements-dev.txt`, which includes runtime and test tooling. |
| Static/security checks | Runs Ruff, Bandit, and pip-audit against production code/dependencies. |
| Verification | Runs `python -m pytest` with the enforced coverage threshold. |

Pytest configuration lives in the root `pyproject.toml`. Running from the repository root is important because tests import the `backend` package and coverage settings use repository-relative paths.

Local equivalent:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt
ruff check backend
bandit -q -r backend -x backend\tests
pip-audit -r backend\requirements.txt
python -m pytest
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

## Frontend job

The `frontend` job runs on the same Ubuntu runner family with Node.js 22.15.0. Its default working directory is `frontend/`.

| Step | Action |
| --- | --- |
| Checkout | Retrieves the revision with credentials disabled and a reviewed action SHA. |
| Node setup | Installs the pinned Node.js version through a reviewed action SHA. |
| Dependency cache | Keys npm's download cache from `frontend/package-lock.json`. |
| Installation | Runs `npm ci` for a clean, lockfile-enforced install. |
| Security/lint | Runs `npm audit --audit-level=high` and `npm run lint`. |
| Tests | Runs Vitest through `npm run test:coverage` and enforces thresholds. |
| Production build | Runs `npm run build`, which type-checks before Vite bundling. |

Local equivalent:

```powershell
Set-Location frontend
npm ci
npm audit --audit-level=high
npm run lint
npm run test:coverage
npm run build
```

Use `npm ci`, rather than `npm install`, when reproducing a CI dependency issue because it follows the committed lockfile exactly and rejects manifest drift.

## Cache behavior

The setup actions cache package-manager download data, not installed project directories:

- pip uses the backend requirement files as cache dependency inputs; and
- npm uses `frontend/package-lock.json`.

`node_modules/`, virtual environments, test coverage, and production artifacts are not committed or restored as source. A cache miss should make a run slower, not change its result.

When dependency declarations change, update the corresponding lock or requirement file in the same commit. The next run will compute the appropriate cache key automatically.

## Reading a failed run

Start with the first failing step in the affected job:

1. Open the run from the repository's **Actions** tab.
2. Select either **Backend tests** or **Frontend tests and build**.
3. Expand the first red step, not only the final job summary.
4. Reproduce the exact command locally from the documented working directory.
5. Fix the underlying code, dependency, test, or workflow issue.
6. Run both the focused check and the complete layer verification.
7. Commit and push the fix; do not manually edit generated logs or artifacts.

Typical categories:

| Failure | First checks |
| --- | --- |
| Dependency installation | Manifest syntax, lockfile consistency, package availability, and runtime version compatibility. |
| Backend import or collection | Working directory, package paths, requirement coverage, and pytest configuration. |
| Backend assertion | API contract, fixtures, mocked World Bank responses, and reported traceback. |
| Frontend assertion | Accessible queries, async waits, API mocks, and changed visible behavior. |
| TypeScript build | Shared interfaces, strict null handling, third-party declarations, and unused imports. |
| Vite build | Entry points, environment variables, dynamic imports, and dependency compatibility. |

## Changing runtime versions

Runtime upgrades are intentional compatibility changes.

For Python:

1. update `python-version` in `ci.yml`;
2. recreate a local environment with that version;
3. install both requirement files from scratch; and
4. run the complete backend suite.

For Node.js:

1. update `node-version` in `ci.yml`;
2. verify the engine requirements of Vite, Vitest, jsdom, and React tooling;
3. run `npm ci`, `npm test`, and `npm run build`; and
4. update developer documentation if the minimum supported version changes.

Pin exact language runtime versions when reproducibility matters. Action dependencies
are pinned to reviewed full commit SHAs and monitored by Dependabot.

## Modifying the workflow

Before publishing a workflow change:

- validate YAML indentation and expression syntax;
- keep third-party actions pinned to trusted, explicit versions;
- maintain `contents: read` unless a documented feature requires more;
- use `npm ci` for lockfile reproducibility;
- keep test commands identical to documented local commands;
- update cache dependency paths when manifests move;
- avoid printing environment values or secrets;
- ensure each job name describes the protection it provides; and
- update this README when behavior, versions, triggers, or permissions change.

GitHub Actions itself is the authoritative validation environment. Local YAML checks are useful, but a successful run on the published commit is the final confirmation.

## Adding another workflow

Create a separate YAML file when automation has a distinct purpose, permission model, or trigger, such as deployment or scheduled dependency maintenance. Keep routine backend and frontend quality gates together in `ci.yml`.

For a new workflow:

1. choose a descriptive filename and top-level `name`;
2. constrain events and branches;
3. declare minimal permissions;
4. pin actions and language runtimes;
5. make working directories explicit;
6. add timeouts or concurrency controls when appropriate;
7. document required secrets without exposing their values; and
8. add the workflow to this guide.

## Related documentation

- [`../../README.md`](../../README.md) is the repository-wide setup and operations guide.
- [`../../backend/README.md`](../../backend/README.md) documents backend verification.
- [`../../frontend/README.md`](../../frontend/README.md) documents frontend verification.
- [`ci.yml`](ci.yml) is the executable source of truth for continuous integration.
