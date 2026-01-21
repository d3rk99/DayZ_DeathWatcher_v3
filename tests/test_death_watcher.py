import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import death_watcher.new_dayz_death_watcher as dw


PLAYER_DEATH_DETAILS_LINE = (
    '{"ts":"2026-01-20T21:12:28.773","event":"PLAYER_DEATH_DETAILS",'
    '"data":{"details":"suicide"},'
    '"player":{"steamId":"76561198009232482","position":{"x":1342.71,"y":311.11,"z":9329.72},'
    '"direction":{"x":0.701497,"y":0,"z":-0.712673},"aliveSec":940,"dead":true}}'
)

PLAYER_DEATH_LINE = (
    '{"ts":"2026-01-20T20:43:04.889","event":"PLAYER_DEATH","sub_event":"suicide",'
    '"player":{"steamId":"76561198009232482","position":{"x":0,"y":0,"z":0}}}'
)


def test_player_death_details_triggers():
    event = dw.parse_death_event(PLAYER_DEATH_DETAILS_LINE, "source")
    assert event is not None
    assert event.steam_id == "76561198009232482"


def test_player_death_does_not_trigger():
    event = dw.parse_death_event(PLAYER_DEATH_LINE, "source")
    assert event is None


def test_player_death_details_zero_position_does_not_trigger():
    line = (
        '{"ts":"2026-01-20T21:12:28.773","event":"PLAYER_DEATH_DETAILS",'
        '"data":{"details":"suicide"},'
        '"player":{"steamId":"76561198009232482","position":{"x":0,"y":0,"z":0}}}'
    )
    event = dw.parse_death_event(line, "source")
    assert event is None


def test_multiple_log_folders_yield_events(tmp_path):
    dw.cache_entries.clear()
    dw.cache_path_by_log.clear()
    dw.verbose_logs = 0
    folder_one = tmp_path / "server_one"
    folder_two = tmp_path / "server_two"
    folder_one.mkdir()
    folder_two.mkdir()

    file_one = folder_one / "dl_20260120_191816.ljson"
    file_two = folder_two / "dl_20260121_091816.ljson"

    file_one.write_text(PLAYER_DEATH_DETAILS_LINE + "\n")
    file_two.write_text(
        '{"ts":"2026-01-20T21:12:28.773","event":"PLAYER_DEATH_DETAILS",'
        '"data":{"details":"suicide"},'
        '"player":{"steamId":"11111111111111111","position":{"x":1,"y":2,"z":3}}}'
        + "\n"
    )

    events = []
    for log_path in [str(folder_one), str(folder_two)]:
        cache_path = tmp_path / f"{Path(log_path).name}_cache.json"
        dw.cache_path_by_log[log_path] = str(cache_path)
        dw.ensure_cache_file(str(cache_path))
        dw.cache_entries[log_path] = dw.load_cache_entry(str(cache_path), log_path)
        cache_entry = dw.get_cache_entry(log_path)
        new_lines, log_file_path = dw.read_new_lines(log_path, cache_entry)
        for line in new_lines:
            event = dw.parse_death_event(line, log_file_path)
            if event:
                events.append(event)

    assert {event.steam_id for event in events} == {
        "76561198009232482",
        "11111111111111111",
    }
