import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest

from config_loader import ConfigError, validate_config
from syncer import read_entries, sync_list


def write_file(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def base_config(tmp_path: Path) -> dict:
    write_file(tmp_path / "whitelist.txt", "76561198000000001\n")
    write_file(tmp_path / "ban.txt", "")
    (tmp_path / "death_watcher").mkdir()
    return {
        "prefix": "*",
        "token": "DISCORD_BOT_TOKEN",
        "sync_enabled": False,
        "whitelist_path": "whitelist.txt",
        "blacklist_path": "ban.txt",
        "userdata_db_path": "userdata_db.json",
        "admin_role_id": 1,
        "guild_id": 2,
        "join_vc_id": 3,
        "join_vc_category_id": 4,
        "validate_steam_id_channel": 5,
        "alive_role": 6,
        "dead_role": 7,
        "death_timer_seconds": 1209600,
        "revive_dm_message": "Revived",
        "watch_death_watcher": True,
        "death_watcher_death_path": "death_watcher/deaths.txt",
        "death_watcher_alive_time_path": "death_watcher/alive_times.txt",
        "steam_ids_to_unban_path": "steam_ids_to_unban.txt",
        "error_dump_channel": -1,
        "error_dump_allow_mention": False,
        "error_dump_mention_tag": "everyone",
        "web_ui": {
            "host": "127.0.0.1",
            "port": 8080,
            "log_tail_lines": 200,
            "bot_log_path": "bot.log",
        },
        "syncer": {
            "whitelist_server_paths": [],
            "blacklist_server_paths": [],
            "sync_interval_seconds": 10,
        },
        "alive_leaderboard_channel_id": -1,
        "leaderboard_text_channel_id": -1,
    }


def add_sync_targets(config: dict, tmp_path: Path) -> dict:
    write_file(tmp_path / "server1" / "whitelist.txt", "")
    write_file(tmp_path / "server1" / "ban.txt", "")
    config["sync_enabled"] = True
    config["syncer"] = {
        "whitelist_server_paths": ["server1/whitelist.txt"],
        "blacklist_server_paths": ["server1/ban.txt"],
        "sync_interval_seconds": 10,
    }
    return config


def test_single_server_mode_does_not_require_syncer_targets(tmp_path):
    config = base_config(tmp_path)
    config.pop("syncer")

    validated, warnings = validate_config(config, base_dir=tmp_path)

    assert validated["sync_enabled"] is False
    assert warnings == []


def test_multi_server_mode_with_valid_sync_targets(tmp_path):
    config = add_sync_targets(base_config(tmp_path), tmp_path)

    validated, _ = validate_config(config, base_dir=tmp_path)

    assert validated["sync_enabled"] is True
    assert validated["syncer"]["sync_interval_seconds"] == 10


def test_multi_server_mode_missing_target_lists_fails(tmp_path):
    config = base_config(tmp_path)
    config["sync_enabled"] = True
    config["syncer"] = {"sync_interval_seconds": 10}

    with pytest.raises(ConfigError, match="whitelist_server_paths"):
        validate_config(config, base_dir=tmp_path)


def test_invalid_sync_enabled_type_fails(tmp_path):
    config = base_config(tmp_path)
    config["sync_enabled"] = "sometimes"

    with pytest.raises(ConfigError, match="sync_enabled"):
        validate_config(config, base_dir=tmp_path)


def test_duplicate_master_and_target_list_entries_fail(tmp_path):
    config = base_config(tmp_path)
    write_file(tmp_path / "server1" / "ban.txt", "")
    config["sync_enabled"] = True
    config["syncer"] = {
        "whitelist_server_paths": ["whitelist.txt"],
        "blacklist_server_paths": ["server1/ban.txt"],
        "sync_interval_seconds": 10,
    }

    with pytest.raises(ConfigError, match="duplicates the master"):
        validate_config(config, base_dir=tmp_path)


def test_whitelist_and_ban_sync_overwrite_targets(tmp_path):
    master_whitelist = write_file(tmp_path / "master_whitelist.txt", "a\nb\nb\n\n")
    master_ban = write_file(tmp_path / "master_ban.txt", "c\n")
    target_whitelist = write_file(tmp_path / "server" / "whitelist.txt", "old\n")
    target_ban = write_file(tmp_path / "server" / "ban.txt", "old\n")

    sync_list(str(master_whitelist), [str(target_whitelist)], "whitelist")
    sync_list(str(master_ban), [str(target_ban)], "blacklist")

    assert read_entries(str(target_whitelist)) == ["a", "b"]
    assert read_entries(str(target_ban)) == ["c"]


def test_disabled_sync_does_not_validate_sync_only_paths(tmp_path):
    config = base_config(tmp_path)
    config["syncer"] = {
        "whitelist_server_paths": ["C:/Definitely/Missing/whitelist.txt"],
        "blacklist_server_paths": "not a list",
        "sync_interval_seconds": 10,
    }

    validated, _ = validate_config(config, base_dir=tmp_path)

    assert validated["sync_enabled"] is False


def test_legacy_syncer_master_paths_are_used_when_top_level_missing(tmp_path):
    config = base_config(tmp_path)
    config.pop("whitelist_path")
    config.pop("blacklist_path")
    add_sync_targets(config, tmp_path)
    config["syncer"]["whitelist_sync_path"] = "whitelist.txt"
    config["syncer"]["blacklist_sync_path"] = "ban.txt"

    validated, warnings = validate_config(config, base_dir=tmp_path)

    assert validated["whitelist_path"] == "whitelist.txt"
    assert validated["blacklist_path"] == "ban.txt"
    assert len(warnings) == 2


def test_numeric_boolean_style_values_remain_supported(tmp_path):
    config = base_config(tmp_path)
    config["watch_death_watcher"] = 1
    config["error_dump_allow_mention"] = 0

    validated, _ = validate_config(config, base_dir=tmp_path)

    assert validated["watch_death_watcher"] is True
    assert validated["error_dump_allow_mention"] is False
