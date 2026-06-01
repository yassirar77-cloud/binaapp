# Security Policy

## Reporting a vulnerability

If you discover a security issue or an exposed credential in this repository,
please email **info@binaapp.my** rather than opening a public issue.

## Handling secrets

- **Never** commit real credentials. Only commit placeholder templates such as
  `.env.example` / `ENV_TEMPLATE.txt`, where every value is a clearly fake
  placeholder (e.g. `your_deepseek_api_key_here`).
- Real configuration lives in `.env`, which is git-ignored, or in the hosting
  provider's secret manager (Render / Railway environment variables).
- A `gitleaks` pre-commit hook (see `.pre-commit-config.yaml`) blocks secrets
  from being committed. Enable it with `pip install pre-commit && pre-commit install`.

## Resolved incident — exposed AI API keys (2025-12)

A `.env.example` commit briefly contained **real** API keys instead of
placeholders. The affected keys were:

- `DEEPSEEK_API_KEY`
- `QWEN_API_KEY`

### Status

- The keys have been replaced with placeholders in the current tree.
- The old values still exist in **git history** and must be treated as
  permanently compromised.

### Required remediation (must be done by the repository owner)

1. **Rotate both keys immediately** — the exposed values are still live until
   revoked:
   - DeepSeek: https://platform.deepseek.com/api_keys — delete the old key and
     create a new one.
   - Qwen / DashScope: https://dashscope.console.aliyun.com — revoke and reissue.
2. Store the new keys only as environment variables / hosting secrets, never in
   any committed file.
3. (Optional but recommended) Purge the secrets from git history with
   [`git filter-repo`](https://github.com/newren/git-filter-repo) or the
   [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/), then
   force-push. Note this rewrites history for all collaborators.

Rotation is the only action that fully neutralises the exposure — once a key has
been pushed to a public repo it should be considered burned, even after the file
is cleaned up.
