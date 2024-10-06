"""Tests for ``Makefile``.

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
import unittest
import re
import shutil
import subprocess
from pathlib import Path
from itertools import tee, chain
from typing import Optional
from tempfile import TemporaryDirectory

def pairwise(iterable):
    """:func:`itertools.pairwise` was added in 3.10, this is a shim"""
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

def dollar_replace(inp :str, trans :dict[str, str]):
    """Replace ``$$`` and ``$(...)`` sequences as they would appear in Makefile recipes"""
    replacements :list[tuple[int, int, str]] = []
    wasdollar = False
    stack :list[tuple] = []
    for i, c in enumerate(inp):
        if wasdollar:
            if c=='$':
                if not any(stack):  # if not inside $()
                    replacements.append( (i-1,i,'') )
            elif c=='(':
                assert i>0
                stack.append( (i-1,) )
            else:
                raise ValueError(f"Unknown sequence ${c}")
            wasdollar = False
        else:
            if c=='$':
                wasdollar = True
            elif c=='(':
                stack.append( () )
            elif c==')':
                if st := stack.pop():
                    if not any(stack):  # if not inside $()
                        replacements.append( ( st[0], i+1, trans[ inp[st[0]+2:i].strip() ] ) )
    if stack:
        raise IndexError("unclosed paren")
    replacements.sort(key=lambda x: x[0], reverse=True)
    assert all( y[0]<x[0] and y[1]<=x[0] for x,y in pairwise(replacements) )  # double-check that there are no overlaps
    out = inp
    for si,ei,r in replacements:
        out = out[:si] + r + out[ei:]
    return out

class MakefileTestCase(unittest.TestCase):

    def test_dollar_replace(self):
        self.assertEqual(
            dollar_replace( '(x) $(y) $$( $(z) ) $(y)$(y) $$$$', { 'y':'A', 'z':'B' } ),
            '(x) A $( B ) AA $$' )
        self.assertEqual(
            dollar_replace('$(x) $$$( y (a(b)(c)) $$d $(z) )', {'x':'C', 'y (a(b)(c)) $$d $(z)':'D'} ),
            'C $D' )
        with self.assertRaises(IndexError):
            dollar_replace('(()', {})
        with self.assertRaises(IndexError):
            dollar_replace('())', {})
        with self.assertRaises(ValueError):
            dollar_replace('$x', {})
        with self.assertRaises(ValueError):
            dollar_replace('($)', {})
        with self.assertRaises(KeyError):
            dollar_replace('$(x)', {'y':'z'})

    # NOTE this test is really just for development, where we have to watch the test output to make sure this test is being run.
    # GitHub Action Runners don't have shellcheck on Windows or macOS, which is why we have to say "no cover" for those (for now).
    #TODO Later: Require shellcheck tests on the local machine.
    @unittest.skipIf(condition=shutil.which('shellcheck') is None, reason='only when shellcheck is installed')
    def test_makefile_shellcheck(self):  # pragma: no cover
        """Run ``shellcheck`` on the individual Makefile recipes"""
        makefile = Path(__file__).parent.parent/'Makefile'
        with ( makefile.open(encoding='UTF-8') as ifh,
               TemporaryDirectory() as tdir ):
            td = Path(tdir)
            cur_target :Optional[str] = None
            recipe :list[str] = []
            files :list[Path] = []
            # process a recipe
            def recipe_done():
                if not recipe:
                    return
                assert cur_target
                # munge the recipe as make would
                recipe[0] = recipe[0].removeprefix('@')
                rec = ''.join( ln+'\n' for ln in chain(['#!/bin/bash'],recipe) )
                recipe.clear()
                rec = dollar_replace(rec, {
                    'PYTHON3BIN': 'python',
                    'foreach x,$(requirement_txts),-r $(x)':'-r requirements.txt -r dev/requirements.txt',
                    'perm_checks': './apply.py ./tests .gitignore .vscode .github',
                    'py_code_locs': './apply.py tests',
                    'requirement_txts': 'requirements.txt dev/requirements.txt',
                    'MAKEFILE_LIST': makefile.as_posix(),
                })
                # write to output file
                files.append( td/(cur_target+'.sh') )
                with files[-1].open('x', encoding='UTF-8', newline='\n') as ofh:
                    ofh.write(rec)
            # scan the Makefile
            seen_shell = False
            seen_oneshell = False
            for line in ifh:
                if line.lstrip().startswith('SHELL'):
                    self.assertTrue(re.fullmatch(r'^\s*SHELL\s*=\s*/bin/bash\s*$', line), 'SHELL is /bin/bash')
                    seen_shell = True
                elif re.fullmatch(r'^\s*\.ONESHELL:(?:\s+\#.*)?\s*$', line):
                    seen_oneshell = True
                elif cur_target is not None and line.startswith('\t'):
                    recipe.append( line.removeprefix("\t").removesuffix("\n") )
                elif m := re.match(r'^([-\w]+):', line):
                    recipe_done()
                    cur_target = m.group(1)
            recipe_done()
            # Run checks after scanning Makefile and getting recipes
            self.assertTrue(seen_shell, '"SHELL = /bin/bash" seen')
            self.assertTrue(seen_oneshell, '".ONESHELL:" directive seen')
            rv = subprocess.run(['shellcheck']+[ str(f) for f in files ], check=False)
            self.assertEqual( rv.returncode, 0 )
