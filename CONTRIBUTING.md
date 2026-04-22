# Contributing to Datura

Thanks for your interest in contributing. This document covers how to get started, what to work on, and what to expect during review.

## Getting Started

1. Fork the repository and clone your fork.
2. Build and run the container to make sure everything works:
   ```bash
   docker build -f docker/Dockerfile -t datura .
   docker run -d --name datura -p 8080:8080 \
     -v ollama_data:/data/ollama -v /tmp/datura/logs:/data/logs datura
   ```
3. Run the tests:
   ```bash
   pip install pytest
   pytest -v tests/
   ```

## What to Work On

Check the [issues](https://github.com/lopes/datura/issues) for open tasks. If you want to work on something not listed, open an issue first to discuss the approach before writing code.

Good first contributions:
- New sensitive data block categories (see `src/proxy.py.tmpl`, `pick_data_block()`)
- Additional few-shot examples in `etc/Modelfile.tmpl` for better model gating
- New classification patterns in `etc/datura.env` (`PROBE_PATTERNS`, `RECON_PATTERNS`)
- Addressing [known supply chain considerations](SECURITY.md#known-supply-chain-considerations)
- Documentation improvements
- Test coverage for untested code paths

## Project Constraints

These are non-negotiable and PRs that violate them will be rejected:

- **No external Python dependencies.** The proxy uses stdlib only. No pip, no requirements.txt.
- **Docker-first.** The project runs as a container. No local launch scripts.
- **Single-file config.** All configuration lives in `etc/datura.env`. No new config files.
- **Templates only.** Source files in `src/` and `etc/` are templates rendered by `envsubst` at startup. Use `${VAR}` placeholders for configurable values. Avoid JavaScript template literals (`${expr}`) in `ui.html.tmpl` because `envsubst` will eat them; use string concatenation instead.

## Submitting a Pull Request

1. Create a feature branch from `main`.
2. Make your changes. Keep commits focused and atomic.
3. Run the tests and make sure they pass:
   ```bash
   pytest -v tests/
   ```
4. If you changed the proxy (`src/proxy.py.tmpl`), also run the linter:
   ```bash
   pip install ruff
   python3 tests/conftest.py
   ruff check src/proxy_rendered.py --select E,F,W --ignore E501,F541,F401,F821
   ```
5. If you added new `${VAR}` placeholders, add them to:
   - `etc/datura.env` (with a default value and comment)
   - `tests/conftest.py` (`TEST_VARS` dict)
6. Open a PR against `main` with a clear description of what and why.

## Code Style

- Python: type annotations on all functions (see existing code for examples). Use `from __future__ import annotations`. Follow PEP 8.
- Documentation: concise, no em-dash overuse, use colons or periods instead. No emojis.
- Tests: one test class per function, descriptive method names, use the `proxy` fixture from `conftest.py`.

## Review Process

All PRs are reviewed before merging. Expect feedback on:

- **Does it fit the threat model?** Changes should make the honeypot more convincing, more detectable, or more robust. Not more complex for complexity's sake.
- **Does it break the dark room?** Sensitive data should only leak when an attacker demonstrates knowledge and intent. See [Tuning & Testing](docs/tuning.md) for the philosophy.
- **Is it tested?** New pure functions need unit tests. Behavioral changes need manual testing against the three personas (casual visitor, curious outsider, threat actor).

## Reporting Security Issues

Do not open public issues for security vulnerabilities. Report them privately through [GitHub's security advisory feature](https://github.com/lopes/datura/security/advisories/new). See [SECURITY.md](SECURITY.md) for scope and details.
