"""Tests for the Prisoner's Dilemma game."""

from fastapi.testclient import TestClient

from app.main import app
from app.prisoners_dilemma.game_logic import resolve_team_accusation, score_choices
from app.prisoners_dilemma.game_state import store
from app.prisoners_dilemma.models import Decision, TeamColor


def _cancel_room_tasks() -> None:
    for room in list(store._rooms.values()):
        if room.game_task:
            room.game_task.cancel()


def setup_function() -> None:
    _cancel_room_tasks()
    store._rooms.clear()


def teardown_function() -> None:
    _cancel_room_tasks()
    store._rooms.clear()


def _create_game(client: TestClient, player_count: int = 4) -> tuple[str, str, list[str]]:
    create_res = client.post("/api/pd/games", json={"host_name": "Host"})
    data = create_res.json()
    code = data["code"]
    host_id = data["host_id"]

    player_ids: list[str] = []
    names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    for index in range(player_count):
        join_res = client.post(
            f"/api/pd/games/{code}/join",
            json={"player_name": names[index]},
        )
        player_ids.append(join_res.json()["player_id"])

    return code, host_id, player_ids


def test_start_assigns_two_teams_and_one_spy_each() -> None:
    client = TestClient(app)
    code, host_id, player_ids = _create_game(client)

    res = client.post(
        f"/api/pd/games/{code}/start",
        headers={"X-Player-Id": host_id},
    )
    assert res.status_code == 200

    info = client.get(f"/api/pd/games/{code}").json()
    assert info["phase"] == "playing"
    assert len(info["players"]) == 4

    teams = [player["team"] for player in info["players"]]
    assert teams.count("red") == 2
    assert teams.count("blue") == 2

    private_states = []
    for player_id in player_ids:
        private_res = client.get(
            f"/api/pd/games/{code}/me",
            headers={"X-Player-Id": player_id},
        )
        assert private_res.status_code == 200
        private_states.append(private_res.json())

    spies = [state for state in private_states if state["is_spy"]]
    assert len(spies) == 2
    assert {spy["team"] for spy in spies} == {"red", "blue"}
    assert all(spy["sabotage_charges"] == 3 for spy in spies)


def test_score_choices_matches_expected_matrix() -> None:
    assert score_choices(Decision.TRUST, Decision.TRUST) == {
        TeamColor.RED: 3,
        TeamColor.BLUE: 3,
    }
    assert score_choices(Decision.TRUST, Decision.BETRAY) == {
        TeamColor.RED: -6,
        TeamColor.BLUE: 6,
    }
    assert score_choices(Decision.BETRAY, Decision.TRUST) == {
        TeamColor.RED: 6,
        TeamColor.BLUE: -6,
    }
    assert score_choices(Decision.BETRAY, Decision.BETRAY) == {
        TeamColor.RED: -3,
        TeamColor.BLUE: -3,
    }


def test_accusation_requires_majority_and_unique_target() -> None:
    team_player_ids = ["a", "b", "c", "d"]

    no_accusation = resolve_team_accusation(
        team_player_ids,
        {"a": "x", "b": None, "c": None, "d": None},
        active_spy_id="x",
    )
    assert no_accusation["accusation_triggered"] is False

    tie_accusation = resolve_team_accusation(
        team_player_ids,
        {"a": "x", "b": "y", "c": "x", "d": "y"},
        active_spy_id="x",
    )
    assert tie_accusation["accusation_triggered"] is False

    correct_accusation = resolve_team_accusation(
        team_player_ids,
        {"a": "x", "b": "x", "c": "x", "d": None},
        active_spy_id="x",
    )
    assert correct_accusation["accusation_triggered"] is True
    assert correct_accusation["correct"] is True
    assert correct_accusation["score_delta"] == 0
