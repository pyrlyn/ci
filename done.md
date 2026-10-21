# infra — completed tasks

### T5. Add the required project files

The project was missing `AGENTS.md`, `done.md`, `roadmap.md`, `ideas.md`, and `toolchain.md`. Done means: all files exist, with the real toolchain (actionlint via mise, git, GitHub Actions) in `toolchain.md`.

Those files are in the repo root. `toolchain.md` lists actionlint, git, and the Rust pin used by `ci-rust.yml`. `tests/fixtures/rust-crate/src/lib.rs` already has a unit test, so no new test was added.

### T2. Run actionlint on pushes to main

`.github/workflows/lint.yml` triggers on `push: branches: [main]` as well as `pull_request` and `workflow_dispatch`, so a merge or a direct commit to main runs actionlint. `workflow_call` is unchanged, so SHA-pinned callers are unaffected. Landed in `496b92a` (#58) and re-verified against `origin/main` at `980f4f8`.
