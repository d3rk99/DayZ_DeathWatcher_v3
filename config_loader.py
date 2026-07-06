import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple


class ConfigError(Exception):
    pass


DEFAULT_CONFIG: Dict[str, Any] = {
    "death_timer_seconds": 1209600,
    "revive_dm_message": "You have been revived! Your dead role has been removed. Welcome back.",
    "watch_death_watcher": True,
    "death_watcher_alive_time_path": "./death_watcher/alive_times.txt",
    "alive_leaderboard_channel_id": -1,
    "leaderboard_text_channel_id": -1,
    "sync_enabled": False,
    "web_ui": {
        "host": "127.0.0.1",
        "port": 8080,
        "log_tail_lines": 200,
        "bot_log_path": "./bot.log",
    },
}


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _expand_path(path_value: str, base_dir: Path) -> Path:
    expanded = os.path.expanduser(os.path.expandvars(str(path_value)))
    path = Path(expanded)
    if (not path.is_absolute()):
        path = base_dir / path
    return path.resolve()


def _coerce_bool(value: Any, key: str) -> bool:
    if (isinstance(value, bool)):
        return value
    if (isinstance(value, int) and value in (0, 1)):
        return bool(value)
    if (isinstance(value, str)):
        normalized = value.strip().lower()
        if (normalized in ("true", "1", "yes", "on")):
            return True
        if (normalized in ("false", "0", "no", "off")):
            return False
    raise ConfigError(f"'{key}' must be true or false. Existing 0/1 values are still accepted.")


def config_bool(value: Any) -> bool:
    return _coerce_bool(value, "boolean setting")


def _coerce_int(value: Any, key: str, allow_negative_one: bool = False) -> int:
    try:
        coerced = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"'{key}' must be a number.") from exc
    if (coerced < 0 and not (allow_negative_one and coerced == -1)):
        raise ConfigError(f"'{key}' must be a positive number.")
    return coerced


def _require_string(config: Dict[str, Any], key: str) -> str:
    value = config.get(key)
    if (not isinstance(value, str) or value.strip() == ""):
        raise ConfigError(f"Missing or invalid '{key}'.")
    return value


def _require_int(config: Dict[str, Any], key: str, allow_negative_one: bool = False) -> int:
    value = _coerce_int(config.get(key), key, allow_negative_one=allow_negative_one)
    config[key] = value
    return value


def _validate_existing_file(config: Dict[str, Any], key: str, base_dir: Path) -> Path:
    raw_path = _require_string(config, key)
    path = _expand_path(raw_path, base_dir)
    if (not path.is_file()):
        raise ConfigError(f"'{key}' points to a file that does not exist: {raw_path}")
    return path


def _validate_parent_for_runtime_file(config: Dict[str, Any], key: str, base_dir: Path) -> None:
    raw_path = _require_string(config, key)
    path = _expand_path(raw_path, base_dir)
    if (not path.parent.is_dir()):
        raise ConfigError(f"'{key}' directory does not exist: {path.parent}")


def _target_paths(syncer_config: Dict[str, Any], key: str, base_dir: Path, *, check_exists: bool) -> List[Path]:
    value = syncer_config.get(key)
    if (not isinstance(value, list) or len(value) == 0):
        raise ConfigError(f"'syncer.{key}' must be a non-empty list when sync_enabled is true.")

    resolved: List[Path] = []
    seen = set()
    for index, item in enumerate(value, start=1):
        if (not isinstance(item, str) or item.strip() == ""):
            raise ConfigError(f"'syncer.{key}' entry {index} must be a file path.")
        path = _expand_path(item, base_dir)
        normalized = os.path.normcase(str(path))
        if (normalized in seen):
            raise ConfigError(f"'syncer.{key}' contains a duplicate target path: {item}")
        if (check_exists and not path.is_file()):
            raise ConfigError(f"'syncer.{key}' target file does not exist: {item}")
        seen.add(normalized)
        resolved.append(path)
    return resolved


def _apply_defaults(config: Dict[str, Any]) -> None:
    for key, value in DEFAULT_CONFIG.items():
        if (key == "web_ui"):
            web_config = config.get("web_ui")
            if (not isinstance(web_config, dict)):
                web_config = {}
            config["web_ui"] = {**value, **web_config}
            continue
        config.setdefault(key, value)
    config.setdefault("leaderboard_text_channel_id", config.get("alive_leaderboard_channel_id", -1))


def _apply_legacy_sync_path_fallbacks(config: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    syncer_config = config.get("syncer")
    if (not isinstance(syncer_config, dict)):
        return warnings

    legacy_pairs = [
        ("whitelist_path", "whitelist_sync_path"),
        ("blacklist_path", "blacklist_sync_path"),
    ]
    for new_key, legacy_key in legacy_pairs:
        if (_is_missing(config.get(new_key)) and not _is_missing(syncer_config.get(legacy_key))):
            config[new_key] = syncer_config[legacy_key]
            warnings.append(
                f"Using deprecated 'syncer.{legacy_key}' as '{new_key}'. Move this value to the top level of config.json."
            )
    return warnings


def load_json_config(config_path: str = "config.json") -> Dict[str, Any]:
    path = Path(config_path)
    if (not path.is_file()):
        raise ConfigError("config.json not found. Copy config.example.json to config.json and edit it first.")
    try:
        with open(path, "r") as file:
            config = json.load(file)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"config.json is not valid JSON: {exc}") from exc
    if (not isinstance(config, dict)):
        raise ConfigError("config.json must contain a JSON object.")
    return config


def validate_config(
    config: Dict[str, Any],
    *,
    base_dir: str | Path = ".",
    check_files: bool = True,
    require_discord: bool = True,
) -> Tuple[Dict[str, Any], List[str]]:
    base_path = Path(base_dir).resolve()
    warnings = _apply_legacy_sync_path_fallbacks(config)
    _apply_defaults(config)

    config["sync_enabled"] = _coerce_bool(config.get("sync_enabled"), "sync_enabled")
    config["watch_death_watcher"] = _coerce_bool(config.get("watch_death_watcher"), "watch_death_watcher")
    config["error_dump_allow_mention"] = _coerce_bool(config.get("error_dump_allow_mention", False), "error_dump_allow_mention")

    for key in ("prefix", "token", "whitelist_path", "blacklist_path", "userdata_db_path", "death_watcher_death_path", "steam_ids_to_unban_path"):
        _require_string(config, key)

    if (require_discord):
        for key in ("admin_role_id", "guild_id", "join_vc_id", "join_vc_category_id", "alive_role", "dead_role"):
            _require_int(config, key)
        _require_int(config, "validate_steam_id_channel", allow_negative_one=True)
        _require_int(config, "error_dump_channel", allow_negative_one=True)
        _require_int(config, "alive_leaderboard_channel_id", allow_negative_one=True)
        _require_int(config, "leaderboard_text_channel_id", allow_negative_one=True)

    _coerce_int(config.get("death_timer_seconds"), "death_timer_seconds")

    web_config = config["web_ui"]
    if (not isinstance(web_config.get("host"), str) or web_config["host"].strip() == ""):
        raise ConfigError("'web_ui.host' must be a host name or IP address.")
    web_config["port"] = _coerce_int(web_config.get("port"), "web_ui.port")
    web_config["log_tail_lines"] = _coerce_int(web_config.get("log_tail_lines"), "web_ui.log_tail_lines")

    if (check_files):
        _validate_existing_file(config, "whitelist_path", base_path)
        _validate_existing_file(config, "blacklist_path", base_path)
        _validate_parent_for_runtime_file(config, "userdata_db_path", base_path)
        _validate_parent_for_runtime_file(config, "steam_ids_to_unban_path", base_path)
        if (config["watch_death_watcher"]):
            _validate_parent_for_runtime_file(config, "death_watcher_death_path", base_path)
            _validate_parent_for_runtime_file(config, "death_watcher_alive_time_path", base_path)

    if (not config["sync_enabled"]):
        return config, warnings

    syncer_config = config.get("syncer")
    if (not isinstance(syncer_config, dict)):
        raise ConfigError("'syncer' section is required when sync_enabled is true.")

    whitelist_targets = _target_paths(syncer_config, "whitelist_server_paths", base_path, check_exists=check_files)
    blacklist_targets = _target_paths(syncer_config, "blacklist_server_paths", base_path, check_exists=check_files)

    sync_interval = _coerce_int(syncer_config.get("sync_interval_seconds", 10), "syncer.sync_interval_seconds")
    if (sync_interval <= 0):
        raise ConfigError("'syncer.sync_interval_seconds' must be greater than 0.")
    syncer_config["sync_interval_seconds"] = sync_interval

    if (check_files):
        master_paths = {
            os.path.normcase(str(_expand_path(config["whitelist_path"], base_path))): "whitelist_path",
            os.path.normcase(str(_expand_path(config["blacklist_path"], base_path))): "blacklist_path",
        }
        for target in whitelist_targets + blacklist_targets:
            normalized = os.path.normcase(str(target))
            if (normalized in master_paths):
                raise ConfigError(f"Sync target duplicates the master '{master_paths[normalized]}': {target}")

    return config, warnings


def load_config(
    config_path: str = "config.json",
    *,
    check_files: bool = True,
    require_discord: bool = True,
) -> Tuple[Dict[str, Any], List[str]]:
    path = Path(config_path)
    config = load_json_config(str(path))
    return validate_config(
        config,
        base_dir=path.parent if path.parent != Path("") else Path("."),
        check_files=check_files,
        require_discord=require_discord,
    )


def server_deployment_count(config: Dict[str, Any]) -> int:
    syncer_config = config.get("syncer", {})
    if (not isinstance(syncer_config, dict)):
        return 0
    whitelist_count = len(syncer_config.get("whitelist_server_paths", [])) if isinstance(syncer_config.get("whitelist_server_paths"), list) else 0
    blacklist_count = len(syncer_config.get("blacklist_server_paths", [])) if isinstance(syncer_config.get("blacklist_server_paths"), list) else 0
    return max(whitelist_count, blacklist_count)


def sync_startup_message(config: Dict[str, Any]) -> str:
    if (not config.get("sync_enabled", False)):
        return "Sync disabled: running in single-server mode."
    return f"Sync enabled: master lists will sync to {server_deployment_count(config)} server deployment(s)."
