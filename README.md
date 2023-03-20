roj (Run On Jail)
=================

roj is a simple command-line tool that runs a command (login shell by default)
in the given jail, either locally or over SSH.

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