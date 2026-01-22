import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiohttp import web

BASE_DIR = Path(__file__).resolve().parent
WEB_ROOT = BASE_DIR / "web_ui"
STATIC_ROOT = WEB_ROOT / "static"

DEFAULT_WEB_CONFIG = {
    "host": "0.0.0.0",
    "port": 8080,
    "log_tail_lines": 200,
}


def load_config() -> Dict[str, Any]:
    if (not Path("config.json").is_file()):
        raise FileNotFoundError("config.json not found. Please create it before starting the WebUI.")
    with open("config.json", "r") as file:
        config = json.load(file)
    web_config = config.get("web_ui", {})
    merged_web_config = {**DEFAULT_WEB_CONFIG, **web_config}
    config["web_ui"] = merged_web_config
    return config


def normalize_userdata_db(userdata_json: Any) -> Dict[str, Any]:
    changed = False
    if (not isinstance(userdata_json, dict)):
        userdata_json = {}
        changed = True
    if ("userdata" not in userdata_json or not isinstance(userdata_json["userdata"], dict)):
        userdata_json["userdata"] = {}
        changed = True
    if ("season_deaths" not in userdata_json or not isinstance(userdata_json["season_deaths"], list)):
        userdata_json["season_deaths"] = []
        changed = True
    return userdata_json


def safe_path(path_value: str) -> Path:
    expanded = os.path.expanduser(os.path.expandvars(path_value))
    return Path(expanded)


def read_user_db(db_path: str) -> Dict[str, Any]:
    path = safe_path(db_path)
    if (not path.is_file()):
        return {"userdata": {}, "season_deaths": []}
    with open(path, "r") as file:
        data = json.load(file)
    return normalize_userdata_db(data)


def write_user_db(db_path: str, data: Dict[str, Any]) -> None:
    path = safe_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as file:
        json.dump(data, file, indent=4)


def format_timestamp(ts: Optional[float]) -> Optional[str]:
    if (ts is None):
        return None
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def file_info(path_value: str) -> Dict[str, Any]:
    path = safe_path(path_value)
    info: Dict[str, Any] = {"path": str(path), "exists": path.is_file()}
    if (path.is_file()):
        stat = path.stat()
        info["size_bytes"] = stat.st_size
        info["modified"] = format_timestamp(stat.st_mtime)
        try:
            with open(path, "r") as file:
                lines = [line for line in (line.strip() for line in file.readlines()) if line]
            info["entries"] = len(lines)
        except Exception as exc:
            info["error"] = str(exc)
    return info


def tail_lines(path_value: str, max_lines: int) -> Dict[str, Any]:
    path = safe_path(path_value)
    data: Dict[str, Any] = {"path": str(path), "exists": path.is_file(), "lines": []}
    if (not path.is_file()):
        return data
    try:
        with open(path, "r", errors="ignore") as file:
            lines = file.readlines()
        data["lines"] = [line.rstrip("\n") for line in lines[-max_lines:]]
    except Exception as exc:
        data["error"] = str(exc)
    return data


def read_death_watcher_config() -> Dict[str, Any]:
    config_path = BASE_DIR / "death_watcher" / "config.json"
    if (not config_path.is_file()):
        return {}
    with open(config_path, "r") as file:
        return json.load(file)


def extract_log_paths(dw_config: Dict[str, Any]) -> List[str]:
    log_paths_value = dw_config.get("log_paths")
    if (log_paths_value is None):
        log_paths_value = dw_config.get("log_path")
    if (log_paths_value is None):
        log_paths_value = dw_config.get("path_to_logs")
    if (log_paths_value is None):
        return []
    if (not isinstance(log_paths_value, list)):
        return [str(log_paths_value)]
    return [str(item) for item in log_paths_value if item]


def serialize_user_entry(user_id: str, userdata: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "username": userdata.get("username"),
        "steam_id": userdata.get("steam_id"),
        "guid": userdata.get("guid"),
        "is_alive": int(userdata.get("is_alive", 0)),
        "time_of_death": userdata.get("time_of_death", 0),
        "is_admin": int(userdata.get("is_admin", 0)),
    }


async def index(_: web.Request) -> web.Response:
    return web.FileResponse(WEB_ROOT / "index.html")


async def static_files(request: web.Request) -> web.Response:
    filename = request.match_info.get("filename", "")
    file_path = STATIC_ROOT / filename
    if (not file_path.is_file()):
        raise web.HTTPNotFound()
    return web.FileResponse(file_path)


async def api_userdata(request: web.Request) -> web.Response:
    config = request.app["config"]
    db = read_user_db(config["userdata_db_path"])
    entries = [serialize_user_entry(user_id, data) for user_id, data in db["userdata"].items()]
    entries.sort(key=lambda item: (item.get("username") or "").lower())
    return web.json_response({"users": entries, "count": len(entries)})


async def api_userdata_search(request: web.Request) -> web.Response:
    config = request.app["config"]
    query = request.query.get("q", "").strip().lower()
    db = read_user_db(config["userdata_db_path"])
    results = []
    for user_id, data in db["userdata"].items():
        serialized = serialize_user_entry(user_id, data)
        if (not query):
            results.append(serialized)
            continue
        haystack = " ".join(
            [
                str(serialized.get("user_id", "")),
                str(serialized.get("username", "")),
                str(serialized.get("steam_id", "")),
                str(serialized.get("guid", "")),
            ]
        ).lower()
        if (query in haystack):
            results.append(serialized)
    results.sort(key=lambda item: (item.get("username") or "").lower())
    return web.json_response({"users": results, "count": len(results)})


async def api_userdata_update(request: web.Request) -> web.Response:
    config = request.app["config"]
    user_id = request.match_info["user_id"]
    payload = await request.json()

    db = read_user_db(config["userdata_db_path"])
    if (user_id not in db["userdata"]):
        raise web.HTTPNotFound(text="User not found")

    userdata = db["userdata"][user_id]
    if ("is_admin" in payload):
        userdata["is_admin"] = int(payload["is_admin"])
    if ("is_alive" in payload):
        userdata["is_alive"] = int(payload["is_alive"])
        if (userdata["is_alive"] == 1):
            userdata["time_of_death"] = 0
    db["userdata"][user_id] = userdata
    write_user_db(config["userdata_db_path"], db)

    return web.json_response({"user": serialize_user_entry(user_id, userdata)})


async def api_userdata_delete(request: web.Request) -> web.Response:
    config = request.app["config"]
    user_id = request.match_info["user_id"]
    db = read_user_db(config["userdata_db_path"])
    if (user_id not in db["userdata"]):
        raise web.HTTPNotFound(text="User not found")
    deleted = db["userdata"].pop(user_id)
    write_user_db(config["userdata_db_path"], db)
    return web.json_response({"deleted": serialize_user_entry(user_id, deleted)})


async def api_logs(request: web.Request) -> web.Response:
    config = request.app["config"]
    dw_config = read_death_watcher_config()
    log_paths = extract_log_paths(dw_config)
    tail_count = int(config["web_ui"].get("log_tail_lines", 200))
    logs = [tail_lines(path, tail_count) for path in log_paths]
    death_path = config.get("death_watcher_death_path")
    death_info = file_info(death_path) if death_path else {"path": None, "exists": False}
    return web.json_response({
        "log_paths": logs,
        "death_watcher_deaths": death_info,
    })


async def api_sync(request: web.Request) -> web.Response:
    config = request.app["config"]
    syncer_config = config.get("syncer", {})

    whitelist_sync = syncer_config.get("whitelist_sync_path")
    blacklist_sync = syncer_config.get("blacklist_sync_path")

    whitelist_servers = syncer_config.get("whitelist_server_paths", [])
    blacklist_servers = syncer_config.get("blacklist_server_paths", [])

    return web.json_response({
        "sync_interval_seconds": syncer_config.get("sync_interval_seconds"),
        "whitelist_sync": file_info(whitelist_sync) if whitelist_sync else {"path": None, "exists": False},
        "blacklist_sync": file_info(blacklist_sync) if blacklist_sync else {"path": None, "exists": False},
        "whitelist_servers": [file_info(path) for path in whitelist_servers],
        "blacklist_servers": [file_info(path) for path in blacklist_servers],
    })


async def api_overview(request: web.Request) -> web.Response:
    config = request.app["config"]
    dw_config = read_death_watcher_config()
    log_paths = extract_log_paths(dw_config)
    response = {
        "userdata_db": file_info(config.get("userdata_db_path", "")),
        "whitelist": file_info(config.get("whitelist_path", "")),
        "blacklist": file_info(config.get("blacklist_path", "")),
        "death_watcher_logs": [file_info(path) for path in log_paths],
        "death_watcher_deaths": file_info(config.get("death_watcher_death_path", "")),
        "syncer": {
            "interval": config.get("syncer", {}).get("sync_interval_seconds"),
            "whitelist_sync": file_info(config.get("syncer", {}).get("whitelist_sync_path", "")),
            "blacklist_sync": file_info(config.get("syncer", {}).get("blacklist_sync_path", "")),
        },
    }
    return web.json_response(response)


def create_app() -> web.Application:
    app = web.Application()
    config = load_config()
    app["config"] = config

    app.router.add_get("/", index)
    app.router.add_get("/static/{filename}", static_files)
    app.router.add_get("/api/overview", api_overview)
    app.router.add_get("/api/userdata", api_userdata)
    app.router.add_get("/api/userdata/search", api_userdata_search)
    app.router.add_patch("/api/userdata/{user_id}", api_userdata_update)
    app.router.add_delete("/api/userdata/{user_id}", api_userdata_delete)
    app.router.add_get("/api/logs", api_logs)
    app.router.add_get("/api/sync", api_sync)

    return app


def main() -> None:
    config = load_config()
    host = config["web_ui"]["host"]
    port = int(config["web_ui"]["port"])
    print(f"WebUI ready on http://{host}:{port} (LAN accessible)")
    web.run_app(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
