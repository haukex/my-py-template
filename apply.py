#!/usr/bin/env python
"""Script to apply this template repository to a directory.

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
import re
import shutil
import filecmp
import argparse
import subprocess
from pathlib import Path
from itertools import chain
from difflib import unified_diff
from typing import NamedTuple, Union
from collections.abc import Iterable, Generator
from colorama import just_fix_windows_console, Fore, Back, Style
from more_itertools import unique_everseen
from igbpyutils.error import init_handlers
from igbpyutils.file import Filename

class FileEntry(NamedTuple):
    path :Path
    #: if None, don't search for alternatives; if empty, search recursively for file of the same name
    alt_names :Union[None, tuple[str, ...]]
    optional :bool = False

class FileActionItem(NamedTuple):
    name :Path
    source :Path
    dest :Path
    optional :bool

FILES: tuple[FileEntry, ...] = (
    FileEntry(Path('.vscode','extensions.json'), None),
    FileEntry(Path('.vscode','settings.json'), None),
    FileEntry(Path('dev','requirements.txt'), ('requirements-dev.txt',)),
    FileEntry(Path('.gitignore'), None),
    FileEntry(Path('Makefile'), None),
    FileEntry(Path('pyproject.toml'), None),
    FileEntry(Path('tests','__init__.py'), None, optional=True),
    FileEntry(Path('tests','test_dummy.py'), None, optional=True),
    FileEntry(Path('.github','workflows','tests.yml'), None, optional=True),
    FileEntry(Path('dev','local-actions.sh'), None, optional=True),
    FileEntry(Path('dev','isolated-dist-test.sh'), None, optional=True),
)

def do_diff(fromfile :Filename, tofile :Filename, *, ignore_ws :bool=False, try_git :bool=True):
    if try_git:
        cmd = ['git','--no-pager','diff','--no-index','--color-words'] \
               + ( ['--ignore-all-space'] if ignore_ws else [] ) \
               + ['--',str(fromfile),str(tofile)]
        try:
            rv = subprocess.run(cmd, check=False)
            if rv.returncode not in (0,1):
                rv.check_returncode()
        except (subprocess.SubprocessError, OSError):
            pass  # fall back to our diff
        else:
            return
    def collapsews(inp :Iterable[str]) -> Generator[str, None, None]:
        was_blank = False
        for line in inp:
            is_blank = not line or line.isspace()
            if is_blank:
                if not was_blank:
                    yield ''
            else:
                yield re.sub(r'\s+',' ',line.strip())
            was_blank = is_blank
    with open(fromfile, encoding='UTF-8') as fh:
        from_lines = list( collapsews(fh) if ignore_ws else (line.removesuffix('\n') for line in fh) )
    with open(tofile, encoding='UTF-8') as fh:
        to_lines = list( collapsews(fh) if ignore_ws else (line.removesuffix('\n') for line in fh) )
    #TODO Later: Could sync with https://github.com/haukex/dotfiles/blob/main/apply.py
    for line in unified_diff(from_lines, to_lines, fromfile=str(fromfile), tofile=str(tofile), lineterm=''):
        if line[0:3] in ('+++','---'):
            style = Style.BRIGHT
        elif line.startswith('@@'):
            style = Fore.CYAN
        elif line.startswith('-'):
            style = Fore.RED
        elif line.startswith('+'):
            style = Fore.GREEN
        else:
            style=''
        print(style, line, Style.RESET_ALL if style else '', sep='')

def prompt_yn(msg :str) -> bool:
    return input(f"{Fore.WHITE}{Back.RED}==>{Style.RESET_ALL} {msg} [yN] ").lower().startswith('y')

def print_msg(color :str, msg :str):
    # Note the flush is apparently needed if piping to `less -R`
    print(f"{Style.BRIGHT}{color}##### {msg} #####{Style.RESET_ALL}", flush=True)

def do_copy(fact :FileActionItem, *, dry_run :bool):
    print_msg(Fore.YELLOW, f"{'[DRY RUN] ' if dry_run else ''}Copying {fact.name} to {fact.dest}")
    if not dry_run:
        fact.dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(fact.source, fact.dest)

def main():
    init_handlers()
    just_fix_windows_console()
    parser = argparse.ArgumentParser(description='Python Template Applicator')
    parser.add_argument('-w', '--ignore-all-space', help="ignore all whitespace in diff", action="store_true")
    parser.add_argument('-G', '--no-git-diff', help="don't use git diff, use builtin", action="store_true")
    parser.add_argument('-i', '--interactive', help="interactively propmt to make changes", action="store_true")
    parser.add_argument('-n', '--dry-run', help="don't actually copy files", action="store_true")
    parser.add_argument('-o', '--optional', help="Treat optional files as required (on when targetdir is empty)", action="store_true")
    parser.add_argument('targetdir', help="the target directory")
    args = parser.parse_args()

    # first, locate all the files
    srcpath = Path(__file__).parent
    dstpath = Path(args.targetdir).resolve(strict=True)
    if not dstpath.is_dir():
        raise NotADirectoryError(args.targetdir)
    dst_children = list(dstpath.iterdir())
    dst_was_empty = not dst_children or len(dst_children)==1 and dst_children[0].is_dir() and dst_children[0].name == '.git'
    if dst_was_empty:
        args.optional=True
    flist :list[FileActionItem] = []
    for fent in FILES:
        srcf = srcpath/fent.path
        assert srcf.is_file()
        dstf = dstpath/fent.path
        # locate the file
        if not dstf.exists() and fent.alt_names is not None:
            alts = tuple(unique_everseen(chain.from_iterable( dstpath.rglob(name) for name in (fent.path.name,)+fent.alt_names )))
            if len(alts)>1:
                raise RuntimeError(f"Found more than one alternative for {fent.path}: {alts}")
            if alts:
                dstf = alts[0]
        if dstf.exists() and not dstf.is_file():
            raise OSError(f"Not a file: {srcf}")
        flist.append( FileActionItem(name=fent.path, source=srcf, dest=dstf, optional=fent.optional) )

    # then process the files
    for fact in flist:
        optnl = ' (optional)' if fact.optional else ''
        if fact.dest.exists():
            if filecmp.cmp(fact.source, fact.dest, shallow=False):
                print_msg(Fore.GREEN, f"Identical{optnl}: {fact.name}")
            else:
                print_msg(Fore.MAGENTA, f"Different{optnl}: {fact.name}")
                do_diff(fact.source, fact.dest, ignore_ws=args.ignore_all_space, try_git=not args.no_git_diff)
                if args.interactive and prompt_yn("Overwrite?"):
                    do_copy(fact, dry_run=args.dry_run)
        elif fact.optional and not args.optional:
            if args.interactive:
                print_msg(Fore.CYAN, f"Optional {fact.name}")
                if prompt_yn("Copy?"):
                    do_copy(fact, dry_run=args.dry_run)
            else:
                print_msg(Fore.CYAN, f"Not copying optional {fact.name}")
        else:
            if args.interactive:
                print_msg(Fore.RED, f"Missing{optnl} {fact.name}")
                if prompt_yn("Copy?"):
                    do_copy(fact, dry_run=args.dry_run)
            else:
                do_copy(fact, dry_run=args.dry_run)

    # when initializing an empty directory, create an empty requirements.txt
    req_txt = dstpath/'requirements.txt'
    if dst_was_empty and not req_txt.exists():
        do_it = False
        if args.interactive:
            print_msg(Fore.RED, f"Missing {req_txt.name}")
            if prompt_yn("Create empty?"):
                do_it = True
        else:
            do_it = True
        if do_it:
            print_msg(Fore.YELLOW, f"{'[DRY RUN] ' if args.dry_run else ''}Creating empty {req_txt.name}")
            if not args.dry_run:
                req_txt.touch()

    parser.exit(0)

if __name__=='__main__':
    main()  # pragma: no cover
