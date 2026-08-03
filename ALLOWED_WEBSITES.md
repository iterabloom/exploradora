<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# ALLOWED_WEBSITES.md
# Security boundary: outbound network access is restricted to these domains only. If a link redirects to a non-allowlisted domain, do not follow it.
# Changes to this file require human approval.

## Rules
- Prefer HTTPS.
- Read-only research: GET/HEAD only (no posting credentials, no uploading repo content).
- No authentication tokens may be pasted into URLs or headers, except by the approved forge scripts (`auto-pr`, `merge-pr`, `ci-debug`, `contribute`, `list-my-prs`) reading from `.env`.
- Package-index uploads (PyPI, TestPyPI) are a human-only action. The agent never holds or uses an index token.
- If a needed domain is missing, stop and request human approval to add it (domain + rationale).

## Search / discovery
- duckduckgo.com

## Source code hosting / forge
- github.com
- api.github.com
- raw.githubusercontent.com

## CI
# This project's Woodpecker instance, named by WOODPECKER_SERVER in .env
# rather than written here, so the host is not published in a public repo.
# Needed because CI logs sit behind Cloudflare Access and are not
# retrievable through the GitHub API.
- $WOODPECKER_SERVER  (see .env)

## Python packaging
- pypi.org
- files.pythonhosted.org
- test.pypi.org
# Rationale for test.pypi.org: the release workflow requires a full
# upload → install-from-index rehearsal on TestPyPI before any real
# upload. The upload legs are human-only (see Rules); the agent's use
# is limited to install-from-index verification (pip) and read-only
# project-page checks.

## Official docs / standards
- docs.python.org
- packaging.python.org
- rfc-editor.org
- textual.textualize.io
