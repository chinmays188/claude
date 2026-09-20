# Production Architecture & Dockerization (Phase 5, Milestones 44-45)

## Milestone 44 — Production Architecture

`docs/production_architecture.md` documents the target production layout and
an explicit table of what changes from Phases 1-4 to a real deployment, with
each change mapped to the Phase 5 milestone that addresses it. It also lists,
explicitly, what Phase 5 does NOT claim to have actually deployed (no real
load balancer, no real external queue broker, no real Prometheus/Grafana
stack) — consistent with this project's practice of stating gaps rather than
implying more than was built.

## Milestone 45 — Dockerization

### What was built

- `Dockerfile`: multi-stage build (builder installs deps including the
  heavier `sentence-transformers`/`faiss-cpu` native wheels; runtime stage
  copies only installed packages + app code), runs as a non-root user,
  includes a `HEALTHCHECK`.
- `docker-compose.yml`: single-service local compose setup with a named
  volume for the SQLite data directory and environment variables for API keys.
- `.dockerignore`: excludes `.venv`, caches, `.env`, the SQLite db file,
  git metadata, tests, and root-level docs — while explicitly NOT excluding
  `specs/*.md` or `evals/*.json`, which the Dockerfile actually `COPY`s into
  the image (a real bug caught and fixed while authoring this: an overly
  broad `*.md` ignore pattern would have silently stripped `specs/` from the
  build context before the `COPY specs/ ./specs/` step ever ran).

### Honest verification status

**Docker is not installed in this development sandbox** (`docker` command
not found, confirmed via `which docker` and checking package managers).
Per the user's explicit fallback instruction, this was not silently glossed
over — instead:

- Every path referenced in `COPY` instructions (`app/`, `specs/`, `evals/`)
  was verified to actually exist in the repository.
- Stage names (`builder`, `runtime`) were verified to be referenced
  consistently between `FROM ... AS <name>` and `COPY --from=<name>`.
- `requirements.txt` is already proven installable — it's the exact file the
  project's own `.venv` was built from and has been running against
  throughout Phases 1-4.

What this does NOT verify: whether `docker build` actually succeeds end to
end (dependency resolution inside the exact `python:3.11-slim` base image
could still surface an issue this review can't catch — e.g. a missing system
library for `faiss-cpu`'s wheel), or whether the built container actually
starts and serves traffic. **This is a real, disclosed gap** — if Docker
becomes available in a future session, `docker build -t personal-ai-os .`
followed by `docker compose up` should be run to close it.
