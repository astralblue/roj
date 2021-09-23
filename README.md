roj (Run On Jail)
=================

roj is a simple command-line tool that runs a command (login shell by default)
in the given jail, either locally or remotely over SSH.

The given jail name is tried verbatim, and if not found, with an `ioc-` prefix
for compatibility with iocage.

Examples:

```sh
roj abc
```

Runs a login shell in the local jail named `abc` (or if not found, `ioc-abc`).

```sh
roj -Hhy abc ps axl
```

Runs `ps axl` in the jail named `abc` or `ioc-abc` on a remote host `hy`.  The
hostname is provided verbatim to
[`ssh(1)`](https://www.freebsd.org/cgi/man.cgi?query=ssh&sektion=1) so usual
[`ssh_config(5)`](https://www.freebsd.org/cgi/man.cgi?query=ssh_config&sektion=5)
settings can be applied, e.g. in the `Host hy` section.
