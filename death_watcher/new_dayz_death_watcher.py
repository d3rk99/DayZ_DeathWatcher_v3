import time
import sys
import os
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from dayz_dev_tools import guid as GUID

os.system("title " + "DayZ Death Watcher")

config: Dict[str, Any] = {}
log_paths: List[str] = []
path_to_bans = ""
cache_paths: List[str] = []
search_logs_interval = 1
verbose_logs = 1
cache_entries: Dict[str, Dict[str, Any]] = {}
cache_path_by_log: Dict[str, str] = {}

CONFIG_DEFAULT = """{
  "log_paths" : ["../profiles/DayZServer_x64.ADM"],
  "path_to_bans" : "./deaths.txt",
  "cache_paths" : ["./death_watcher_cache.json"],
  "ban_delay" : 5,
  "search_logs_interval" : 1,
  "verbose_logs" : 1
}"""


@dataclass
class DeathEvent:
    steam_id: str
    ts: Optional[str]
    raw: Dict[str, Any]
    source_path: str


def load_config(config_path: str = "./config.json") -> Dict[str, Any]:
    try:
        with open(config_path, "r") as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        print("Generating default config file: (config.json)")
        with open(config_path, "w") as json_file:
            json_file.write(CONFIG_DEFAULT)
    with open(config_path, "r") as json_file:
        return json.load(json_file)


def ensure_cache_file(cache_path: str) -> None:
    if (not os.path.isfile(cache_path)):
        print(f"Failed to find cache file: {cache_path}\nCreating it now.")
        with open(cache_path, "w") as file:
            json.dump(default_cache_entry(), file, indent=4)


def default_cache_entry() -> Dict[str, Any]:
    return {"log_file": "", "offset": 0, "partial": ""}


def normalize_log_paths(raw_config: Dict[str, Any]) -> List[str]:
    log_paths_value = raw_config.get("log_paths", None)
    if (log_paths_value is None):
        log_paths_value = raw_config.get("log_path", None)
    if (log_paths_value is None):
        log_paths_value = raw_config.get("path_to_logs", "")
    if (not isinstance(log_paths_value, list)):
        log_paths_value = [log_paths_value]

    cleaned_paths = []
    seen_paths = set()
    for log_path in log_paths_value:
        if (not log_path):
            continue
        if (isinstance(log_path, str)):
            log_path = log_path.strip()
        if (not log_path or log_path in seen_paths):
            continue
        seen_paths.add(log_path)
        cleaned_paths.append(log_path)

    if (len(cleaned_paths) > 5):
        print("Warning: More than 5 log paths provided. Only the first 5 will be used.")
        cleaned_paths = cleaned_paths[:5]

    return cleaned_paths


def normalize_cache_paths(raw_config: Dict[str, Any], log_paths: List[str]) -> List[str]:
    cache_paths_value = raw_config.get("cache_paths", None)
    if (cache_paths_value is None):
        cache_paths_value = raw_config.get("path_to_caches", None)
    if (cache_paths_value is None):
        cache_paths_value = raw_config.get("path_to_cache", None)
    if (not isinstance(cache_paths_value, list)):
        cache_paths_value = [cache_paths_value]

    cleaned_paths = []
    for cache_path in cache_paths_value:
        if (not cache_path):
            continue
        if (isinstance(cache_path, str)):
            cache_path = cache_path.strip()
        if (not cache_path):
            continue
        cleaned_paths.append(cache_path)

    if (len(cleaned_paths) == 0):
        cleaned_paths = ["./death_watcher_cache.json"]

    if (len(cleaned_paths) > len(log_paths)):
        print("Warning: More cache paths than log paths provided. Extra cache paths will be ignored.")
        cleaned_paths = cleaned_paths[:len(log_paths)]

    if (len(cleaned_paths) < len(log_paths)):
        base_path = cleaned_paths[0]
        base_root, base_ext = os.path.splitext(base_path)
        if (not base_ext):
            base_root = base_path
            base_ext = ".json"
        while (len(cleaned_paths) < len(log_paths)):
            index = len(cleaned_paths) + 1
            cleaned_paths.append(f"{base_root}_{index}{base_ext}")

    return cleaned_paths


players_to_ban = []


def try_to_ban_players():    
    current_seconds = time.time()
    
    for player in players_to_ban:
        if (current_seconds >= player[1]):
            ban_player(player[0])
            players_to_ban.remove(player)
        else:
            break


def ban_player(player_id):
    try:
        guid = GUID.guid_for_steamid64(str(player_id))
    except Exception as e:
        print(f"Failed to convert steam id to guid ({player_id}): {e}")
        return
    with open(path_to_bans, "r") as file:
        ban_list = file.read().split('\n')
        
    if (not guid in ban_list):
        with open(path_to_bans, "a") as file:
            file.write(f"{guid}\n")
        if (verbose_logs):
            print(f"Added player guid: {guid} (steam id: {player_id}) to ban file: {path_to_bans}")


def resolve_log_file(log_path):
    if (os.path.isdir(log_path)):
        try:
            candidates = []
            for name in os.listdir(log_path):
                if (name.startswith("dl_") and name.endswith(".ljson")):
                    candidates.append(os.path.join(log_path, name))
            if (len(candidates) == 0):
                return ""
            return max(candidates, key=os.path.getmtime)
        except Exception:
            return ""
    return log_path


def read_new_lines(log_path, cache_entry):
    log_file_path = resolve_log_file(log_path)
    if (not log_file_path or not os.path.isfile(log_file_path)):
        time.sleep(1)
        return [], log_file_path

    if (cache_entry["log_file"] != log_file_path):
        if (cache_entry["log_file"]):
            print(f"Detected log rotation for {log_path}. Switching to {log_file_path}")
        else:
            print(f"Now tailing {log_file_path}")
        cache_entry["offset"] = 0
        cache_entry["partial"] = ""
        cache_entry["log_file"] = log_file_path
        update_cache(log_path)

    try:
        file_size = os.path.getsize(log_file_path)
        if (cache_entry["offset"] > file_size):
            cache_entry["offset"] = 0
            cache_entry["partial"] = ""
        with open(log_file_path, "r") as file:
            file.seek(cache_entry["offset"])
            data = file.read()
            cache_entry["offset"] = file.tell()
    except Exception:
        time.sleep(10)
        return [], log_file_path

    if (not data):
        return [], log_file_path

    data = f"{cache_entry['partial']}{data}"
    lines = data.split("\n")
    if (data and not data.endswith("\n")):
        cache_entry["partial"] = lines.pop()
    else:
        cache_entry["partial"] = ""

    update_cache(log_path)
    return [line for line in lines if line], log_file_path


def parse_death_event(line: str, source_path: str) -> Optional[DeathEvent]:
    if (not line.lstrip().startswith("{")):
        return None
    try:
        log_data = json.loads(line)
    except Exception:
        return None
    if (log_data.get("event") != "PLAYER_DEATH"):
        return None
    player_data = log_data.get("player", {})
    player_id = player_data.get("steamId")
    if (not player_id):
        return None
    player_position = player_data.get("position", {})
    x = player_position.get("x", None)
    y = player_position.get("y", None)
    z = player_position.get("z", None)
    if (x is None or y is None or z is None):
        return None
    if (x == 0 and y == 0 and z == 0 and log_data.get("sub_event") == "suicide"):
        return None
    return DeathEvent(steam_id=player_id, ts=log_data.get("ts"), raw=log_data, source_path=source_path)


def update_cache(log_path: str):
    cache_path = cache_path_by_log.get(log_path)
    if (not cache_path):
        return
    with open(cache_path, "w") as json_file:
        json.dump(cache_entries.get(log_path, default_cache_entry()), json_file, indent=4)
    if (verbose_logs):
        print(f"Updated cache file ({cache_path}):\n    {cache_entries.get(log_path)}")
    
    
def load_cache_entry(cache_path: str, log_path: str) -> Dict[str, Any]:
    with open(cache_path, "r") as json_file:
        cache_data = json.load(json_file)

    if (isinstance(cache_data, dict) and "logs" in cache_data):
        cache_data = cache_data["logs"].get(log_path, {})

    if (not isinstance(cache_data, dict)):
        cache_data = {}

    cache_data.setdefault("log_file", "")
    cache_data.setdefault("offset", 0)
    cache_data.setdefault("partial", "")
    return cache_data


def get_cache_entry(log_path):
    if (log_path not in cache_entries):
        cache_entries[log_path] = default_cache_entry()
    cache_entry = cache_entries[log_path]
    cache_entry.setdefault("log_file", "")
    cache_entry.setdefault("offset", 0)
    cache_entry.setdefault("partial", "")
    return cache_entry


def player_is_queued_for_ban(player_id):
    for player in players_to_ban:
        if (player[0] == player_id):
            return True
    return False



def run() -> None:
    global config, log_paths, path_to_bans, cache_paths, search_logs_interval, verbose_logs
    print("Starting script...")

    config = load_config()
    try:
        log_paths = normalize_log_paths(config)
        path_to_bans = config["path_to_bans"]
        cache_paths = normalize_cache_paths(config, log_paths)
        search_logs_interval = int(config["search_logs_interval"])
        verbose_logs = int(config["verbose_logs"])

    except Exception as e:
        print(f"Ran into unexpected error loading variables from config:\n{e}")
        input("Press enter to close this window.")
        sys.exit(0)

    cache_path_by_log.clear()
    for log_path, cache_path in zip(log_paths, cache_paths):
        cache_path_by_log[log_path] = cache_path
        ensure_cache_file(cache_path)
        cache_entries[log_path] = load_cache_entry(cache_path, log_path)
    
    # verify core files are found
    valid_log_paths = []
    for log_path in log_paths:
        if (os.path.isdir(log_path) or os.path.isfile(log_path)):
            valid_log_paths.append(log_path)
        else:
            print(f"Failed to find log destination: \"{log_path}\"")
    if (len(valid_log_paths) == 0):
        input("Press enter to close this window.")
        sys.exit(0)
    if (not os.path.isfile(path_to_bans)):
        print(f"Failed to find ban file: \"{path_to_bans}\"")
        input("Press enter to close this window.")
        sys.exit(0)
    
    
    log_number = 0
    
    
    if (len(cache_entries) > 0):
        print("Last log read values loaded from cache.")
    
    time.sleep(1)
    print(f"Started searching for new logs. ({', '.join(valid_log_paths)})\n")
    time.sleep(1)
    
    
    while(True):
        
        for log_path in valid_log_paths:
            cache_entry = get_cache_entry(log_path)
            new_lines, log_file_path = read_new_lines(log_path, cache_entry)
            if (verbose_logs and len(new_lines) > 0):
                print(f"Found {len(new_lines)} new logs from {log_file_path}")

            # Search each new log message for death messages
            for line in new_lines:
                if (verbose_logs):
                    print(f"[{log_number}] {line}")

                death_event = parse_death_event(line, log_file_path)
                if (death_event):
                    player_id = death_event.steam_id
                    if (verbose_logs):
                        print(f"Found death log:\n    {line} Victim id: {player_id}")

                    if (player_id and not player_is_queued_for_ban(player_id)):
                        time_to_ban_player = time.time() + float(config["ban_delay"])
                        if (len(players_to_ban) > 0 and time_to_ban_player < players_to_ban[len(players_to_ban) - 1][1] + 2):
                            time_to_ban_player = players_to_ban[len(players_to_ban) - 1][1] + 2
                        players_to_ban.append((player_id, time_to_ban_player))
                        print(f"    Banning player with id: {player_id}.")
                        if (verbose_logs):
                            print(f"    This player will be banned in {time_to_ban_player - time.time()} seconds.")
                    if (verbose_logs):
                        print()

                log_number += 1

            if (verbose_logs and len(new_lines) > 0):
                print()
        try_to_ban_players()
        
        # time.sleep loop to cut out faster on interrupts
        sleep_amount = search_logs_interval
        while(sleep_amount > 0):
            sleep_inc = min(0.25, sleep_amount)
            time.sleep(sleep_inc)
            sleep_amount -= sleep_inc
    

if __name__ == "__main__":
    try:
        run()
        
    except KeyboardInterrupt:
        print("Closing program...")
        time.sleep(1.0)
        
    except Exception as e:
        print(f"Ran into an unexpected exception. Error: {e}")
        input("Press enter to close this window.")
