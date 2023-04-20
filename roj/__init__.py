from __future__ import annotations

import argparse
import logging
import os
import shlex
import subprocess
import sys
from typing import Optional

logger = logging.getLogger(__name__)


class FatalError(RuntimeError):
    """Fatal error, which causes program to exit with the given message."""


class RunOnJail:
    __argparser: Optional[argparse.ArgumentParser] = None
    __args: Optional[argparse.Namespace] = None
    logger = logger.getChild('RunOnJail')

    def __init__(self, *poargs, **kwargs):
        super().__init__(*poargs, **kwargs)
        self.__logger = self.logger.getChild(str(id(self)))

    def main(self):
        try:
            if self.args.debug:
                logging.getLogger().setLevel(logging.DEBUG)
            if self.args.bash_complete:
                return self.bash_complete()
            if self.args.jail is None:
                self.__logger.debug("listing jails")
                for jid, name in self.list_jails():
                    print(f"{jid} {name}")
                return 0
            self.__logger.debug("looking for jail %s", self.args.jail)
            jid, name = self.find_jail()
            self.__logger.debug("found jail %s (%s)", jid, name)
            ssh_tty = self.args.tty
            if self.args.command:
                command = ['jexec', '-U', self.args.user, jid]
                command.extend(self.args.command)
                if ssh_tty is None:
                    ssh_tty = False
            else:
                command = ['jexec', '-U', 'root', jid,
                           'login', '-f', self.args.user]
                if ssh_tty is None:
                    ssh_tty = True
            command = self.wrap_argv(command, ssh_tty=ssh_tty)
            self.__logger.debug("running: %r", command)
            os.execvp(command[0], command)
        except FatalError as e:
            print(f"{self.argparser.prog}: {e}", file=sys.stderr)
            try:
                return e.args[1]
            except IndexError:
                return 1

    def list_jails(self):
        jail_list = []
        jails = set()
        with self.popen(['jls', 'jid', 'name'],
                        stdout=subprocess.PIPE) as popen:
            for line in popen.stdout:
                jid, name = line.decode().removesuffix('\n').split(' ', 1)
                jail_list.append((jid, name))
                jails.add(name)
        for jid, name in jail_list:
            if (
                    not self.args.full and
                    name.startswith('ioc-') and
                    name[4:] not in jails
            ):
                name = name[4:]
            yield jid, name

    def find_jail(self):
        jids = {name: jid for jid, name in self.list_jails()}
        self.__logger.debug("jids=%r", jids)
        try:
            return jids[self.args.jail], self.args.jail
        except KeyError:
            raise FatalError(f"jail {self.args.jail} not found")

    def popen(self, args, *poargs, **kwargs):
        argv = self.wrap_argv(args)
        self.__logger.debug("running: %r", argv)
        return subprocess.Popen(argv, *poargs, **kwargs)

    def wrap_argv(self, argv, ssh_tty=False):
        if self.args.host is None:
            return argv
        else:
            tty_flag = '-t' if ssh_tty else '-T'
            return ['ssh', tty_flag, self.args.host,
                    ' '.join(shlex.quote(arg) for arg in argv)]

    @property
    def args(self):
        if self.__args is None:
            self.__args = self.argparser.parse_args()
        return self.__args

    @property
    def argparser(self):
        if self.__argparser is None:
            parser = argparse.ArgumentParser()
            parser.add_argument('--host', '-H', metavar='<HOST>',
                                help="""jail host; passed to OpenSSH ssh(1) so
                                        ssh_config(5) aliases also work""")
            user = parser.add_mutually_exclusive_group()
            user.add_argument('--user', '-u', metavar='<USER>',
                              help="""username (in jail) or uid to run as""")
            tty = parser.add_mutually_exclusive_group()
            tty.add_argument('--tty', '-t',
                             action='store_const', dest='tty', const=True,
                             help="""allocate TTY when running remotely""")
            tty.add_argument('--no-tty', '-T',
                             action='store_const', dest='tty', const=False,
                             help="""do not allocate TTY when running
                                     remotely""")
            parser.add_argument('--full', '-f', action='store_const',
                                dest='full', const=True,
                                help="""show/use full jail names:
                                        disable "ioc-" stripping""")
            parser.add_argument('--short', '-s', action='store_const',
                                dest='full', const=False,
                                help="""show/use short jail names: if a jail
                                        name starts with an "ioc-" prefix and
                                        there is no other jail with the
                                        corresponding name without the prefix,
                                        strip the prefix""")
            parser.add_argument('--debug', action='store_true',
                                help="""enable debug logging""")
            parser.add_argument('--bash-complete', nargs=3,
                                metavar=('<COMMAND>', '<WORD>', '<PWORD>'),
                                help="""bash completion helper""")
            parser.add_argument('jail', metavar='<JAIL>', nargs='?',
                                help="""the jail name or ID; if not found
                                        as-is a name prefixed with "ioc-" is
                                        tried for iocage compatibility""")
            parser.add_argument('command', metavar='<ARG>', nargs='*',
                                help="""command and its arguments to run in
                                        the jail; if not specified, login -f
                                        <USER> is assumed, to get a login
                                        shell""")
            parser.set_defaults(user='root')
            self.__argparser = parser
        return self.__argparser

    def bash_complete(self):
        def get_env(name):
            try:
                return os.environ[name]
            except KeyError:
                raise FatalError(f"Bash completion variable {name} not found")

        comp_line = get_env('COMP_LINE')
        comp_point = int(get_env('COMP_POINT'))
        comp_key = get_env('COMP_KEY')
        comp_typ = get_env('COMP_TYPE')
        command, word, prev_word = self.args.bash_complete

        names = {name for jid, name in self.list_jails()}
        for name in names:
            if name.startswith(word):
                print(name)
