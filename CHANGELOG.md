# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- A test suite, run in CI against Python 3.10–3.14 on Linux and macOS.
- GitHub Actions for tests, lint, a weekly dependency audit, and a
  tag-triggered release that publishes to PyPI via Trusted Publishing.

### Changed

- **Requires Python 3.10 or newer.** 3.9 has reached end of life.
- Packaging moved from `setup.cfg` to PEP 621 metadata in `pyproject.toml`,
  built by `flit_core`. The version is now single-sourced from
  `roj.__version__`.
- The trove classifiers now say `POSIX` / `POSIX :: BSD :: FreeBSD` rather
  than `OS Independent`: `os.execvp`, `shlex.quote` and `ssh(1)` mean Windows
  was never supported.
- Source is formatted and linted by `ruff`.

### Fixed

- `roj/__main__.py` called `main()` at import time, so merely running
  `import roj.__main__` executed the whole program — it would spawn `jls` and
  then `exec` a login shell. The call is now guarded by
  `if __name__ == "__main__":`. The `roj` console script and `python -m roj`
  are unaffected.

## [0.2.4] — 2026-01-04

### Fixed

- Do not drain standard input early.

## [0.2.3] — 2023-04-19

### Fixed

- `-t`/`--tty` handling.

## [0.2.2] — 2023-03-20

### Added

- Manual control over `ioc-` prefix stripping (`-f`/`--full`, `-s`/`--short`).

## [0.2.1] — 2023-03-19

### Fixed

- Bash completion.

## [0.2.0] — 2023-03-17

### Added

- Bash completion support.

## 0.1.0 — 2021-09-23

- Initial release.

[Unreleased]: https://github.com/astralblue/roj/compare/v0.2.4...HEAD
[0.2.4]: https://github.com/astralblue/roj/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/astralblue/roj/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/astralblue/roj/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/astralblue/roj/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/astralblue/roj/releases/tag/v0.2.0
