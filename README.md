roj (Run On Jail)
=================

roj is a simple command-line tool that runs a command (login shell by default)
in the given jail, either locally or over SSH.

Requirements
------------

Python 3.10 or newer.

The host whose jails you are addressing must be FreeBSD, since `roj` drives
`jls(8)` and `jexec(8)` there.  The machine you run `roj` *from* need only be
POSIX: with `-H`/`--host` everything is wrapped in `ssh(1)`, so driving a
FreeBSD jail host from Linux or macOS works.  Windows is not supported.

`jexec(8)` needs root.  If you are not root on the jail host, `sudo(8)` must
be installed there and you must be allowed to run `jexec` through it; see
[Privilege Escalation](#privilege-escalation-sudo) below.

Installation
------------

```sh
pip install roj
```

Examples:

```sh
roj abc
```

Runs a login shell in the local jail named `abc`.

```sh
roj -H adx ldap1 ps axl
```

Runs `ps axl` in the jail named `ldap1` on the remote SSH host `adx`.

```sh
roj
```

Shows the jails on the local host.

```sh
roj -H pbsp
```

Shows the jails on the remote SSH host `pbsp`.

iocage Compatibility
--------------------

[The `iocage` jail manager](https://github.com/iocage/iocage)
uses the `ioc-` prefix in its jail names.
To maintain compatibility with `iocage`,
by default `roj` shows and accepts jail names without the `ioc-` prefix.

Except if there is a conflict, then this prefix stripping behavior is disabled.
For example, if there is a jail `ioc-xyz` and there is also another jail `xyz`,
then the former is shown as and must be specified as `ioc-test`.

This behaviour can be disabled using the `-f`/`--full` flag.

SSH Host (`-H`/`--host`) Config
-------------------------------

The hostname given to `-H`/`--host` is provided verbatim to
[OpenSSH `ssh(1)`](https://www.freebsd.org/cgi/man.cgi?query=ssh&sektion=1)
so the name is subject to the usual
[configuration](https://www.freebsd.org/cgi/man.cgi?query=ssh_config&sektion=5)
settings.  For example, to use a shorthand alias, ex: `roj -Hadx`:

```
Host adx
        HostName adx-florence.bop.gov
```

SSH Pseudo TTY Allocation
-------------------------

Just like OpenSSH `ssh(1)`, by default login shells are run with a pseudo TTY,
and explicit commands are run without one.
This behavior can be overridden with `--tty`/`--no-tty`
(or `-t`/`-T`, as with `ssh(1)`).


Privilege Escalation (`sudo`)
-----------------------------

`jexec(8)` requires root, so `roj` runs it under `sudo(8)` when the user it
would otherwise run as is not root.  `jls(8)` is never run under `sudo`:
listing jails does not need privileges.

There are three states:

* By default the decision is automatic.  Locally, `roj` sudoes when its own
  effective uid is not 0.  Remotely, the decision is made on the far side by
  the jail host's `/bin/sh`, since which user an SSH session lands as is not
  knowable from here.
* `--sudo`/`-S` always runs `jexec` under `sudo`, with no uid check.
* `--no-sudo` never does, which is exactly the pre-0.4.0 behavior.

`roj` never passes `-n`, so a password prompt is always allowed to happen; if
it cannot, `sudo` itself says so and fails:

```
sudo: a terminal is required to read the password; either use ssh's -t option
or configure an askpass helper
sudo: a password is required
```

Whether there is a terminal to prompt on is up to `ssh`, which allocates a
pseudo TTY only when asked with `-t` -- the default for a login shell, but not
for an explicit command.  So to let `sudo` prompt for a password while running
an explicit command over SSH, pass `-t`:

```sh
roj -H adx -t ldap1 ps axl
```

For unattended use -- cron, scripts, anything with neither a terminal nor an
askpass helper -- give the invoking user a `NOPASSWD` entry for `jexec` in
`sudoers(5)` on the jail host:

```
alice ALL = (root) NOPASSWD: /usr/sbin/jexec
```


Bash Completion
---------------

To use Bash completion support of `roj`:

```sh
complete -C 'roj --bash-complete' roj
```

It takes connection-related options (`-H`/`--host` and `-u`/`--user`)
so the following works as expected:

```sh
alias roj1='roj --host=server1'
complete -C `roj1 --bash-complete` roj1
```


Development
-----------

The dev toolchain is managed by [uv](https://docs.astral.sh/uv/), and
`uv.lock` is committed and authoritative.

```sh
uv sync                          # create .venv from uv.lock
uv run pytest                    # run the tests
uv run --python 3.14 pytest      # ...on any supported version; uv fetches it
uv run ruff check .              # lint
uv run ruff format .             # format ("--check" to verify only)
uv build                         # build the sdist and wheel
```

If you change `[project]` or `[dependency-groups]` in `pyproject.toml`,
regenerate the lockfile with `uv lock` and commit it: CI runs `uv lock --check`
and fails on a stale one.
