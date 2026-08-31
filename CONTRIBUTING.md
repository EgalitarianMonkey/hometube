# Contributing to HomeTube

Thank you for your interest in contributing to **HomeTube**! 🙌  
Pull Requests (PRs) are welcome, but please note:

👉 **No direct collaborators are added to the repository.**  
All contributions must go through the PR review process from your fork, and final merge decisions are made by the maintainer.

---

## 🧭 Philosophy

HomeTube’s goal is to stay **simple, robust, and privacy-respectful** — a unified downloader built on `yt-dlp`, with a clean UI, strong resilience, and minimal dependencies.

Please keep contributions aligned with this philosophy.

**Priorities:**
- Stability > Features
- Simplicity > Complexity
- Clarity > Cleverness
- Security > Convenience

---

## 💡 General Contribution Rules

1. **Open an Issue first**  
   - Describe the motivation and intended scope before opening a PR.  
   - Large or experimental ideas should be discussed before implementation.

2. **Scope matters**  
   - Prefer small, self-contained PRs (1 feature/fix per PR).  
   - Avoid large refactors unless discussed first.

3. **Optional by default**  
   - Any external integration (e.g., Jellyfin, Plex, etc.) must be **disabled by default** and configurable via environment variables.

4. **Security & reliability**  
   - No hard-coded secrets, tokens, or credentials.  
   - Use timeouts, retries, and non-blocking error handling for all network calls.

5. **Keep dependencies minimal**  
   - Every new dependency must be justified and lightweight.  
   - Prefer Python stdlib whenever possible.

---

## ⚙️ Development Guidelines

- **Python**: version 3.11+  
- **Linting**: `ruff` + `black`  
- **Tests**: `pytest -m "not slow and not external and not network"` must pass.  
- **Typing**: gradual adoption of type hints is encouraged.  
- **Configuration**: use environment variables defined in `config.py` (no global hard-coded constants).  
- **Logging**: human-readable, actionable messages.  

---

## 🧩 Integrations (e.g., Jellyfin, Plex, etc.)

If you propose an external service integration:

- Place it under `integrations/<service>.py`.
- Must be **disabled by default** (`SERVICE_ENABLED=false`).
- Use env vars:
  ```
  JELLYFIN_ENABLED=false
  JELLYFIN_URL=https://your-server
  JELLYFIN_API_KEY=...
  JELLYFIN_TIMEOUT=5
  JELLYFIN_RETRIES=2
  ```
- Add `timeout`, `retry`, and logging (non-blocking on errors).
- Include minimal tests and documentation section in `README.md`.

---

## 🧪 Testing

- Add at least one unit or integration test for new logic.  
- Use reduced sample JSON fixtures under `tests/fixtures/`.  
- Do not commit large files (>1 MB).  
- CI must stay fast and reproducible.

---

## 🧾 Commit & PR Guidelines

- **Fork the repository first** — all PRs must come from your fork, not from a branch in this repo.
- **Commit messages**: use imperative mood — e.g. `Add`, `Fix`, `Refactor`.  
- **PR titles**: concise and descriptive (`Add Jellyfin trigger integration`).  
- **Description**: explain the motivation, scope, and limitations.  
- The maintainer may **squash-merge** your PR into a single clean commit.

Example PR checklist:
```
- [ ] Minimal, focused scope
- [ ] Optional by default (if integration)
- [ ] Non-blocking on errors
- [ ] Tests added / updated
- [ ] Lint & formatting pass
- [ ] README or docs updated
```

---

## 📜 Licensing of contributions

HomeTube is licensed under the **AGPL-3.0-or-later** — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

By submitting a contribution — a pull request, a patch, or any code, documentation or other material — you agree to all of the following.

- **You keep your copyright.** Nothing here assigns it or takes it away from you.
- **You license your contribution under the project licence**, AGPL-3.0-or-later, so that it can be distributed as part of HomeTube.
- **You grant the project's author a perpetual, worldwide, irrevocable, royalty-free right to relicense your contribution**, including under commercial or proprietary terms, as part of HomeTube or a work derived from it.
- **You confirm you are entitled to grant this** — the work is yours, or you have permission from whoever owns it, an employer for instance.

### Why the relicensing grant is asked

HomeTube is one person's project, released under a copyleft licence. Without this grant, any future change to how HomeTube is offered — a commercial edition, a different licence, inclusion in a differently-licensed work — would require locating every past contributor and obtaining their individual agreement. Asking once, up front, keeps that option open rather than quietly closing it with each merge.

The grant does not make your contribution any less free: it stays under the AGPL for everyone, exactly as before.

### If you would rather not grant it

Say so in your pull request. Your contribution can still be accepted under the AGPL alone. It simply means it could not be included in any future relicensing, and might have to be reimplemented if that ever happens — so it is better said openly at the time than discovered later.

---

## 🔐 Security

- Never submit API keys, cookies, or tokens.  
- No credentials in code or commits.  
- Report security concerns privately by emailing the maintainer or creating a private security advisory on GitHub.

---

## 🧑‍💻 Governance

- **Maintainer:** single owner responsible for merges, releases, and roadmap decisions.  
- **Contributions:** via PRs only, from forks (no direct push access).  
- **Collaborators:** not accepted — all contributors work from their own forks.  
- **Merges:** squash-merge for a clean history.  
- **Versioning:** [Semantic Versioning (SemVer)](https://semver.org/).  
  - Breaking changes bump the major version.

---

## ❤️ Thank You

Your time and ideas are appreciated!  
Even small PRs (typo fixes, minor refactors, docs improvements) make a difference.  
Thank you for helping HomeTube stay open, solid, and beautiful. 🚀
