# Developer Guide


## Table of Contents
- [Overview](#overview)
- [Contributing and Communicating](#contributing-and-communicating)
- [Project Directories](#project-directories)
- [Testing](#testing)
- [Operator Run Ladder](#operator-run-ladder)
- [Cross-Repository Refactoring](#cross-repository-refactoring)
- [Python Package Entry Point](#python-package-entry-point)
- [Makefile Targets](#makefile-targets)
- [Developing Documentation](#developing-documentation)
- [Packaging and Deployment](#packaging-and-deployment)
- [Branch Protection](#branch-protection)
- [Maintainer Guide](#maintainer-guide)
- [Branch and Documentation Deployment](#branch-and-documentation-deployment)
- [GitHub Copilot](#github-copilot)
- [Managing Logs and Caches](#managing-logs-and-caches)
- [Files and Directories Excluded from Version Control](#files-and-directories-excluded-from-version-control)


## Overview
The Climate-Action-GABM developer guide provides guidance for developers some of which are also maintainers.

Please follow the [Developer Quick Start Guide](DEV_QUICKSTART.md) to get set up to contribute as a developer.

In the rest of the document "you" means you as a Climate-Action-GABM developer.


## Contributing and Communicating
Please follow the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

For the time being, please communicate by commenting on or raising new [Climate-Action-GABM Repository Issues](https://github.com/compolis/Climate-Action-GABM/issues).

You should have forked the [Climate-Action-GABM Repository](https://github.com/compolis/Climate-Action-GABM) to your own GitHub account.

The general workflow for contributing is to:
- Create and check out a new local branch:

```bash
git branch my_feature
git checkout my_feature
```

- Make changes:
  - For each Python file edited, please adjust the Metadata at the top of the file by:
    - Adding your details to the `__author__` list
    - Incrementing the `__version__`
  - Update the [Change Log](CHANGE_LOG.md) with a summary of your changes.
- Commit changes with a clear message. For example:

```bash
git add .
git commit -m "Clear message that explains changes." 
```

- Ensure tests pass and documentation builds before submitting a PR:

```bash
make test
make docs
```

- Push to your Fork, For example:

```bash
git push origin my_feature
```

- Open a PR on GitHub to merge your `my_feature` branch into the the `main` branch of the upstream Climate-Action-GABM Repository.
  - Please refer to any related issues in the PR comments.
- The PR will be reviewed and once the review is complete, the changes will be merged.


## Project Directories
The root project directory contains documentation and files needed for building and deploying. The sub-diretories include: 
- `data/`: For data including log files
- `dist/`: Output directory for built distributions.
- `documentation/`: Authoritative long-form documentation: maintained guides,
  research material, archives, and presentations. Start at
  [documentation/README.md](documentation/README.md).
- `docs/`: Sphinx configuration/navigation plus temporary staged content and
  generated site output. Do not author new usage guides here; see
  [Developing Documentation](#developing-documentation).
- `scripts/`: Utility scripts organised by purpose:
  - `scripts/dev/`: developer workflow helpers used by Makefile targets.
  - `scripts/hpc/`: cluster launch/ops scripts (Aire and Calder profiles).
- `src/`: Python source code
- `tests/`: Test suite for src
- `venv-build-test/`: For temporary virtual environments created for testing.


## Testing

Climate-Action-GABM uses [pytest](https://docs.pytest.org/) for unit and integration tests. The unit test suite is located in the `tests/` directory, mirroring the module structure.

### Running Tests

Run most tests with:
  ```bash
  make test
  ```
or:
  ```bash
  pytest
  ```

### Adding Tests

Please add or update tests when modifying or adding features. Aim for high test coverage to catch regressions and ensure code reliability.

### Test Workflow

- PRs should pass the test workflow before being merged.
- See `.github/workflows/test.yml` for Continuous Integration (CI) details.

## Operator Run Ladder

When validating behaviour changes, prefer fast, bounded evidence first:

1. **Config canary (local, no provider calls)**  
   `PYTHONPATH=src python3 -m cag --preset smoke --dry-run`
2. **Short smoke run**  
   Validate run output shape and logs before scaling duration/population.
3. **Substantive runs on HPC**  
   Use Aire as the primary path; use Calder where needed for portability checks.

HPC references:
- [Running_On_HPC_Systems.md](documentation/guides/hpc/Running_On_HPC_Systems.md)
- [Aire quickstart](documentation/guides/hpc/Aire_Quickstart.md)
- [Aire HPC repo primer](documentation/guides/hpc/Aire_HPC_repo_primer.md)

Do not treat long local-LLM runs as the default contributor validation loop.
Use them intentionally when diagnosing local runtime behaviour or privacy-bound
execution paths.


## Cross-Repository Refactoring

For work that moves reusable CAG capabilities into GABM, follow the
[CAG to GABM Refactor Plan](documentation/planning/GABM_Refactor_Plan.md). It records the published
dependency audit, ownership boundaries, implementation sequence, and validation
gates; the [roadmap](documentation/planning/ROADMAP.md#cag-to-gabm-refactor-track) records the strategic
goal.

Establish deterministic integration evidence before runtime edits. Develop
generic APIs and tests in GABM, retain CAG-specific research logic and tests
here, and wire one bounded extraction at a time. Separate the fast development
loop from packaging validation and release: a small extraction does not require
an immediate PyPI release.
Do not change prompts, random-number usage, cache policy, output schemas, or
checkpoint/resume behaviour incidentally during extraction.

### Local development loop

Use adjacent CAG and GABM checkouts on focused feature branches. From the CAG
repository root, create a dedicated integration environment so the normal `cag`
environment can retain the published dependency:

```bash
conda create --name cag-integration --clone cag
conda activate cag-integration
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install -e ../GABM
PYTHONPATH=src:scripts python -m pytest -q
```

The relative path assumes the framework checkout is named `GABM` beside CAG;
adjust it for your workspace. Install CAG's requirements **before** the editable
framework: rerunning them afterward can replace it with the published pin.
An editable installation exposes Python source edits immediately. Reinstall
after dependency or packaging changes; rebuild any compiled components.

Check which framework is actually imported:

```bash
python -c "import gabm; print(gabm.__file__)"
git -C ../GABM rev-parse HEAD
git -C ../GABM status --short
```

Record both repository commits and any uncommitted changes with test evidence.
Package version metadata alone does not distinguish an unreleased checkout
from the published artifact carrying the same version.
Run focused tests during each change, then relevant full suites before review.
Keep small commits/PRs; do not combine population construction, survey execution,
transport, memory, and inheritance changes into one refactor.

### Reproducible integration outside the workspace

For CI, collaborators, or HPC, use an exact committed GABM revision instead of
a moving branch or a developer's editable directory. For example, after
replacing `FULL_COMMIT_SHA` with the full commit hash:

```bash
python -m pip install \
  "gabm @ git+https://github.com/compolis/gabm.git@FULL_COMMIT_SHA"
```

Use the repository or fork containing that commit and an approved authentication
method; never put credentials in requirements or documentation. This needs Git
and access to that repository. As with the editable installation, apply the
override after CAG's normal dependencies and verify the imported package.
For automated installs, a separate integration requirements input may replace
the published GABM entry with this direct reference. Do not combine incompatible
PyPI and Git requirements for `gabm` in the same resolver invocation.

A commit reference captures committed code, not local edits, and does not lock
the entire environment. Record Python/dependency versions and run configuration
as well. Test the same deterministic CAG reference run; live LLM smoke tests are
supplementary evidence, not exact equivalence gates.

### Packaging milestones and batched releases

Merge stable, backward-compatible GABM additions after review without requiring
a release for every PR. Keep dependent CAG work on a feature/integration branch
while several related slices mature. CAG `main` must remain installable using
its declared dependencies: do not merge code requiring an unpublished API while
its manifests still pin a release that lacks it.

At meaningful milestones, build a GABM wheel and install it in a separate
validation environment **instead of** the editable/Git dependency. Run CAG
without GABM's source directory on `PYTHONPATH` and verify the import comes from
the installed wheel. This tests packaging without publishing. Do not upload a
development wheel under an already published version.

Publish when a coherent, validated capability is ready, not after every small
change. Then update all CAG production manifests, validate the actual PyPI
artifact without source overrides, and merge the dependent CAG integration.
Keep the original golden fixtures unless an intentional behaviour change is
separately approved.

Update the [refactor plan](documentation/planning/GABM_Refactor_Plan.md) after each slice with commits,
test/comparison evidence, and whether validation used editable source, an exact
Git revision, a local wheel, or a published artifact. These are distinct gates;
development success is not published-package acceptance.


## Python Package Entry Point

The main entry point for the Climate-Action-GABM package is `src/cag/__main__.py`. This allows the application to be run using:

	python3 -m cag

This approach is preferred over directly running a script (like `run.py`) as:
  - It enables Python to treat `cag` as a package, ensuring imports work correctly.
  - It is the standard way to provide a command-line entry point for Python packages.
  - It makes the project ready for distribution and installation.

The `__main__.py` file is executed when you run `python3 -m cag` from the project root (with `src` on the Python path). If you need to add or change the main application logic, edit `src/cag/__main__.py`.

Please see the [Python Packaging documentation](https://docs.python.org/3/library/__main__.html) for information about Python packaging.


## Makefile Targets

The root directory contains a [Makefile](https://www.gnu.org/software/make/manual/make.html#Introduction). This is set up to automate tasks using [GNU Make](https://www.gnu.org/software/make). This section explains the rules or targets in the Makefile. Please ensure any changes to the Makefile are platform agnostic.


### Target Chaining, DRY, and Consistency

For maintainability, all Makefile targets that depend on other build steps should use Make's built-in dependency chaining (e.g., `gh-pages-deploy: docs`) rather than manually invoking `$(MAKE)` or shelling out to `make` within a target. This ensures:
- Each target is only responsible for its own logic.
- Consistency: all targets use the same build steps, and changes to one target (like `docs`) automatically propagate to dependents (like `gh-pages-deploy`). The following is a presentation of the Makefile rules/targets:

| Target         | Usage/Description                                                                 |
|--------------- |----------------------------------------------------------------------------------|
| `make help`    | Show available Makefile commands                                                  |
| `make test`    | Run all tests (pytest)                                                            |
| `make docs`    | Build documentation (Sphinx) and clean auto-copied docs assets                    |
| `make docs-make` | Build documentation (Sphinx)                                                      |
| `make docs-clean` | Remove auto-copied documentation files from docs/                              |
| `make gh-pages-deploy` | Build and deploy documentation to GitHub Pages (runs `scripts/dev/gh-pages-deploy.py`) |
| `make clean`   | Remove build/test artifacts and Python caches                                     |
| `make clear-caches` | Delete all LLM caches and model lists (for a clean slate)                    |
| `make git-clean` | Clean up merged local branches and prune deleted remotes                        |
| `make git-prune-local` | Delete local branches merged into `main` (except `main`/`gh-pages`)      |
| `make git-prune-origin` | Delete `origin` branches merged into `origin/main` (except `main`/`gh-pages`) |
| `make sync`    | Sync main branch with upstream                                                    |
| `make sync-feature BRANCH=release/0.2.0` | Sync and rebase a feature/release branch onto main     |
| `make release VERSION=x.y.z BRANCH=release/x.y.z` | Tag and push a release (platform-agnostic)     |
| `make delete-release VERSION=x.y.z` | Delete a release tag locally and on remotes (origin, upstream) |
| `make build`    | Build a distribution package for PyPI (python -m build)                            |
| `make build-test` | Build and test install the package in a fresh venv                               |
| `make pypi-release` | Upload the built package to PyPI (twine upload dist/*)                         |
| `make testpypi-release` | Upload the built package to TestPyPI (twine upload --repository testpypi dist/*) |
| `make bump-version` | Bump the project version everywhere (patch by default; use `make bump-version part=minor` or `part=major` for other bumps). Uses bump2version and updates all relevant files. |
| `make run-local` | Run cag using local source (PYTHONPATH=src) |
| `make run-installed` | Run cag using installed package |


Makefile-target helper scripts live under `scripts/dev/`.

The `delete-release` target automates deleting a release tag locally and on both remotes (origin, upstream).

Please refer to the Makefile for full details.


## Developing Documentation

### Authored sources and Sphinx staging

Create and maintain prose documentation outside `docs/`. Keep project
entry points, contributor guides, the roadmap, and change history in the
repository root. Longer-form authored material belongs in `documentation/`:

- `documentation/guides/`: maintained usage, code, configuration, and HPC guides.
- `documentation/research/`: design history, research notes, result reports,
  survey documentation, and literature notes.
- `documentation/archive/`: superseded guides and historical planning snapshots.
- `documentation/presentations/`: authored presentation assets such as the
  standalone HTML handover deck.

These categories already contain authored sources. Use
[documentation/README.md](documentation/README.md) as the reader-facing index.
Keep project entry points, contribution instructions, release history, and
maintained project plans in the root as described under
[Root documents](#root-documents). Do not duplicate those documents under
`documentation/`.

### What belongs in `docs/`

`docs/` is the Sphinx site workspace, not a second source tree for prose.
It contains a deliberate mixture of maintained build inputs and disposable
build products:

| Content | Edit directly? | Commit? |
|---|---|---|
| [docs/conf.py](docs/conf.py): Sphinx configuration | Yes | Yes |
| [docs/index.md](docs/index.md): site navigation/toctrees | Yes | Yes |
| [docs/api.rst](docs/api.rst): maintained API directives | Yes | Yes |
| Intentionally maintained Sphinx templates or site assets, if added | Yes | Yes |
| Copies staged from the root or `documentation/`, including renamed pages and `supplementary_docs/` pages | No; edit the authoritative source | No |
| Dependency mirrors generated from the root requirements | No; edit the requirements | No |
| Newly generated `docs/_autosummary/` stubs | No, not as prose sources | No |
| Staged presentation assets in `docs/_extra/` | No; edit `documentation/presentations/` | No |
| Rendered HTML and other build output in `docs/_build/` | No | No |

Some autosummary stubs are tracked legacy generated files. Leave unrelated
changes to them out of commits; deliberately update/remove tracked stubs only
when changing their API/navigation ownership. The historical
[docs/index.rst](docs/index.rst) is excluded from the build and is not the active
site index.

**Practical rule:** to change instructions, research prose, or a presentation,
edit its root or `documentation/` source. To change how the site is built or
navigated, edit the maintained Sphinx inputs in `docs/`. Never copy a guide
there manually and treat both copies as editable sources.

### Staging authored content into the site

The Aire guides, code tour, local LLM setup, prompts/personas V2, output guide,
and configuration guide now have authoritative sources in
`documentation/guides/`. Their original filenames under `docs/` are temporary
staging copies only. The design history, research notes, results report, and
survey documentation now live in `documentation/research/` and are staged
under their original page names. Preserve their research provenance and
historical claims during ownership moves; the design history is not a current
model specification. Supplementary literature/parameterisation notes also live
in `documentation/research/`. Superseded prompts/code tours, older Aire article
notes, and issue-planning snapshots live in `documentation/archive/`.
Archive placement preserves context; it does not establish that all planned
items were completed or that older cluster advice remains valid.
Their existing `supplementary_docs/` site paths are retained by staging.
The documentation index is authored in `documentation/README.md` and staged as
`docs/documentation_index.md`. Runtime and developer dependency pages are
generated from the root requirement manifests and cleaned after the build;
never edit or commit those mirrors.

The handover deck lives in `documentation/presentations/`. Staging copies its
HTML bytes to `docs/_extra/`; Sphinx's `html_extra_path` publishes it at
`cag_handover_deck.html` beside the built index. Cleanup removes the staged
asset, not its authored source or published output. It is a standalone
presentation, not a generated API page; its external Google Fonts dependency
is retained.

For a new authored Markdown document intended for the Sphinx site:

1. Create the authoritative file in its agreed source location and link it from an
   appropriate entry-point document.
2. Add its repository-relative path to `DOC_FILES` in
   [scripts/dev/docs_assets.py](scripts/dev/docs_assets.py), the shared copy/cleanup
   manifest. Do not register an authored file that exists only in `docs/`:
   cleanup would delete it. For a nested source, add a `STAGED_NAMES` entry
   mapping its source path to the desired filename under `docs/`. Keep staged
   filenames unique. The Aire guides demonstrate this mapping while retaining
   their existing Sphinx page names.
   Staged paths may include subdirectories; staging creates their parents,
   link rewriting resolves relative to the staged document, and cleanup
   removes only registered files, never authored directories.
3. Add the staged filename to the Project Documents toctree in
   [docs/index.md](docs/index.md).
4. Check links in both the authored source and the rendered site. Paths valid
   at the repository root may need adjustment during staging.
5. Run `make docs` in the development environment. Confirm the source remains
   intact and cleanup removes its staged copy after a successful build.

Only authoritative sources and intentional Sphinx inputs should be committed,
not generated copies or `docs/_build/`.

The project README is staged as `docs/project_readme.md`, using `STAGED_NAMES`
in the shared manifest. The separate authored documentation index lives in
`documentation/README.md`. Sphinx uses `docs/index.md`;
the historical `docs/index.rst` placeholder is excluded from the build.

Staging resolves links relative to each authored source, including nested
guides. Links to other staged documents
stay local, links to existing guides under `docs/` lose that prefix, and links
to repository code, tests, or data point to the upstream GitHub `main` branch.
Unresolved paths remain unchanged so Sphinx can report them. These repository
links describe the current branch on GitHub, not a versioned documentation snapshot.
Markdown heading anchors are enabled for local section links.

When an unmigrated legacy guide in `docs/` references a migrated source, use
its upstream repository URL until that guide is migrated too. This keeps the
link usable both on GitHub and in Sphinx without creating a second authored
copy. Links from migrated sources should be relative to those sources and
are rewritten for Sphinx during staging. The Aire reference now records cited public Leeds guidance and the current
launcher contract. Repository/CLI validation is not an on-cluster deployment
test; account-specific access, image/model compatibility, and scheduled smoke
validation remain required.

Autosummary does not overwrite existing stubs during ordinary builds. New
generated stubs are ignored by Git; explicit API directives in `docs/api.rst`
remain the maintained API reference. Some stubs are still tracked legacy
generated files; avoid incidental changes to them and migrate their ownership
deliberately. Requirement mirrors are temporary generated files.

Default pytest discovery is limited to `tests/` by `pytest.ini`. This prevents
Python test examples downloaded into Sphinx's HTML output from being collected
as a second test suite after a documentation build.

### Root documents

Keep planning and history separate:

- [ROADMAP.md](documentation/planning/ROADMAP.md) is forward-looking: priorities, intended outcomes,
  unfinished work, and dependencies. It is not a release log. When work lands,
  remove or update the relevant planned item and record the delivered change
  in the change log. Keep inherited tasks with uncertain completion explicitly
  marked for evidence reconciliation, rather than silently dropping them or
  treating them as confirmed open work.
- [CHANGE_LOG.md](CHANGE_LOG.md) records delivered changes by release, with an
  Unreleased section for changes awaiting release. Preserve unique historical
  details when moving material from the roadmap; do not duplicate entries.
- [DEVELOPMENT_HISTORY.md](documentation/history/DEVELOPMENT_HISTORY.md) records dated milestones,
  development context, and reflections, rather than duplicating the release
  log or acting as the current plan.
- Detailed implementation plans, such as
  [GABM_Refactor_Plan.md](documentation/planning/GABM_Refactor_Plan.md), hold scope, acceptance gates,
  and progress evidence. Link them from the roadmap instead of repeating them.

Markdown files in the root directory, each serving a specific purpose:
  - [README.md](README.md): A general [README](https://en.wikipedia.org/wiki/README) that links to much of the documentation outlined below including the developer and user guides. It is included in the Sphinx documentation and forms the basis for the main Sphinx documentation page.
  - [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md): Provides details on expected behavior of developers and reporting procedures.
  - [USER_GUIDE.md](USER_GUIDE.md): Provides step-by-step instructions for users to get set, and should provide guidance for using GABM.
  - [DEV_QUICKSTART.md](DEV_QUICKSTART.md) Provides step-by-step instructions for developers to get set up for contributing to GABM development.
  - [DEV_GUIDE.md](DEV_GUIDE.md): Explains how to contribute to GABM as a developer. It provides details about project structure, and workflow guidance.
  - [API_KEYS.md](API_KEYS.md): Explains how to create a file containing API keys for communicating with LLMs.
  - [ROADMAP.md](documentation/planning/ROADMAP.md): Forward-looking priorities, planned features, and unfinished development goals.
  - [GABM_Refactor_Plan.md](documentation/planning/GABM_Refactor_Plan.md): Maintained plan and acceptance gates for extracting reusable CAG capabilities into GABM.
  - [CHANGE_LOG.md](CHANGE_LOG.md): Delivered changes and updates organised by release.
  - [DEVELOPMENT_HISTORY.md](documentation/history/DEVELOPMENT_HISTORY.md): Dated development milestones, context, and reflections.

- Add API docs via `docs/index.md` or `docs/api.rst`.


### Sphinx Documentation

To build run:

```bash
make docs
```

- This runs [scripts/dev/docs.py](scripts/dev/docs.py) to stage registered sources from
  the repository root and `documentation/` into `docs/`, rewrite links and
  generate dependency pages, then build the site. After a successful build,
  cleanup removes registered staging files, not their authored sources or
  the rendered output in `docs/_build/`. A failed build can leave staged
  files behind; use `make docs-clean` after inspecting the failure.

**Note on Sphinx/MyST Documentation Warnings:**

When building the documentation with [Sphinx](https://www.sphinx-doc.org/) and [MyST](https://mystmd.org/), you may see warnings like:

  Document headings start at H2, not H1 [myst.header]
  document isn't included in any toctree [toc.not_included]
  duplicate object description ... use :no-index: for one of them
  WARNING: Field list ends without a blank line; unexpected unindent. [docutils]
  'myst' cross-reference target not found: ... [myst.xref_missing]

Warnings do not necessarily stop HTML generation, but a successful build is
not a warning-clean validation. In particular, `myst.xref_missing` means a
link or cross-reference could not be resolved and may be broken in the site.
Fix warnings introduced by a change and record remaining historical warnings
as explicit follow-up work; do not suppress them globally or assume that all
are harmless.

For a complete warning audit, rather than an incremental build, stage the
sources and force Sphinx to reread all documents:

```bash
make docs-make
sphinx-build -E -a -b html docs docs/_build/html > /tmp/cag-docs-build.log 2>&1
make docs-clean
```

Check the Sphinx command's exit status and log before cleanup; cleanup success
does not prove that the build succeeded. Normal `make docs` runs cleanup only
after a successful build, including with `make -j`.


Preview the Sphinx documentation by opening `docs/_build/html/index.html` in a [Web browser](https://en.wikipedia.org/wiki/Web_browser).

To deploy the Sphinx Documentation run:

```bash
make gh-pages-deploy
```

This should deploy/update the `gh-pages` branch on your origin Fork. If your Fork uses the `gh-pages` branch for [GitHub Pages](https://docs.github.com/en/pages), then the documentation should update there.

If it all looks good. Please submit a PR to incorporate documentation changes into main. A maintainer will subsequently update the upstream repository gh-pages branch.

#### Sphinx API Documentation and Autosummary


Climate-Action-GABM uses Sphinx with the autosummary extension to generate API documentation for all major modules. To document new modules:

- Import the new module in the appropriate `__init__.py` file so Sphinx can discover it (e.g., add `from .my_module import *`).
- Add the module to the API Reference toctree in `docs/index.md` (as an `_autosummary/` entry) to ensure it appears in the documentation navigation.
- You do not need to manually maintain individual `.rst` files for each module; autosummary will generate them automatically during `make docs`.
- If you remove or rename modules, update both the `__init__.py` imports and the API Reference list in `docs/index.md`.
- You may delete stale `.rst` files in `_autosummary` if they are no longer referenced.

Preview the Sphinx documentation by opening `docs/_build/html/index.html` in a web browser.


## Packaging and Deployment

The following files and directories are essential for building, testing, and distributing the Climate-Action-GABM package:
- **pyproject.toml**: Declares build system requirements and project metadata. Required for modern Python packaging (PEP 517/518).
- **setup.cfg**: Contains static package metadata and configuration for setuptools, such as:
	- Package name, version, author, and description
	- Python version requirements
	- Entry points (e.g., console_scripts)
	- Classifiers and other options
	This file is preferred over setup.py for static, declarative configuration.
- **MANIFEST.in**: Informs setuptools which additional files (beyond Python modules) to include in the source distribution (sdist). This should be updated so users who install from source get all necessary files.
- **requirements.txt**: Lists pinned dependencies for end users (used by pip install -r requirements.txt).
- **requirements-dev.txt**: Lists development dependencies (testing, linting, docs) with version ranges for contributors.
- **requirements-local.txt**: Optional dependencies for the `provider="local"` LLM backend (e.g. `mlx-lm` on Apple Silicon). Not required for cloud-only runs; see [docs/Local_LLM_Setup_Guide.md](documentation/guides/Local_LLM_Setup_Guide.md).
- **dist/**: Output directory for built distributions (.tar.gz and .whl files) after running the build process.
- **src/cag.egg-info/**: Metadata directory created by setuptools during build. Contains information about the package (version, dependencies, etc.). Safe to delete; will be recreated as needed.
- **venv-build-test/**: Temporary virtual environment created by `make build-test` for testing the built package in isolation. This can be safely deleted after testing.


## Branch Protection
[GitHub Actions](https://github.com/features/actions) workflows are used to help manage Pull Requests (PRs):
- `.github/workflows/test.yml` automatically runs `make test` on PRs to the main branch.
- `.github/workflows/gh-pages-deploy.yml` builds documentation for the gh-pages branch and is for automated docs deployment.

PRs to the [Climate-Action-GAB Repository main branch](https://github.com/compolis/Climate-Action-GABM/tree/main) must pass the test workflow before merging.

The gh-pages branch is protected from deletion.


## Maintainer Guide

This section is aimed at developers that are maintainers. Developers that are not maintainers are requested to refrain from publishing releases to PyPI so maintainers can ensure project integrity and security.


### PyPI Release Process
To release a new version of Climate-Action-GABM to [PyPI](https://pypi.org/), follow these steps:

1. **Update Version**: Run `make bump-version` to update the version everywhere (including setup.cfg, pyproject.toml, src/cag/__init__.py, requirements-dev.txt, and all occurrences in [User Guide](USER_GUIDE.md)). Use `make bump-version part=minor` or `part=major` for non-patch bumps. Commit and push the changes before continuing.
2. **Build the Package**:
	```sh
	make build
	```
	This creates .tar.gz and .whl files in the dist/ directory.
3. **Test the Build**:
	```sh
	make build-test
	```
	This installs the built package in a clean environment and runs the test suite.
4. **Upload to TestPyPI (optional but recommended):**
	```sh
	make testpypi-release
	```
	This uploads the package to TestPyPI. Test installation from TestPyPI in a clean environment:
	```sh
	pip install --index-url https://test.pypi.org/simple/ gabm
	```
	You will need to have an account on https://test.pypi.org and have created an API key for this to work.
5. **Upload to PyPI:**
	```sh
	make pypi-release
	```
	This uploads the package to the official PyPI repository.
	You will need to have an account on https://pypi.org and have created an API key for this to work.
6. **Verify Release:**
	- Check the PyPI page and test installation as a user ensuring the instructions in the [User Guide](USER_GUIDE.md) work.

For more details, see the [Python Packaging User Guide](https://packaging.python.org/).


### Branch and Documentation Deployment

Sphinx documentation is built and deployed using `make gh-pages-deploy`. If the upstream `gh-pages` branch is out of sync or needs to be replaced, use `git push --force upstream gh-pages` to overwrite it with the correct local version. This should be done with care, as it replaces the branch history. 

When deploying documentation with `make gh-pages-deploy`, you may encounter an error like:

```
fatal: 'gh-pages' is already used by worktree at '/tmp/gh-pages-xxxx...'
```

This occurs if a previous deployment left a lingering worktree directory for the `gh-pages` branch. The deployment script should automatically check for and removes any existing worktree before adding a new one. If you encounter this error, manually remove the worktree:

```
git worktree remove /tmp/gh-pages-xxxx...
```

For more details, see the comments in the Makefile and the deployment script.


## GitHub Copilot

Using [GitHub Copilot](https://github.com/features/copilot)) for [vibe coding](https://en.wikipedia.org/wiki/Vibe_coding), can help with understanding workflows and developing documentation, code and tests.

GitHub Copilot uses limited context and the chat context does not currently persist between sessions. As a result, it is good to develop/update documentation along with changes. GitHub Copilot can be asked to read the [README](README.md) and [Developer Guide](DEV_GUIDE.md) at the start of a session so as to be more context aware and provide better support.


## Managing Logs and Caches

Logs and caches (including prompt/response caches for LLM services) are generated during development and use. These files can become large. Typically they are not committed to the repository.

Project Python scripts use Python logging and write logs to:

	data/logs/docs/

Each Python script has its own log file to help:
- Debug issues with documentation builds or asset copying
- Review script actions and errors

Logging levels can be adjusted as needed.

If you encounter problems, please check relevant log files for details.


## Files and Directories Excluded from Version Control

Certain files and directories are intentionally excluded from the repository via `.gitignore` to keep the project clean and secure:

- `data/logs/` — All log files generated by scripts and modules (can be large and environment-specific)
- `data/io/llm/*/prompt_response_cache.pkl` — LLM response cache files
- `data/api_key.csv` — API keys (never commit secrets)