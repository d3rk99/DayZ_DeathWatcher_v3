import json
import os
import sys
import time
import traceback
from typing import Dict, List
from pathlib import Path

from config_loader import ConfigError, load_config, sync_startup_message

os.system("title " + "DayZ Syncer")
STATUS_PATH = Path(".runtime") / "syncer_status.json"


def normalize_entries(raw_lines: List[str]) -> List[str]:
    cleaned: List[str] = []
    seen = set()
    for line in raw_lines:
        entry = line.strip()
        if (not entry or entry in seen):
            continue
        cleaned.append(entry)
        seen.add(entry)
    return cleaned


def read_entries(path: str) -> List[str]:
    with open(path, "r") as file:
        raw_lines = file.read().split("\n")
    return normalize_entries(raw_lines)


def write_entries(path: str, entries: List[str]) -> None:
    target = Path(path)
    temp_path = target.with_name(f"{target.name}.tmp")
    with open(temp_path, "w") as file:
        file.write("\n".join(entries))
    os.replace(temp_path, target)


def sync_list(sync_path: str, server_paths: List[str], label: str) -> None:
    sync_entries = read_entries(sync_path)

    for server_path in server_paths:
        server_entries = read_entries(server_path)
        if (server_entries != sync_entries):
            write_entries(server_path, sync_entries)
            print(f"Synced {label} list: {server_path}")


def write_status(status: str, message: str) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "message": message,
        "updated_at": time.time(),
    }
    temp_path = STATUS_PATH.with_name(f"{STATUS_PATH.name}.tmp")
    with open(temp_path, "w") as file:
        json.dump(payload, file, indent=2)
    os.replace(temp_path, STATUS_PATH)


def main() -> None:
    try:
        config, config_warnings = load_config(require_discord=False)
    except ConfigError as exc:
        write_status("misconfigured", str(exc))
        sys.exit(f"Configuration error: {exc}")
    for warning in config_warnings:
        print(f"Configuration warning: {warning}")
    print(sync_startup_message(config))

    if (not config.get("sync_enabled", False)):
        write_status("disabled", "Sync disabled: running in single-server mode.")
        return

    syncer_config = config["syncer"]
    whitelist_sync_path = config["whitelist_path"]
    blacklist_sync_path = config["blacklist_path"]
    whitelist_server_paths = syncer_config.get("whitelist_server_paths", [])
    blacklist_server_paths = syncer_config.get("blacklist_server_paths", [])
    sync_interval_seconds = int(syncer_config.get("sync_interval_seconds", 10))

    print("Syncer running. Watching for whitelist/blacklist updates.")
    while True:
        try:
            sync_list(whitelist_sync_path, whitelist_server_paths, "whitelist")
            sync_list(blacklist_sync_path, blacklist_server_paths, "blacklist")
            write_status("running", "Syncer copied master lists to configured server targets.")
        except Exception as exc:
            print(f"Syncer error: {exc}")
            write_status("error", str(exc))
        time.sleep(sync_interval_seconds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Closing program...")
    except SystemExit as exc:
        print(f"Syncer exited: {exc}")
    except Exception as e:
        print(f"Syncer crashed with error: {e}")
        traceback.print_exc()
        input("Press enter to close this window.")
