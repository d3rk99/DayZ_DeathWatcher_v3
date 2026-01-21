import time
import sys
import os
import json


os.system("title " + "DayZ Death Watcher")

try:
    with open("./config.json", "r") as json_file:
        config = json.load(json_file)
except FileNotFoundError:
    print("Generating default config file: (config.json)")
    with open("./config.json", "w") as json_file:
        json_file.write("""{
  "log_paths" : ["../profiles/DayZServer_x64.ADM"],
  "path_to_bans" : "./deaths.txt",
  "path_to_cache" : "./death_watcher_cache.json",
  "death_cues" : ["killed by", "committed suicide", "bled out", "died.", "(DEAD)", "was brutally murdered by that psycho Timmy"],
  "ban_delay" : 5,
  "search_logs_interval" : 1,
  "verbose_logs" : 1
}""")

with open("./config.json", "r") as json_file:
    config = json.load(json_file)


# create last read log file if it doesn't exist
if (not os.path.isfile(config["path_to_cache"])):
    print(f"Failed to find cache file: {config['path_to_cache']}\nCreating it now.")
    with open(config["path_to_cache"], "w") as file:
        file.write("""{
  "logs" : {}
}""")

with open(config["path_to_cache"], "r") as json_file:
    current_cache = json.load(json_file)



try:
    log_paths = config.get("log_paths", None)
    if (log_paths is None):
        log_paths = [config.get("path_to_logs", "")]
    if (not isinstance(log_paths, list)):
        log_paths = [log_paths]
    log_paths = [path for path in log_paths if path]
    if (len(log_paths) > 5):
        log_paths = log_paths[:5]
    path_to_bans = config["path_to_bans"]
    path_to_cache = config["path_to_cache"]
    death_cues = config["death_cues"]
    search_logs_interval = int(config["search_logs_interval"])
    verbose_logs = int(config["verbose_logs"])

except Exception as e:
    print(f"Ran into unexpected error loading variables from config:\n{e}")
    input("Press enter to close this window.")
    sys.exit(0)


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
    with open(path_to_bans, "r") as file:
        ban_list = file.read().split('\n')
        
    if (not player_id in ban_list):
        with open(path_to_bans, "a") as file:
            file.write(f"{player_id}\n")
        if (verbose_logs):
            print(f"Added player with id: {player_id} to ban file: {path_to_bans}")


def resolve_log_file(log_path):
    if (os.path.isdir(log_path)):
        try:
            candidates = []
            for name in os.listdir(log_path):
                if (name.endswith(".ljson")):
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
        cache_entry["prev_log_read"] = ""
        cache_entry["log_file"] = log_file_path
        update_cache()

    try:
        with open(log_file_path, "r") as file:
            lines = file.read().split("\n")
    except Exception:
        time.sleep(10)
        return [], log_file_path

    while ("" in lines):
        lines.remove("")

    lines.reverse()

    new_lines = []
    for line in lines:
        if (line == cache_entry["prev_log_read"]):
            break
        new_lines.insert(0, line)

    return new_lines, log_file_path


def is_death_log(line):
    if (line.lstrip().startswith("{")):
        try:
            log_data = json.loads(line)
        except Exception:
            return False
        if (log_data.get("event") != "PLAYER_DEATH_DETAILS"):
            return False
        player_data = log_data.get("player", {})
        player_position = player_data.get("position", {})
        x = player_position.get("x", None)
        y = player_position.get("y", None)
        z = player_position.get("z", None)
        if (x is None or y is None or z is None):
            return False
        if (x == 0 and y == 0 and z == 0):
            return False
        return True

    for death in death_cues:
        if (death in line and not f'"{death}' in line and not f"'{death}" in line):
            return True

    return False


def get_id_from_line(line):
    if (line.lstrip().startswith("{")):
        try:
            log_data = json.loads(line)
        except Exception:
            return ""
        if (log_data.get("event") != "PLAYER_DEATH_DETAILS"):
            return ""
        player_data = log_data.get("player", {})
        player_id = player_data.get("steamId", "")
        if (not player_id):
            return ""
        player_position = player_data.get("position", {})
        x = player_position.get("x", None)
        y = player_position.get("y", None)
        z = player_position.get("z", None)
        if (x is None or y is None or z is None):
            return ""
        if (x == 0 and y == 0 and z == 0):
            return ""
        return player_id

    index = line.find("(id=")
    start_index = index + 4

    if (index == -1 or len(line) < (start_index + 44)):
        return ""

    player_id = ""
    player_id = line[start_index:start_index + 44]

    if ("Unknown" in player_id):
        return ""

    return player_id


def update_cache():
    with open(config["path_to_cache"], "w") as json_file:
        json.dump(current_cache, json_file, indent = 4)
    if (verbose_logs):
        print(f"Updated cache file:\n    {current_cache}")
    
    
def load_cache():
    with open(config["path_to_cache"], "r") as json_file:
        cache_data = json.load(json_file)
    if ("logs" not in cache_data):
        cache_data = {"logs": {}}
    if ("logs" not in cache_data):
        cache_data["logs"] = {}
    return cache_data


def get_cache_entry(log_path):
    if (log_path not in current_cache["logs"]):
        current_cache["logs"][log_path] = {"prev_log_read": "", "log_file": ""}
    return current_cache["logs"][log_path]


def player_is_queued_for_ban(player_id):
    for player in players_to_ban:
        if (player[0] == player_id):
            return True
    return False



def __main__():
    global current_cache
    print("Starting script...")
    
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
    
    
    current_cache = load_cache()
    log_number = 0
    
    
    if (len(current_cache.get("logs", {})) > 0):
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

                # If current log message is a death message, get their id, and ban them
                if (is_death_log(line)):
                    player_id = get_id_from_line(line)
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

                # Update last log message to know where we already searched for death messages
                cache_entry["prev_log_read"] = line
                cache_entry["log_file"] = log_file_path
                update_cache()

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
    

try:
    __main__()
    
except KeyboardInterrupt:
    print("Closing program...")
    time.sleep(1.0)
    
except Exception as e:
    print(f"Ran into an unexpected exception. Error: {e}")
    input("Press enter to close this window.")
