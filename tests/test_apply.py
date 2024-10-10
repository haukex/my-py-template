"""Tests for ``apply.py``

Author, Copyright, and License
------------------------------

Copyright (c) 2023-2024 Hauke Daempfling (haukex@zero-g.net)
at the Leibniz Institute of Freshwater Ecology and Inland Fisheries (IGB),
Berlin, Germany, https://www.igb-berlin.de/

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see https://www.gnu.org/licenses/
"""
import io
import sys
import filecmp
import unittest
import subprocess
from pathlib import Path
from itertools import chain
from contextlib import redirect_stdout
from tempfile import TemporaryDirectory
from unittest.mock import patch, call, _Call  # pyright: ignore [reportPrivateUsage]
from igbpyutils.file import NamedTempFileDeleteLater
from colorama import Fore, Back, Style
import apply

def fake_msg(color :str, msg :str):
    return f"{Style.BRIGHT}{color}##### {msg} #####{Style.RESET_ALL}\n"

class ApplyScriptTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_do_diff(self):
        with NamedTempFileDeleteLater() as tf1, NamedTempFileDeleteLater() as tf2:
            tf1.write(b'Hello\nx')
            tf1.close()
            tf2.write(b'Hello\nx')
            tf2.close()
            sp_rv :subprocess.CompletedProcess

            # git diff
            sp_rv = subprocess.CompletedProcess(
                ['git','--no-pager','diff','--no-index','--color-words','--',tf1.name,tf2.name], 0)
            with patch('subprocess.run', return_value=sp_rv) as sp_run:
                apply.do_diff(tf1.name, tf2.name)
            sp_run.assert_called_once_with(sp_rv.args, check=False)

            # git diff rv 1
            sp_rv.returncode = 1
            with patch('subprocess.run', return_value=sp_rv) as sp_run:
                apply.do_diff(tf1.name, tf2.name)
            sp_run.assert_called_once_with(sp_rv.args, check=False)

            # git diff rv other
            sp_rv.returncode = 250
            with patch('subprocess.run', return_value=sp_rv) as sp_run:
                apply.do_diff(tf1.name, tf2.name)
            sp_run.assert_called_once_with(sp_rv.args, check=False)

            # git diff err
            with patch('subprocess.run', side_effect=subprocess.SubprocessError) as sp_run:
                apply.do_diff(tf1.name, tf2.name)
            sp_run.assert_called_once_with(sp_rv.args, check=False)

            # git ignore ws
            sp_rv = subprocess.CompletedProcess(
                ['git','--no-pager','diff','--no-index','--color-words','--ignore-all-space','--',tf1.name,tf2.name], 0)
            with patch('subprocess.run', return_value=sp_rv) as sp_run:
                apply.do_diff(tf1.name, tf2.name, ignore_ws=True)
            sp_run.assert_called_once_with(sp_rv.args, check=False)

            # no git diff
            with patch('subprocess.run') as sp_run:
                apply.do_diff(tf1.name, tf2.name, try_git=False)
            sp_run.assert_not_called()

            # test custom diff
            with open(tf2.name,'wb') as fh:
                fh.write(b'World\nx')
            with redirect_stdout(io.StringIO()) as out:
                apply.do_diff(tf1.name, tf2.name, try_git=False)
            self.assertEqual( out.getvalue(),
                f"{Style.BRIGHT}--- {tf1.name}{Style.RESET_ALL}\n"
                f"{Style.BRIGHT}+++ {tf2.name}{Style.RESET_ALL}\n"
                f"{Fore.CYAN}@@ -1,2 +1,2 @@{Style.RESET_ALL}\n"
                f"{Fore.RED}-Hello{Style.RESET_ALL}\n"
                f"{Fore.GREEN}+World{Style.RESET_ALL}\n x\n" )

            # custom diff with ignore_ws
            with open(tf1.name,'wb') as fh:
                fh.write(b"Hello\n\n \n there,\tfriend\t\n\nwhat  's\nup?\nNothing\nmuch.\n")
            with open(tf2.name,'wb') as fh:
                fh.write(b"Hi\n\nthere,  friend\nwhat's\nup?\nNothing\nmuch.")
            with redirect_stdout(io.StringIO()) as out:
                apply.do_diff(tf1.name, tf2.name, try_git=False, ignore_ws=True)
            self.assertEqual( out.getvalue(),
                f"{Style.BRIGHT}--- {tf1.name}{Style.RESET_ALL}\n"
                f"{Style.BRIGHT}+++ {tf2.name}{Style.RESET_ALL}\n"
                f"{Fore.CYAN}@@ -1,8 +1,7 @@{Style.RESET_ALL}\n"
                f"{Fore.RED}-Hello{Style.RESET_ALL}\n"
                f"{Fore.GREEN}+Hi{Style.RESET_ALL}\n"
                f" \n"
                f" there, friend\n"
                f"{Fore.RED}-{Style.RESET_ALL}\n"
                f"{Fore.RED}-what 's{Style.RESET_ALL}\n"
                f"{Fore.GREEN}+what's{Style.RESET_ALL}\n"
                f" up?\n"
                f" Nothing\n"
                f" much.\n" )

    def test_print_msg(self):
        with redirect_stdout(io.StringIO()) as out:
            apply.print_msg(Fore.RED, 'Foo')
        self.assertEqual( out.getvalue(), fake_msg(Fore.RED, 'Foo') )

    def test_prompt_yn(self):
        with patch('builtins.input', return_value='Y') as mock_input:
            self.assertTrue( apply.prompt_yn('Foo?') )
        mock_input.assert_called_once_with(f"{Fore.WHITE}{Back.RED}==>{Style.RESET_ALL} Foo? [yN] ")

    def test_apply(self):  # pylint: disable=too-many-statements,too-many-locals
        sd = Path(__file__).parent.parent
        with (TemporaryDirectory() as tdir,
              patch('apply.init_handlers') as mock_ih,
              patch('apply.print_msg') as mock_printmsg,
              patch('apply.do_diff') as mock_diff,
              patch('apply.prompt_yn', return_value=True) as mock_yn,
              patch('apply.just_fix_windows_console') as mock_fix,
              patch('argparse.ArgumentParser.exit') as mock_exit ):
            td = Path(tdir).resolve(strict=True)

            exp_main = (
                td/'.vscode'/'extensions.json',
                td/'.vscode'/'settings.json',
                td/'dev'/'requirements.txt',
                td/'.gitignore',
                td/'Makefile',
                td/'pyproject.toml',
            )
            exp_optnl = (
                td/'tests'/'__init__.py',
                td/'tests'/'test_dummy.py',
                td/'.github'/'workflows'/'tests.yml',
                td/'dev'/'local-actions.sh',
                td/'dev'/'isolated-dist-test.sh',
                td/'.devcontainer'/'devcontainer.json',
                td/'.devcontainer'/'initialize.sh',
            )
            exp_files = exp_main+exp_optnl
            exp_special = (
                td/'requirements.txt',
            )

            def cmpthem():
                self.assertEqual( sorted( p for p in td.rglob('*') if not p.is_dir() ), sorted(exp_files+exp_special) )
                for p in exp_files:
                    src = sd/p.relative_to(td)
                    self.assertTrue( filecmp.cmp( src, p, shallow=False ), f"files identical: {src} and {p}" )
                for p in exp_special:
                    self.assertEqual( p.lstat().st_size, 0 )

            exp_prompt_yn :list[_Call] = []
            exp_printmsg :list[_Call] = []
            exp_diff :list[_Call] = []

            # try a dry-run on empty dir
            exp_printmsg += [
                call(Fore.YELLOW, f"[DRY RUN] Copying {ef.relative_to(td)} to {ef}") for ef in exp_files ] + [
                call(Fore.YELLOW, "[DRY RUN] Creating empty requirements.txt") ]
            sys.argv = ['apply.py', '--dry-run', str(td)]
            apply.main()

            # requirements.txt creation on empty dir
            mock_yn.return_value = False
            exp_prompt_yn += [call('Copy?')]*len(exp_files) + [call('Create empty?')]
            exp_printmsg += [
                call(Fore.RED, f"Missing {ef.relative_to(td)}") for ef in exp_main ] + [
                call(Fore.RED, f"Missing (optional) {ef.relative_to(td)}") for ef in exp_optnl ] + [
                call(Fore.RED, "Missing requirements.txt") ]
            sys.argv = ['apply.py', '--dry-run', '--interactive', str(td)]
            apply.main()
            mock_yn.return_value = True
            exp_prompt_yn += [call('Copy?')]*len(exp_files) + [call('Create empty?')]
            exp_printmsg += list(chain.from_iterable(
                    [call(Fore.RED,    f"Missing {ef.relative_to(td)}"),
                     call(Fore.YELLOW, f"[DRY RUN] Copying {ef.relative_to(td)} to {ef}")] for ef in exp_main
                )) + list(chain.from_iterable(
                    [call(Fore.RED,    f"Missing (optional) {ef.relative_to(td)}"),
                     call(Fore.YELLOW, f"[DRY RUN] Copying {ef.relative_to(td)} to {ef}")] for ef in exp_optnl
                )) + [
                    call(Fore.RED, "Missing requirements.txt"), call(Fore.YELLOW, "[DRY RUN] Creating empty requirements.txt") ]
            sys.argv = ['apply.py', '--dry-run', '--interactive', str(td)]
            apply.main()

            self.assertFalse( list(td.iterdir()) )  # dir is still empty
            # apply to empty dir
            exp_printmsg += [
                call(Fore.YELLOW, f"Copying {ef.relative_to(td)} to {ef}") for ef in exp_files ] + [
                call(Fore.YELLOW, "Creating empty requirements.txt") ]
            sys.argv = ['apply.py', str(td)]
            apply.main()
            cmpthem()

            # apply to existing dir
            exp_printmsg += [
                call(Fore.GREEN, f"Identical: {ef.relative_to(td)}") for ef in exp_main ] + [
                call(Fore.GREEN, f"Identical (optional): {ef.relative_to(td)}") for ef in exp_optnl ]
            apply.main()
            cmpthem()

            # interactive
            exp_printmsg += [
                call(Fore.GREEN, f"Identical: {ef.relative_to(td)}") for ef in exp_main ] + [
                call(Fore.GREEN, f"Identical (optional): {ef.relative_to(td)}") for ef in exp_optnl ]
            sys.argv = ['apply.py', '--interactive', str(td)]
            apply.main()

            # tests with modifications in target
            # file doesn't exist
            exp_main[0].unlink()  # .vscode/extensions.json
            # existing file is different
            with exp_main[-1].open('ab') as fh:  # pyproject.toml
                fh.write(b'\n# foo\n')
            # optional file doesn't exist
            exp_optnl[-1].unlink()  # dev/local-actions.sh
            # normal
            exp_diff += [ call(sd/exp_main[-1].relative_to(td), exp_main[-1], ignore_ws=False, try_git=True ) ]
            exp_printmsg += [
                call(Fore.YELLOW,  f"[DRY RUN] Copying {exp_main[0].relative_to(td)} to {exp_main[0]}") ] + [
                call(Fore.GREEN,   f"Identical: {ef.relative_to(td)}") for ef in exp_main[1:-1] ] + [
                call(Fore.MAGENTA, f"Different: {exp_main[-1].relative_to(td)}") ] + [
                call(Fore.GREEN,   f"Identical (optional): {ef.relative_to(td)}") for ef in exp_optnl[:-1] ] + [
                call(Fore.CYAN,    f"Not copying optional {exp_optnl[-1].relative_to(td)}") ]
            sys.argv = ['apply.py', '--dry-run', str(td)]
            apply.main()
            # interactive runs (also test the passthru of do_diff args from cmdline)
            mock_yn.return_value = False
            exp_diff += [ call(sd/exp_main[-1].relative_to(td), exp_main[-1], ignore_ws=False, try_git=False) ]
            exp_prompt_yn += [call('Copy?'), call('Overwrite?'), call('Copy?')]
            exp_printmsg += [
                call(Fore.RED,     f"Missing {exp_main[0].relative_to(td)}") ] + [
                call(Fore.GREEN,   f"Identical: {ef.relative_to(td)}") for ef in exp_main[1:-1] ] + [
                call(Fore.MAGENTA, f"Different: {exp_main[-1].relative_to(td)}") ] + [
                call(Fore.GREEN,   f"Identical (optional): {ef.relative_to(td)}") for ef in exp_optnl[:-1] ] + [
                call(Fore.CYAN,    f"Optional {exp_optnl[-1].relative_to(td)}") ]
            sys.argv = ['apply.py', '--dry-run', '--interactive', '--no-git-diff', str(td)]
            apply.main()
            mock_yn.return_value = True
            exp_diff += [ call(sd/exp_main[-1].relative_to(td), exp_main[-1], ignore_ws=True,  try_git=True ) ]
            exp_prompt_yn += [call('Copy?'), call('Overwrite?'), call('Copy?')]
            exp_printmsg += [
                call(Fore.RED,     f"Missing {exp_main[0].relative_to(td)}") ] + [
                call(Fore.YELLOW,  f"[DRY RUN] Copying {exp_main[0].relative_to(td)} to {exp_main[0]}")] + [
                call(Fore.GREEN,   f"Identical: {ef.relative_to(td)}") for ef in exp_main[1:-1] ] + [
                call(Fore.MAGENTA, f"Different: {exp_main[-1].relative_to(td)}") ] + [
                call(Fore.YELLOW,  f"[DRY RUN] Copying {exp_main[-1].relative_to(td)} to {exp_main[-1]}") ] + [
                call(Fore.GREEN,   f"Identical (optional): {ef.relative_to(td)}") for ef in exp_optnl[:-1] ] + [
                call(Fore.CYAN,    f"Optional {exp_optnl[-1].relative_to(td)}") ] + [
                call(Fore.YELLOW,  f"[DRY RUN] Copying {exp_optnl[-1].relative_to(td)} to {exp_optnl[-1]}") ]
            sys.argv = ['apply.py', '--dry-run', '--interactive', '--ignore-all-space', str(td)]
            apply.main()

            # error case: target is not a directory
            sys.argv = ['apply.py', str(td/'pyproject.toml')]
            with self.assertRaises(NotADirectoryError):
                apply.main()
            # error case: more than one alternative
            (td/'dev'/'requirements.txt').unlink()
            (td/'requirements-dev.txt').touch()
            (td/'dev'/'requirements-dev.txt').touch()
            sys.argv = ['apply.py', str(td)]
            with self.assertRaises(RuntimeError):
                apply.main()
            (td/'requirements-dev.txt').unlink()
            (td/'dev'/'requirements-dev.txt').unlink()
            # error case: file is a directory
            (td/'pyproject.toml').unlink()
            (td/'pyproject.toml').mkdir()
            with self.assertRaises(OSError):  # pragma: no branch
                apply.main()

        self.assertEqual( mock_exit.call_args_list,     [call(0)]*9   )
        self.assertEqual( mock_ih.call_args_list,       [call()]*12   )  # incl. 3 error cases
        self.assertEqual( mock_fix.call_args_list,      [call()]*12   )
        self.assertEqual( mock_diff.call_args_list,     exp_diff      )
        self.assertEqual( mock_yn.call_args_list,       exp_prompt_yn )
        self.assertEqual( mock_printmsg.call_args_list, exp_printmsg  )
