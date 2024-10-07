Hauke's Python Template
=======================

This is my template Python project.
It can be applied to a project (and diffed with existing files) with the `apply.py` script.

Note that `Makefile` and `.vscode` settings can and probably will need to be adjusted
for individual projects, while I think the Python linting/styling settings in
`pyproject.toml` should be kept synchronized across my projects.

Some additional stuff elsewhere:
- Development notes for releasing to PyPI:
  [simple-perms](https://github.com/haukex/simple-perms/blob/main/dev/DevNotes.md) and
  [igbpyutils](https://github.com/haukex/igbpyutils/blob/main/dev/Notes.md) (older)
- `README.md` generation by Sphinx:
  [simple-perms](https://github.com/haukex/simple-perms) and
  [unzipwalk](https://github.com/haukex/unzipwalk)'s `Makefile`s and `docs` folders
- *Read the Docs* and Sphinx documentation generation:
  [igbpyutils](https://github.com/haukex/igbpyutils/)

Dependencies
------------

- To install all Python requirements, just do `make installdeps`.

- To install `pyright`, install Node as per
  <https://github.com/haukex/toolshed/blob/main/notes/TypeScript.md>
  and then `npm install -g pyright`.

- Mypy may require a few `types-*` packages, just do `mypy --install-types`
  (look for "Hint"s in its output).

- On non-Windows systems, the `nix-checks` target requires `findmnt`
  (on Ubuntu, package `util-linux`).

- `find` and `perl` (5.14+) are typically preinstalled in all environments I work in.

### Windows

- Git Bash

- `make` as per <https://github.com/haukex/toolshed/blob/main/notes/Python.md#windows-notes>

- `shellcheck` can be downloaded as a `zip` containing a single `exe` from
  <https://github.com/koalaman/shellcheck#installing>
  and simply placed in a location in `PATH` (such as `~/bin`)

### Others

- In case it's needed, `jq` can be downloaded as a single `exe` from
  <https://jqlang.github.io/jq/> and installed like `shellcheck` above


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
