import json
import os
import sys
import time
from typing import Dict, List

os.system("title " + "DayZ Syncer")


def load_config(config_path: str = "./config.json") -> Dict[str, object]:
    if (not os.path.isfile(config_path)):
        sys.exit("'config.json' not found!")
    with open(config_path, "r") as file:
        return json.load(file)


def ensure_file_exists(path: str, label: str) -> None:
    directory = os.path.dirname(path)
    if (directory and not os.path.isdir(directory)):
        sys.exit(f"{label} directory does not exist: {directory}")
    if (not os.path.isfile(path)):
        print(f"{label} file missing, creating: {path}")
        with open(path, "w") as file:
            file.write("")


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
    with open(path, "w") as file:
        file.write("\n".join(entries))


def sync_list(sync_path: str, server_paths: List[str], label: str) -> None:
    sync_entries = read_entries(sync_path)

    for server_path in server_paths:
        server_entries = read_entries(server_path)
        if (server_entries != sync_entries):
            write_entries(server_path, sync_entries)
            print(f"Synced {label} list: {server_path}")


def main() -> None:
    config = load_config()
    syncer_config = config.get("syncer", None)
    if (not isinstance(syncer_config, dict)):
        sys.exit("Syncer config missing. Please add a 'syncer' section to config.json.")

    whitelist_sync_path = syncer_config.get("whitelist_sync_path", "")
    blacklist_sync_path = syncer_config.get("blacklist_sync_path", "")
    whitelist_server_paths = syncer_config.get("whitelist_server_paths", [])
    blacklist_server_paths = syncer_config.get("blacklist_server_paths", [])
    sync_interval_seconds = int(syncer_config.get("sync_interval_seconds", 10))

    if (not whitelist_sync_path or not blacklist_sync_path):
        sys.exit("Syncer config requires whitelist_sync_path and blacklist_sync_path.")
    if (not isinstance(whitelist_server_paths, list) or not whitelist_server_paths):
        sys.exit("Syncer config requires whitelist_server_paths as a non-empty list.")
    if (not isinstance(blacklist_server_paths, list) or not blacklist_server_paths):
        sys.exit("Syncer config requires blacklist_server_paths as a non-empty list.")

    ensure_file_exists(whitelist_sync_path, "Whitelist sync")
    ensure_file_exists(blacklist_sync_path, "Blacklist sync")

    for path in whitelist_server_paths:
        ensure_file_exists(path, "Whitelist server")
    for path in blacklist_server_paths:
        ensure_file_exists(path, "Blacklist server")

    print("Syncer running. Watching for whitelist/blacklist updates.")
    while True:
        try:
            sync_list(whitelist_sync_path, whitelist_server_paths, "whitelist")
            sync_list(blacklist_sync_path, blacklist_server_paths, "blacklist")
        except Exception as exc:
            print(f"Syncer error: {exc}")
        time.sleep(sync_interval_seconds)


if __name__ == "__main__":
    main()
