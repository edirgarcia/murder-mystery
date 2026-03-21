"""Tests for the Werewolf game."""

from __future__ import annotations

import random

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.werewolf.game_logic import (
    check_win_condition,
    resolve_day_vote,
    resolve_night,
    resolve_werewolf_vote,
)
from app.werewolf.game_state import WWPlayer, store as ww_store
from app.werewolf.models import Role, WinCondition
from app.werewolf.roles import assign_roles


@pytest.fixture(autouse=True)
def clean_store():
    """Reset store between tests and cancel background game tasks."""
    for room in ww_store._rooms.values():
        if room.game_task and not room.game_task.done():
            room.game_task.cancel()
    ww_store._rooms.clear()
    yield
    for room in ww_store._rooms.values():
        if room.game_task and not room.game_task.done():
            room.game_task.cancel()
    ww_store._rooms.clear()


@pytest.fixture
def client():
    return TestClient(app)


class TestRoleAssignment:
    def test_assign_roles_6_players(self):
        assignment = assign_roles([f"p{i}" for i in range(6)])
        values = list(assignment.roles.values())
        assert values.count(Role.WEREWOLF) == 2
        assert values.count(Role.SEER) == 1
        assert values.count(Role.WITCH) == 1
        assert values.count(Role.HUNTER) == 1
        assert values.count(Role.CUPID) == 1

    def test_assign_roles_10_players(self):
        assignment = assign_roles([f"p{i}" for i in range(10)])
        values = list(assignment.roles.values())
        assert values.count(Role.WEREWOLF) == 3

    def test_assign_roles_15_players(self):
        assignment = assign_roles([f"p{i}" for i in range(15)])
        values = list(assignment.roles.values())
        assert values.count(Role.WEREWOLF) == 4

    def test_alpha_wolf_is_a_werewolf(self):
        assignment = assign_roles([f"p{i}" for i in range(6)])
        assert assignment.alpha_wolf_id is not None
        assert assignment.roles[assignment.alpha_wolf_id] == Role.WEREWOLF


class TestNightResolution:
    def test_werewolf_kill_healed(self):
        players = {
            "p1": WWPlayer(id="p1", name="A", role=Role.VILLAGER, alive=True),
            "p2": WWPlayer(id="p2", name="B", role=Role.VILLAGER, alive=True),
        }
        out = resolve_night("p1", True, None, None, players)
        assert out.deaths == []

    def test_lover_chain(self):
        players = {
            "p1": WWPlayer(id="p1", name="A", role=Role.VILLAGER, alive=True),
            "p2": WWPlayer(id="p2", name="B", role=Role.VILLAGER, alive=True),
            "p3": WWPlayer(id="p3", name="C", role=Role.VILLAGER, alive=True),
        }
        out = resolve_night("p1", False, None, ("p1", "p2"), players)
        assert set(out.deaths) == {"p1", "p2"}
        assert out.death_causes["p2"] == "lover"


class TestDayVote:
    def test_plurality_wins(self):
        voted_out = resolve_day_vote({"a": "x", "b": "x", "c": "y"}, ["a", "b", "c", "x", "y"])
        assert voted_out == "x"

    def test_tie_no_elimination(self):
        voted_out = resolve_day_vote({"a": "x", "b": "y"}, ["a", "b", "x", "y"])
        assert voted_out is None

    def test_skip_blocks_elimination(self):
        voted_out = resolve_day_vote({"a": "skip", "b": "x"}, ["a", "b", "x"])
        assert voted_out is None


class TestWinCondition:
    def test_lovers_win(self):
        players = {
            "l1": WWPlayer(id="l1", name="L1", role=Role.VILLAGER, alive=True),
            "l2": WWPlayer(id="l2", name="L2", role=Role.WEREWOLF, alive=True),
            "x": WWPlayer(id="x", name="X", role=Role.VILLAGER, alive=False),
        }
        assert check_win_condition(players, ("l1", "l2")) == WinCondition.LOVERS

    def test_villagers_win(self):
        players = {
            "a": WWPlayer(id="a", name="A", role=Role.VILLAGER, alive=True),
            "w": WWPlayer(id="w", name="W", role=Role.WEREWOLF, alive=False),
        }
        assert check_win_condition(players, None) == WinCondition.VILLAGERS

    def test_werewolves_win(self):
        players = {
            "w1": WWPlayer(id="w1", name="W1", role=Role.WEREWOLF, alive=True),
            "v1": WWPlayer(id="v1", name="V1", role=Role.VILLAGER, alive=True),
        }
        assert check_win_condition(players, None) == WinCondition.WEREWOLVES


class TestWerewolfVote:
    def test_none_when_no_votes(self):
        assert resolve_werewolf_vote({}) is None

    def test_majority(self):
        assert resolve_werewolf_vote({"w1": "p1", "w2": "p1", "w3": "p2"}) == "p1"

    def test_tie_random_choice(self):
        random.seed(1)
        out = resolve_werewolf_vote({"w1": "p1", "w2": "p2"})
        assert out in {"p1", "p2"}

    def test_alpha_breaks_tie(self):
        result = resolve_werewolf_vote({"w1": "p1", "w2": "p2"}, alpha_wolf_id="w1")
        assert result == "p1"

    def test_alpha_breaks_tie_other_direction(self):
        result = resolve_werewolf_vote({"w1": "p2", "w2": "p1"}, alpha_wolf_id="w1")
        assert result == "p2"

    def test_majority_overrides_alpha(self):
        result = resolve_werewolf_vote({"w1": "p1", "w2": "p2", "w3": "p2"}, alpha_wolf_id="w1")
        assert result == "p2"

    def test_alpha_didnt_vote_falls_to_random(self):
        random.seed(1)
        result = resolve_werewolf_vote({"w2": "p1", "w3": "p2"}, alpha_wolf_id="w1")
        assert result in {"p1", "p2"}


class TestWWAPI:
    def _create_ww_game(self, client: TestClient, n: int = 6):
        create_res = client.post("/api/ww/games", json={"host_name": "Host"})
        code = create_res.json()["code"]
        host_id = create_res.json()["host_id"]
        player_ids = []

        names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank"]
        for i in range(n):
            res = client.post(
                f"/api/ww/games/{code}/join",
                json={"player_name": names[i]},
            )
            player_ids.append(res.json()["player_id"])

        return code, host_id, player_ids

    def test_create_join_and_start(self, client: TestClient):
        code, host_id, player_ids = self._create_ww_game(client, n=6)

        res = client.post(
            f"/api/ww/games/{code}/start",
            json={"discussion_seconds": 90},
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "started"

        info = client.get(f"/api/ww/games/{code}").json()
        assert info["phase"] == "playing"
        assert len(info["players"]) == 6
        assert info["discussion_seconds"] == 90

    def test_not_enough_players(self, client: TestClient):
        code, host_id, _ = self._create_ww_game(client, n=5)
        res = client.post(
            f"/api/ww/games/{code}/start",
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 400
        assert "Need at least" in res.json()["detail"]

    def test_non_host_cannot_start(self, client: TestClient):
        code, host_id, player_ids = self._create_ww_game(client, n=6)
        res = client.post(
            f"/api/ww/games/{code}/start",
            headers={"X-Player-Id": player_ids[0]},
        )
        assert res.status_code == 403

    def test_get_player_state(self, client: TestClient):
        code, host_id, player_ids = self._create_ww_game(client, n=6)
        client.post(
            f"/api/ww/games/{code}/start",
            headers={"X-Player-Id": host_id},
        )

        res = client.get(
            f"/api/ww/games/{code}/state",
            headers={"X-Player-Id": player_ids[0]},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["phase"] == "playing"
        assert "me" in data
        assert data["me"]["role"] in {
            Role.VILLAGER.value,
            Role.WEREWOLF.value,
            Role.SEER.value,
            Role.WITCH.value,
            Role.HUNTER.value,
            Role.CUPID.value,
        }
