Development Notes
=================

This document is currently referenced by:
- <https://github.com/haukex/simple-perms/blob/main/dev/DevNotes.md>
- <https://github.com/haukex/unzipwalk/blob/main/dev/DevNotes.md>
- <https://github.com/haukex/coverage-simple-excludes/blob/main/dev/DevNotes.md>
- <https://github.com/haukex/igbpyutils/blob/main/dev/DevNotes.md>
- <https://github.com/haukex/pytoa5/blob/main/dev/DevNotes.md>

Development Environment
-----------------------

- [ ] Development on Linux (preferred; some projects can be developed on Windows or macOS too)
- [ ] In order to run full tests locally, install multiple Python versions with `python3.X`
  aliases, e.g as per <https://github.com/haukex/toolshed/blob/main/notes/Python.md>,
  and use the lowest supported version for normal development to catch any backcompat issues.
- [ ] `python3.9 -m venv .venv3.9` and `. .venv3.9/bin/activate`
  - [ ] In some cases (DevPod), placing the venv at e.g. `~/.venvs/project-name/.venv3.9` is better
- [ ] `make installdeps` - set up dev env
- [ ] Installing Pyright (if you don't have Node already):
  - [ ] Install Node as per <https://github.com/haukex/toolshed/blob/main/notes/JavaScript.md>
  - [ ] `npm install -g pyright`

Testing
-------

- [ ] `make` - tests incl. lint & coverage
- [ ] `dev/local-actions.sh .` - tests on all Python versions

Release Preparation
-------------------

- [ ] Check:
  - [ ] `make tasklist`
  - [ ] GitHub Issues
  - [ ] Git stash
  - [ ] Whether the Python versions in `dev/local-actions.sh` and the GitHub Actions need updating
- [ ] Spellcheck all documentation
- [ ] Generate documentation (dependent on the project) and check its formatting
- [ ] Bump version number in `pyproject.toml`
- [ ] Update Changelog

Releasing
---------

- [ ] `git commit` and `git push` if needed
- [ ] watch GitHub Actions
- **The following steps should be done on Linux with an FS with reliable file permissions!**
- [ ] `make build-check` - builds and checks `dist/*.tar.gz`
- [ ] `tar tzvf dist/*.tar.gz` to inspect the package
- [ ] `git tag vX.X.X` and `git push --tags`
- [ ] `python -m twine upload dist/*.tar.gz`
- [ ] New GitHub Release: Title "project-name vX.X.X", body from the Changelog,
  link to PyPI (specific version); attach `.tar.gz` to release
- [ ] `pip install --upgrade project-name` and run any command-line tools
  (test installation of package and command-line scripts)
- [ ] `git clean -dxf dist *.egg-info`
- [ ] Add placeholder for next version to Changelog
