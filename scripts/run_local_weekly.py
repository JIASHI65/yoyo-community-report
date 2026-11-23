#!/usr/bin/env python3
"""Build the private-review weekly report using the local CC Switch proxy."""
import base64
import getpass
import json
import os
import pathlib
import re
import subprocess
import tempfile
import time

from generate_weekly import CHANNELS


REPO = "JIASHI65/yoyo-community-report"
ROOT = pathlib.Path(__file__).resolve().parents[1]
PROXY_URL = "http://127.0.0.1:15721/v1"


def command(*args, cwd=None, env=None, input_bytes=None):
    for attempt in range(4):
        result = subprocess.run(
            args, cwd=cwd, env=env, input=input_bytes, capture_output=True, check=False
        )
        if result.returncode == 0:
            return result.stdout
        error = result.stderr.decode(errors="replace")
        transient = args[0] == "gh" and any(
            marker in error.lower() for marker in
            ("timeout", "stream error", "connection reset", "tls handshake", "eof")
        )
        if not transient or attempt == 3:
            raise RuntimeError(f"{' '.join(args[:3])} failed: {error[-2000:]}")
        time.sleep(5 * (attempt + 1))


def keychain_secret(service):
    return command(
        "security", "find-generic-password", "-a", getpass.getuser(),
        "-s", service, "-w"
    ).decode().strip()


def wait_for_run(run_id):
    deadline = time.monotonic() + 900
    while time.monotonic() < deadline:
        state = json.loads(command(
            "gh", "run", "view", run_id, "--repo", REPO,
            "--json", "status,conclusion"
        ))
        if state["status"] == "completed":
            if state["conclusion"] != "success":
                raise RuntimeError(f"Discord scan {run_id} failed: {state['conclusion']}")
            return
        time.sleep(8)
    raise TimeoutError(f"Discord scan {run_id} did not complete within 15 minutes")


def encrypted_scan(run_id):
    for attempt in range(4):
        try:
            lines = command("gh", "run", "view", run_id, "--repo", REPO, "--log").decode().splitlines()
            break
        except RuntimeError:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    encoded = []
    capturing = False
    for line in lines:
        value = line.rsplit(" ", 1)[-1]
        if value == "ENCRYPTED_SCAN_BEGIN":
            capturing = True
        elif value == "ENCRYPTED_SCAN_END":
            capturing = False
        elif capturing and re.fullmatch(r"[A-Za-z0-9+/=]+", value):
            encoded.append(value)
    if not encoded:
        raise RuntimeError(f"Discord scan {run_id} produced no encrypted data")
    return base64.b64decode("".join(encoded), validate=True)


def collect_snapshots(snapshot_dir, encryption_key):
    run_ids = {}
    for name, channel_id in CHANNELS.items():
        output = command(
            "gh", "workflow", "run", "scan-community.yml", "--repo", REPO,
            "-f", "lookback_hours=338", "-f", f"channel_id={channel_id}"
        ).decode()
        match = re.search(r"/runs/(\d+)", output)
        if not match:
            raise RuntimeError(f"No run ID returned for {name}")
        run_ids[channel_id] = match.group(1)
    for name, channel_id in CHANNELS.items():
        run_id = run_ids[channel_id]
        wait_for_run(run_id)
        env = os.environ.copy()
        env["SCAN_ENCRYPTION_KEY"] = encryption_key
        plaintext = command(
            "openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2",
            "-pass", "env:SCAN_ENCRYPTION_KEY",
            env=env, input_bytes=encrypted_scan(run_id)
        )
        messages = json.loads(plaintext)
        if not isinstance(messages, list) or any("author_id" not in item for item in messages):
            raise RuntimeError(f"Discord scan {run_id} returned an incompatible snapshot")
        destination = snapshot_dir / f"{channel_id}.json"
        destination.write_bytes(plaintext)
        destination.chmod(0o600)
        print(f"#{name}: {len(messages)} non-bot messages in 14 days")


def main():
    os.umask(0o077)
    encryption_key = keychain_secret("yoyo-scan-encryption-key")
    proxy_key = keychain_secret("yoyo-ccswitch-api-key")
    with tempfile.TemporaryDirectory(prefix="yoyo-weekly-") as temporary:
        directory = pathlib.Path(temporary)
        snapshot_dir = directory / "snapshots"
        snapshot_dir.mkdir(mode=0o700)
        collect_snapshots(snapshot_dir, encryption_key)

        checkout = directory / "report"
        command("git", "clone", "--depth", "1", "--branch", "main",
                f"https://github.com/{REPO}.git", str(checkout))
        env = os.environ.copy()
        env.update({
            "OPENAI_API_KEY": proxy_key,
            "OPENAI_BASE_URL": PROXY_URL,
            "OPENAI_MODEL": "gpt-6-astra",
            "DISCORD_SNAPSHOT_DIR": str(snapshot_dir),
        })
        command("python3", "scripts/generate_weekly.py", cwd=checkout, env=env)

        command("git", "config", "user.name", "yoyo-weekly-local", cwd=checkout)
        command("git", "config", "user.email", "yoyo-weekly-local@users.noreply.github.com", cwd=checkout)
        command("git", "add", "weekly.html", "index.html", "weekly-draft.md",
                "weekly-feishu-payload.json", "weekly_cache.json", cwd=checkout)
        staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=checkout)
        if staged.returncode == 1:
            command("git", "commit", "-m", "weekly report local generation", cwd=checkout)
            command("git", "push", "origin", "main", cwd=checkout)
        elif staged.returncode:
            raise RuntimeError("Unable to inspect generated report changes")
        print("Weekly BI and draft updated; Feishu was not contacted")


if __name__ == "__main__":
    main()
