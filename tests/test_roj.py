"""Tests for :mod:`roj`.

Everything here is pure Python: ``jls``/``jexec``/``ssh`` are never spawned,
so the suite runs on any POSIX CI runner rather than only on a FreeBSD jail
host.
"""

import subprocess
import sys

import pytest

import roj

# jid/name pairs as `jls jid name` would print them.  "ioc-alpha" has no
# unprefixed twin, so it is a candidate for prefix stripping; "ioc-beta"
# collides with "beta", so it is not.
JLS_LINES = [b"1 ioc-alpha\n", b"2 ioc-beta\n", b"3 beta\n", b"4 gamma\n"]


class _FakePopen:
    """Stand-in for :class:`subprocess.Popen` yielding canned output."""

    def __init__(self, lines):
        self.stdout = iter(lines)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def make_roj(argv, jls_lines=JLS_LINES):
    """Build a RunOnJail with parsed *argv* and a faked jail listing."""
    instance = roj.RunOnJail()
    # `args` is a lazily-parsed property backed by a name-mangled attribute;
    # priming it keeps the real sys.argv out of the tests.
    instance._RunOnJail__args = instance.argparser.parse_args(argv)
    instance.popen = lambda *poargs, **kwargs: _FakePopen(iter(jls_lines))
    return instance


# --- argument parsing ------------------------------------------------------


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        ([], None),
        (["--tty"], True),
        (["-t"], True),
        (["--no-tty"], False),
        (["-T"], False),
    ],
)
def test_tty_flags(argv, expected):
    assert make_roj(argv).args.tty is expected


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        ([], None),
        (["--full"], True),
        (["-f"], True),
        (["--short"], False),
        (["-s"], False),
    ],
)
def test_full_flags(argv, expected):
    assert make_roj(argv).args.full is expected


def test_user_defaults_to_root():
    assert make_roj([]).args.user == "root"


def test_tty_and_no_tty_are_mutually_exclusive():
    with pytest.raises(SystemExit):
        make_roj(["-t", "-T"])


# --- ioc- prefix handling --------------------------------------------------


def test_list_jails_strips_unambiguous_ioc_prefix():
    assert list(make_roj([]).list_jails()) == [
        ("1", "alpha"),
        ("2", "ioc-beta"),
        ("3", "beta"),
        ("4", "gamma"),
    ]


def test_list_jails_keeps_prefix_when_a_bare_name_collides():
    # "ioc-beta" must stay prefixed because a separate "beta" jail exists.
    assert ("2", "ioc-beta") in list(make_roj([]).list_jails())


def test_full_disables_stripping_entirely():
    assert list(make_roj(["--full"]).list_jails()) == [
        ("1", "ioc-alpha"),
        ("2", "ioc-beta"),
        ("3", "beta"),
        ("4", "gamma"),
    ]


def test_short_is_the_same_as_the_default():
    assert list(make_roj(["--short"]).list_jails()) == list(
        make_roj([]).list_jails()
    )


def test_names_containing_spaces_survive_parsing():
    lines = [b"7 ioc-a name with spaces\n"]
    assert list(make_roj([], jls_lines=lines).list_jails()) == [
        ("7", "a name with spaces")
    ]


# --- jail lookup -----------------------------------------------------------


def test_find_jail_resolves_a_stripped_name():
    assert make_roj(["alpha"]).find_jail() == ("1", "alpha")


def test_find_jail_raises_fatal_error_when_absent():
    with pytest.raises(roj.FatalError, match="jail nosuch not found"):
        make_roj(["nosuch"]).find_jail()


# --- ssh wrapping ----------------------------------------------------------


def test_wrap_argv_is_a_passthrough_without_a_host():
    argv = ["jexec", "-U", "root", "1", "login", "-f", "root"]
    assert make_roj(["alpha"]).wrap_argv(argv) == argv


def test_wrap_argv_requests_a_tty_when_asked():
    wrapped = make_roj(["-H", "adx", "alpha"]).wrap_argv(
        ["jexec", "1"], ssh_tty=True
    )
    assert wrapped == ["ssh", "-t", "adx", "jexec 1"]


def test_wrap_argv_suppresses_the_tty_by_default():
    wrapped = make_roj(["-H", "adx", "alpha"]).wrap_argv(["jexec", "1"])
    assert wrapped == ["ssh", "-T", "adx", "jexec 1"]


def test_wrap_argv_quotes_arguments_for_the_remote_shell():
    wrapped = make_roj(["-H", "adx", "alpha"]).wrap_argv(
        ["echo", "two words", "semi;colon"]
    )
    assert wrapped[-1] == "echo 'two words' 'semi;colon'"


# --- the tty default depends on whether a command was given ----------------


def _exec_argv(monkeypatch, argv):
    """Run main() with os.execvp stubbed, returning the argv it would exec."""
    captured = {}

    def fake_execvp(file, args):
        captured["file"] = file
        captured["args"] = args
        raise SystemExit(0)

    monkeypatch.setattr(roj.os, "execvp", fake_execvp)
    with pytest.raises(SystemExit):
        make_roj(argv).main()
    return captured["args"]


def test_login_shell_gets_a_tty_by_default(monkeypatch):
    args = _exec_argv(monkeypatch, ["-H", "adx", "alpha"])
    assert args[:3] == ["ssh", "-t", "adx"]
    assert args[3] == "jexec -U root 1 login -f root"


def test_explicit_command_gets_no_tty_by_default(monkeypatch):
    args = _exec_argv(monkeypatch, ["-H", "adx", "alpha", "ps", "axl"])
    assert args[:3] == ["ssh", "-T", "adx"]
    assert args[3] == "jexec -U root 1 ps axl"


def test_no_tty_overrides_the_login_shell_default(monkeypatch):
    args = _exec_argv(monkeypatch, ["-H", "adx", "-T", "alpha"])
    assert args[1] == "-T"


def test_tty_overrides_the_command_default(monkeypatch):
    args = _exec_argv(monkeypatch, ["-H", "adx", "-t", "alpha", "ps"])
    assert args[1] == "-t"


def test_local_invocation_execs_jexec_directly(monkeypatch):
    args = _exec_argv(monkeypatch, ["alpha", "ps"])
    assert args == ["jexec", "-U", "root", "1", "ps"]


# --- packaging -------------------------------------------------------------


def test_version_is_exposed():
    assert isinstance(roj.__version__, str)


def test_importing_the_main_module_does_not_run_the_program():
    """Regression test: roj.__main__ used to call main() at import time.

    The console script imports this module, so an unguarded call meant a
    bare `import roj.__main__` spawned jls and then exec'd a login shell.
    """
    completed = subprocess.run(
        [sys.executable, "-c", "import roj.__main__"],
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode()
    assert completed.stdout == b""


# --- listing, error reporting and bash completion --------------------------


def test_no_jail_argument_lists_jails(capsys):
    assert make_roj([]).main() == 0
    assert capsys.readouterr().out == (
        "1 alpha\n2 ioc-beta\n3 beta\n4 gamma\n"
    )


def test_fatal_error_is_reported_on_stderr_and_exits_nonzero(capsys):
    assert make_roj(["nosuch"]).main() == 1
    assert "jail nosuch not found" in capsys.readouterr().err


def test_fatal_error_can_carry_its_own_exit_status(capsys):
    instance = make_roj(["alpha"])
    instance.find_jail = lambda: (_ for _ in ()).throw(
        roj.FatalError("boom", 42)
    )
    assert instance.main() == 42
    assert "boom" in capsys.readouterr().err


def _bash_complete_env(monkeypatch, line):
    monkeypatch.setenv("COMP_LINE", line)
    monkeypatch.setenv("COMP_POINT", str(len(line)))
    monkeypatch.setenv("COMP_KEY", "9")
    monkeypatch.setenv("COMP_TYPE", "9")


def test_bash_complete_prints_names_matching_the_current_word(
    monkeypatch, capsys
):
    _bash_complete_env(monkeypatch, "roj b")
    make_roj(["--bash-complete", "roj", "b", "roj"]).main()
    assert sorted(capsys.readouterr().out.split()) == ["beta"]


def test_bash_complete_offers_every_jail_for_an_empty_word(
    monkeypatch, capsys
):
    _bash_complete_env(monkeypatch, "roj ")
    make_roj(["--bash-complete", "roj", "", "roj"]).main()
    assert sorted(capsys.readouterr().out.split()) == [
        "alpha",
        "beta",
        "gamma",
        "ioc-beta",
    ]


def test_bash_complete_requires_the_bash_completion_environment(capsys):
    # get_env() raising is the only check that bash actually invoked us.
    assert make_roj(["--bash-complete", "roj", "b", "roj"]).main() == 1
    assert "COMP_LINE" in capsys.readouterr().err


def test_main_entry_point_exits_with_the_status_from_run_on_jail(monkeypatch):
    import roj.__main__

    monkeypatch.setattr(
        roj.__main__.roj, "RunOnJail", lambda: _StubRunOnJail(7)
    )
    with pytest.raises(SystemExit) as excinfo:
        roj.__main__.main()
    assert excinfo.value.code == 7


class _StubRunOnJail:
    def __init__(self, status):
        self._status = status

    def main(self):
        return self._status
