# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

## What this is

`roj` ("run on jail") is a small console script that runs a command — a login shell by
default — inside a FreeBSD jail. It shells out to `jls jid name` to enumerate jails and
`os.execvp`s `jexec`; with `-H`/`--host` the whole argv is `shlex`-quoted and wrapped in
`ssh(1)`, so a FreeBSD jail host can be driven from any POSIX client. `jexec` is run under
`sudo(8)` when the user it would run as is not root. Everything lives in
`roj/__init__.py` (~280 lines); `roj/__main__.py` is a 13-line entry point.

## Commands

The dev toolchain is managed by `uv`; `uv.lock` is committed and authoritative.

```sh
uv sync                 # create .venv from uv.lock (project + `dev` group)

uv run pytest           # tests on the default interpreter
uv run --python 3.14 pytest      # ...on any supported version; uv fetches it
uv run ruff check .     # lint
uv run ruff format .    # format (`--check` to verify only)
uv run coverage run -m pytest && uv run coverage report -m
uv build                # sdist + wheel via flit_core
uv lock                 # re-resolve after editing pyproject.toml; CI runs
                        # `uv lock --check` and fails on a stale lockfile
uv audit --frozen --preview-features audit-command   # known vulnerabilities
```

Single test / subset:

```sh
uv run pytest tests/test_roj.py::test_wrap_argv_quotes_arguments_for_the_remote_shell
uv run pytest -k ioc
```

There is no Makefile and no tox: the version matrix lives in
`.github/workflows/test.yml`, and `uv run --python X.Y` covers it locally.

Vulnerability scanning is deliberately *not* part of the pull-request gate: it runs weekly
from `.github/workflows/audit.yml`, because every locked package is dev tooling (zero runtime
dependencies) and a fresh advisory should not redden an unrelated pull request.

## Architecture

`RunOnJail` is one class with two lazily-built cached properties, `argparser` and `args`,
backed by name-mangled `__argparser`/`__args` attributes. Tests prime `args` directly
(`instance._RunOnJail__args = ...`) to keep the real `sys.argv` out of the suite.

Four behaviors carry more subtlety than they look:

- **`ioc-` prefix stripping is conditional.** `list_jails` reads the whole listing first,
  then strips an `ioc-` prefix from a name only if no *other* jail already has the bare name.
  A jail called `ioc-beta` stays `ioc-beta` when a `beta` also exists. `-f`/`--full` disables
  stripping; `-s`/`--short` restores the default. Because the collision check needs the full
  set, the listing cannot be streamed.
- **The pseudo-TTY default depends on whether a command was given.** A login shell defaults to
  `ssh -t`, an explicit command to `ssh -T`, mirroring `ssh(1)` itself. `--tty`/`--no-tty`
  override. `args.tty` is tri-state — `None` means "not specified", so use `is None`, not
  falsiness.
- **The sudo decision is made in two different places.** Locally `roj` knows its own uid,
  so `local_sudo_prefix` decides in Python. Remotely it cannot know who the SSH session
  lands as, so `remote_sudo_script` emits a `case "$(id -u)" in 0) …` snippet that decides
  on the far side. `args.sudo` is tri-state like `args.tty` — `None` means "not specified".

  Three details are load-bearing:

  - **The `/bin/sh -c` wrapper is only for the auto case, and it cannot be raw shell in the
    argv.** `wrap_argv` `shlex.quote`s *every* element before joining, so `case`,
    `"$(id -u)"` and `;;` would all reach the far side as literals; and `ssh host 'cmd'` runs
    `cmd` under the remote *login* shell, historically `/bin/csh` on FreeBSD, where
    `case … esac` is a syntax error. `["/bin/sh", "-c", script]` fixes both: the existing
    quoting makes `script` a single argument, and the two quoting levels line up exactly with
    the two shells that unwrap them (login shell, then `/bin/sh`). Inside the script, use
    **double** quotes, so `shlex.quote`'s single-quoting needs no `'"'"'` escaping, and leave
    `$s` unquoted so it disappears when empty instead of becoming an empty first argument to
    `exec`. `--sudo` needs none of this — with no uid test left to run, it is a plain `sudo`
    prefix on both paths.
  - **`jls` is never sudo'd.** It does not need privileges, and `list_jails` parses its output
    positionally, so it must never get a pty either (LF→CRLF would corrupt the parse). Hence
    `wrap_argv`'s `sudo` parameter defaults to `False`, which leaves `popen` — and therefore
    `list_jails` — untouched. `--no-sudo` reproduces the 0.3.0 argv byte for byte, including
    the absence of the `/bin/sh -c` wrapper.
  - **There is deliberately no terminal detection, and `sudo -n` is never used.** An earlier
    draft picked `sudo -n` when no tty was around, to avoid hanging on a prompt nobody could
    answer. That is unnecessary — `sudo` already fails immediately and legibly ("a terminal is
    required to read the password; either use ssh's -t option or configure an askpass helper")
    — and actively harmful, because `-n` also refuses to use an askpass helper, which is
    exactly how a password *can* be supplied without a terminal. Whether sudo may prompt is
    therefore governed entirely by `-t`/`-T`: `ssh -t` allocates the pty that gives the remote
    `sudo` something to prompt on.

- **`main()` ends in `os.execvp` and does not return** on the success path. It is testable
  only by stubbing `os.execvp` and asserting the argv it would have exec'd, which is what
  `tests/test_roj.py` does.

`bash_complete` reads `COMP_LINE`, `COMP_POINT`, `COMP_KEY` and `COMP_TYPE` and then ignores
all four. Do not "clean up" those bindings: `get_env` raises `FatalError` when a variable is
missing, and that is the function's only check that bash actually invoked it. They are
underscore-prefixed so `ruff`'s F841 accepts them; deleting them drops the check, and
replacing them with bare calls trips B018.

## Conventions

- `ruff` is the lint gate, configured in `pyproject.toml` with `E`, `W`, `F`, `I`, `UP`, `B`
  selected. **`D` (pydocstyle) is deliberately not selected** — the gate it replaced was an
  inactive PyCharm inspection profile that never required docstrings, and selecting `D` would
  flag every method in `RunOnJail` at once.
- `ruff format` owns formatting; 79-column lines, LF endings, no trailing whitespace
  (`.editorconfig`). Note it normalizes string quotes to double — which matters, see below.
- `.idea/` is **deliberately tracked**. Keep `misc.xml`, `roj.iml`, `ruff.xml` and
  `codeStyles/` in step with the toolchain (SDK name `uv (roj)`, `RIGHT_MARGIN` matching
  `[tool.ruff] line-length`) rather than removing them.
- Add a `CHANGELOG.md` entry alongside any user-visible change.

## Packaging / CI state

Packaging is PEP 621 metadata in `pyproject.toml` built by `flit_core`, with zero runtime
dependencies and the version single-sourced from `roj.__version__`.

**`[tool.flit.sdist]` is load-bearing, not decorative.** Under a PEP 517 frontend `flit_core`
never consults version control, so the default sdist is only `roj/`, `pyproject.toml`,
`README.md` and `LICENSE`. Anything else that should ship — `tests/`, `CHANGELOG.md` — has to
be listed in its `include`. Check `tar -tzf dist/*.tar.gz` after touching it.

Because `license = "BSD-2-Clause"` is a PEP 639 expression, a `License :: OSI Approved`
classifier must **not** be added back: `flit_core` errors out when both are present.

Version bumps are driven by `bump-my-version` (`[tool.bumpversion]`); it rewrites
`__version__` in `roj/__init__.py`, commits, and tags `vX.Y.Z`. **Never edit that string by
hand** — the packaging metadata reads it via `dynamic = ["version"]`, and the tool's `search`
pattern must keep matching it. It is double-quoted because that is what `ruff format`
produces; if the quote style ever diverges, the bump silently succeeds while changing nothing.

Two GitHub Actions references are **pinned to exact versions on purpose**:
`astral-sh/setup-uv` stopped publishing floating major tags after `v7` (there is no `v10`),
and `pypa/gh-action-pypi-publish` has no `v1` tag at all — it publishes `release/v1` as a
*branch*. Referencing either as `@vN` fails every job at setup. The grouped `github-actions`
Dependabot updates keep those pins current; re-resolve against the upstream tag list before
changing them.

Branch protection on `main` requires exactly one status check, **`all checks`** — the
aggregator job in `test.yml` that depends on `lint` and the whole `test` matrix. Required
checks are matched by *name*, so requiring the matrix legs directly (`py3.10 on
ubuntu-latest`, …) would block every pull request the moment the matrix changes. Renaming the
`all-checks` job means updating the protection rule in the same change.

CI is GitHub Actions on the **`main`** default branch, and the only git remote is
**`astralblue`** — there is no `origin`. That remote's fetch refspec maps upstream tags into a
prefixed local namespace (`refs/tags/astralblue/*`), so **never push with `--follow-tags` or
`--tags`**: push a release tag by name. Releases go to PyPI through Trusted Publishing on a
pushed release tag — no stored credential. `release.yml` filters on
`v[0-9]+.[0-9]+.[0-9]+` rather than `v*`, so a tag like `verify-something` cannot trigger a
release; that filter is the single definition of a release tag, and the workflow's job guards
key off `github.event_name == 'push'` rather than re-matching the ref, so they cannot drift
from it.

**The `pypi` environment's tag rule uses a different pattern language** and is restricted to
`v[0-9]*.[0-9]*.[0-9]*`. Deployment branch/tag rules are matched with Ruby's `File.fnmatch`,
where `+` is a *literal* character rather than a quantifier — pasting the workflow's
`v[0-9]+.[0-9]+.[0-9]+` in there matches nothing at all and silently blocks every deployment.
Verify any change to it with `ruby -e 'p File.fnmatch(<pattern>, "v1.2.3")'` before saving.

The supported-version list is duplicated in **four** places — `requires-python`, the
`Programming Language :: Python` classifiers, `[tool.ruff] target-version`, and the
`test.yml` matrix. Changing version support means touching all four.
