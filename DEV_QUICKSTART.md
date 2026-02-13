# Developer Quickstart


## Table of Contents
- [Overview](#overview)
- [Pre-requisites](#pre-requisits)
- [1. Fork and Clone](#1-fork-and-clone)
- [2. Install Dependencies](#2-install-dependencies)
- [3. Set Up LLM API Keys](#3-set-up-llm-api-keys)
- [4. Run Tests and Build Documentation](#4-run-tests-and-build-documentation)
- [Troubleshooting](#troubleshooting)
- [Additional Resources](#additional-resources)


## Overview
This guide helps developers get started with Climate-Action-GABM quickly. Please refer to the [Developer Guide](DEV_GUIDE.md) for details of how to contribute.

In the rest of the document "you" means you as a GABM developer.

Your choice of development environment is your own, but we recommend [Visual Studio Code](https://code.visualstudio.com/).


## Pre-requisits
You need:
- A [GitHub](https://github.com/) account to contribute.
- [git](https://git-scm.com/) version 2 at or above 2.43.
- [Python](https://www.python.org/) version 3 at or above version 3.12.
- [PIP](https://pypi.org/project/pip/) at or above version 25.2.
- [GNU Make](https://www.gnu.org/software/make/) version 4 at or above version 4.3.

To check your Python version run:

```bash
python3 --version
```

To check your PIP version run:

```bash
pip --version
```

To check you GNU Make version run:

```bash
make --version
```

You may have multiple versions of Python and GNU Make on your system. Please use the right [Path](https://en.wikipedia.org/wiki/Path_(computing)) to the versions needed for GABM when developing GABM. You might want to do this by modifying your [PATH](https://en.wikipedia.org/wiki/PATH_(variable)).


With the pre-requisites in place, the following steps should have you set up in a matter of minutes.


## 1. Fork and Clone
- Fork from the [Climate-Action-GABM Repository](https://github.com/compolis/Climate-Action-GABM) to your own GitHub account using the "Fork" button to "Create a new fork".
- Clone your fork locally using the following command and by replacing "<your-GitHub-username>" with your actual GitHub username:

```bash
git clone https://github.com/<your-GitHub-username>/Climate-Action-GABM.git
```

To keep your fork up to date with the main repository, add the upstream remote:

```bash
git remote add upstream https://github.com/compolis/Climate-Action-GABM.git
```

## 2. Install Dependencies
Change into the GABM directory. From the project root, install all runtime, development, and documentation dependencies:

```bash
pip install -r requirements-dev.txt
```


## 3. Run Tests and Build Documentation

- Run tests:

```bash
make test
```

- Build documentation:

```bash
make docs
```

- View docs in your browser: open `docs/_build/html/index.html`



## Troubleshooting

If you encounter errors, double-check your setup steps above. If you want help, [open an issue on GitHub](https://github.com/compolis/Climate-Action-GABM/issues/new/choose).

### GitHub SSO and Remote Access Issues

If you see errors like:

```
remote: The 'compolis' organization has enabled or enforced SAML SSO.
fatal: unable to access 'https://github.com/compolis/Climate-Action-GABM.git/': The requested URL returned error: 403
```

Try the following steps:

1. Log out and log back into GitHub in your browser.
2. Visit your organization’s SSO page (e.g., https://github.com/orgs/compolis/sso) and grant SSO access if prompted.
3. In VS Code, open the Command Palette and run “GitHub: Sign out” then “GitHub: Sign in” to refresh your credentials.
4. Try your git command again (e.g., `make sync`).
5. If you have admin access, you can update the upstream remote URL to use SSH instead of HTTPS:

	```bash
	git remote set-url upstream git@github.com:compolis/Climate-Action-GABM.git
	```

If the issue persists, contact your organization admin to ensure your account is SSO-authorized for the repository.
  
#### How to ensure your account is SSO-authorized for the repository

1. Go to your organization’s SSO page (e.g., https://github.com/orgs/compolis/sso).
2. If you see a prompt to authorize your GitHub account for SSO, click the “Authorize” or “Grant” button next to the repository or organization.
3. If you do not see the option, contact your organization administrator and request SSO access for your GitHub account on the repository.
4. After authorization, try your git command again.


## Additional Resources
- [README](README.md)
- [Developer Guide](DEV_GUIDE.md)
- [Reported Issues](https://github.com/compolis/Climate-Action-GABM/issues)