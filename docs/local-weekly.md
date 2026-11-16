# Yoyo Creative Studio weekly report

The Monday report is generated on the operator's Mac because CC Switch listens only on `127.0.0.1:15721`. GitHub Actions cannot call that loopback address.

At 16:00 Asia/Shanghai, `com.yoyo.weekly-report` runs `scripts/run_local_weekly.py`. The runner asks GitHub Actions to scan each of the eight KOC channels for 14 days. Actions encrypts the snapshots before printing or uploading them. The Mac decrypts them in a temporary directory, computes both weeks' metrics, calls CC Switch for LLM analysis, and updates `weekly.html`, `index.html`, `weekly-draft.md`, `weekly-feishu-payload.json`, and `weekly_cache.json` on `main`.

The runner never calls a Feishu webhook. `publish-weekly-report.yml` remains a separate manual action after the draft has been reviewed and the user explicitly confirms sending.

Prerequisites on the Mac:

- CC Switch is running and accepts the configured `gpt-6-astra` model.
- `gh` is authenticated for `JIASHI65/yoyo-community-report`.
- Login Keychain contains `yoyo-ccswitch-api-key` and `yoyo-scan-encryption-key` for the current macOS account. The latter must match GitHub's `SCAN_ENCRYPTION_KEY` secret.
- The Mac is awake and the user's login session is active at 16:00 on Monday.

Check the task with `launchctl print gui/$(id -u)/com.yoyo.weekly-report`. Read failures in `~/Library/Logs/yoyo-weekly-report.log`. A failed scan or LLM call stops before updating the report and before any Feishu delivery.
