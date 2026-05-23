"""Tests for the Basta game."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.basta.config import DEFAULT_CATEGORIES
from app.basta.game_state import store as basta_store
from app.basta.routes.game import _flush_missing_drafts, _vetoed_answers
from app.basta.scoring import score_round
from app.main import app
from app.shared.models import GamePhase


@pytest.fixture(autouse=True)
def clean_store():
    """Reset the store between tests."""
    basta_store._rooms.clear()
    yield
    basta_store._rooms.clear()


@pytest.fixture
def client():
    return TestClient(app)


class TestBastaScoring:
    def test_unique_pair_and_group_duplicates(self):
        answers = {
            "p1": {"Animal": "Mono"},
            "p2": {"Animal": "Mono"},
            "p3": {"Animal": "Mariposa"},
            "p4": {"Animal": "Mono"},
        }

        result = score_round(answers, ["p1", "p2", "p3", "p4"], ["Animal"], "M")

        assert result.points == {"p1": 25, "p2": 25, "p3": 100, "p4": 25}
        assert result.category_results[0].points == {
            "p1": 25,
            "p2": 25,
            "p3": 100,
            "p4": 25,
        }

    def test_two_matching_answers_get_fifty_each(self):
        answers = {
            "p1": {"Color": "Morado"},
            "p2": {"Color": "Morado"},
            "p3": {"Color": "Marron"},
        }

        result = score_round(answers, ["p1", "p2", "p3"], ["Color"], "M")

        assert result.points == {"p1": 50, "p2": 50, "p3": 100}

    def test_blank_and_wrong_letter_score_zero(self):
        answers = {
            "p1": {"Comida": ""},
            "p2": {"Comida": "Pizza"},
            "p3": {"Comida": "Mango"},
        }

        result = score_round(answers, ["p1", "p2", "p3"], ["Comida"], "M")

        assert result.points == {"p1": 0, "p2": 0, "p3": 100}
        assert result.category_results[0].invalid_players == ["p1", "p2"]

    def test_scoring_is_case_and_accent_insensitive(self):
        answers = {
            "p1": {"Pais": "Mexico"},
            "p2": {"Pais": "mexico"},
            "p3": {"Pais": "Mexico  "},
        }

        result = score_round(answers, ["p1", "p2", "p3"], ["Pais"], "m")

        assert result.points == {"p1": 25, "p2": 25, "p3": 25}

    def test_vetoed_answers_score_zero(self):
        answers = {
            "p1": {"Animal": "Mono"},
            "p2": {"Animal": "Marmota"},
        }

        result = score_round(
            answers,
            ["p1", "p2"],
            ["Animal"],
            "M",
            {"Animal": {"p2"}},
        )

        assert result.points == {"p1": 100, "p2": 0}
        assert result.category_results[0].vetoed_players == ["p2"]


class TestBastaAPI:
    def _create_game(self, client: TestClient, n: int = 2):
        create_res = client.post("/api/ba/games", json={"host_name": "Host"})
        code = create_res.json()["code"]
        host_id = create_res.json()["host_id"]
        player_ids = []

        for name in ["Alice", "Bob", "Charlie", "Diana", "Eve"][:n]:
            res = client.post(f"/api/ba/games/{code}/join", json={"player_name": name})
            player_ids.append(res.json()["player_id"])

        return code, host_id, player_ids

    def test_start_game_uses_default_categories(self, client):
        code, host_id, _ = self._create_game(client)

        res = client.post(
            f"/api/ba/games/{code}/start",
            json={"rounds_to_play": 1, "round_seconds": 10, "host_paced": True},
            headers={"X-Player-Id": host_id},
        )

        assert res.status_code == 200
        info = client.get(f"/api/ba/games/{code}").json()
        assert info["phase"] == "playing"
        assert info["categories"] == DEFAULT_CATEGORIES
        assert info["rounds_to_play"] == 1
        assert info["round_seconds"] == 10

    def test_submit_answers(self, client):
        code, _, player_ids = self._create_game(client)
        room = basta_store.get_room(code)
        assert room is not None
        room.phase = GamePhase.PLAYING
        room.round_phase = "answering"
        room.categories = ["Animal", "Color"]
        room.current_letter = "M"
        room.round_seconds = 10
        room.scores = {pid: 0 for pid in player_ids}

        assert room.round_ends_at is None

        res = client.post(
            f"/api/ba/games/{code}/answers",
            json={"answers": {"Animal": "Mono", "Color": "Morado"}},
            headers={"X-Player-Id": player_ids[0]},
        )

        assert res.status_code == 200
        assert room.current_answers[player_ids[0]] == {
            "Animal": "Mono",
            "Color": "Morado",
        }
        assert room.round_ends_at is not None

    def test_rejects_incomplete_answers(self, client):
        code, _, player_ids = self._create_game(client)
        room = basta_store.get_room(code)
        assert room is not None
        room.phase = GamePhase.PLAYING
        room.round_phase = "answering"
        room.categories = ["Animal", "Color"]
        room.current_letter = "M"
        room.scores = {pid: 0 for pid in player_ids}

        res = client.post(
            f"/api/ba/games/{code}/answers",
            json={"answers": {"Animal": "Mono", "Color": ""}},
            headers={"X-Player-Id": player_ids[0]},
        )

        assert res.status_code == 400
        assert res.json()["detail"] == "Answer every category before calling Basta"
        assert player_ids[0] not in room.current_answers
        assert room.round_ends_at is None

    def test_auto_submit_accepts_partial_answers_after_basta_called(self, client):
        code, _, player_ids = self._create_game(client)
        room = basta_store.get_room(code)
        assert room is not None
        room.phase = GamePhase.PLAYING
        room.round_phase = "answering"
        room.categories = ["Animal", "Color"]
        room.current_letter = "M"
        room.round_ends_at = "2026-05-22T21:00:00+00:00"
        room.scores = {pid: 0 for pid in player_ids}

        res = client.post(
            f"/api/ba/games/{code}/answers",
            json={"answers": {"Animal": "Mono", "Color": ""}, "auto_submit": True},
            headers={"X-Player-Id": player_ids[0]},
        )

        assert res.status_code == 200
        assert room.current_answers[player_ids[0]] == {
            "Animal": "Mono",
            "Color": "",
        }

    def test_auto_submit_cannot_start_basta_timer(self, client):
        code, _, player_ids = self._create_game(client)
        room = basta_store.get_room(code)
        assert room is not None
        room.phase = GamePhase.PLAYING
        room.round_phase = "answering"
        room.categories = ["Animal", "Color"]
        room.current_letter = "M"
        room.scores = {pid: 0 for pid in player_ids}

        res = client.post(
            f"/api/ba/games/{code}/answers",
            json={"answers": {"Animal": "Mono", "Color": ""}, "auto_submit": True},
            headers={"X-Player-Id": player_ids[0]},
        )

        assert res.status_code == 400
        assert res.json()["detail"] == "Auto-submit is only available after Basta is called"
        assert player_ids[0] not in room.current_answers

    def test_save_draft_records_partial_answers(self, client):
        code, _, player_ids = self._create_game(client)
        room = basta_store.get_room(code)
        assert room is not None
        room.phase = GamePhase.PLAYING
        room.round_phase = "answering"
        room.categories = ["Animal", "Color"]
        room.current_letter = "M"

        res = client.post(
            f"/api/ba/games/{code}/draft",
            json={"answers": {"Animal": "Mono", "Color": "R"}},
            headers={"X-Player-Id": player_ids[0]},
        )

        assert res.status_code == 200
        assert room.current_drafts[player_ids[0]] == {
            "Animal": "Mono",
            "Color": "R",
        }

    def test_missing_submissions_are_filled_from_drafts(self, client):
        code, _, player_ids = self._create_game(client)
        room = basta_store.get_room(code)
        assert room is not None
        room.categories = ["Animal", "Color"]
        room.current_answers = {
            player_ids[0]: {"Animal": "Mono", "Color": "Morado"}
        }
        room.current_drafts = {
            player_ids[1]: {"Animal": "Marmota", "Color": "Marron"}
        }

        _flush_missing_drafts(room)

        assert room.current_answers[player_ids[0]] == {
            "Animal": "Mono",
            "Color": "Morado",
        }
        assert room.current_answers[player_ids[1]] == {
            "Animal": "Marmota",
            "Color": "Marron",
        }

    def test_rejects_answers_that_do_not_start_with_round_letter(self, client):
        code, _, player_ids = self._create_game(client)
        room = basta_store.get_room(code)
        assert room is not None
        room.phase = GamePhase.PLAYING
        room.round_phase = "answering"
        room.categories = ["Animal", "Color"]
        room.current_letter = "M"
        room.scores = {pid: 0 for pid in player_ids}

        res = client.post(
            f"/api/ba/games/{code}/answers",
            json={"answers": {"Animal": "Mono", "Color": "Rojo"}},
            headers={"X-Player-Id": player_ids[0]},
        )

        assert res.status_code == 400
        assert res.json()["detail"] == "Every answer must start with M"
        assert player_ids[0] not in room.current_answers
        assert room.round_ends_at is None

    def test_player_can_veto_another_players_answer(self, client):
        code, _, player_ids = self._create_game(client)
        room = basta_store.get_room(code)
        assert room is not None
        room.phase = GamePhase.PLAYING
        room.round_phase = "review"
        room.categories = ["Animal"]
        room.current_letter = "M"
        room.review_category_index = 0
        room.current_answers = {
            player_ids[0]: {"Animal": "Mono"},
            player_ids[1]: {"Animal": "Marmota"},
        }

        res = client.post(
            f"/api/ba/games/{code}/veto",
            json={"category": "Animal", "target_player_id": player_ids[0]},
            headers={"X-Player-Id": player_ids[1]},
        )

        assert res.status_code == 200
        assert res.json()["veto_count"] == 1
        assert room.current_vetoes["Animal"][player_ids[0]] == {player_ids[1]}

    def test_two_vetoes_are_required_to_invalidate_answer(self, client):
        code, _, player_ids = self._create_game(client, n=3)
        room = basta_store.get_room(code)
        assert room is not None
        room.categories = ["Animal"]
        room.current_answers = {
            player_ids[0]: {"Animal": "Mono"},
            player_ids[1]: {"Animal": "Marmota"},
            player_ids[2]: {"Animal": "Mapache"},
        }
        room.current_vetoes = {"Animal": {player_ids[0]: {player_ids[1]}}}

        assert _vetoed_answers(room) == {}

        room.current_vetoes = {
            "Animal": {player_ids[0]: {player_ids[1], player_ids[2]}}
        }

        assert _vetoed_answers(room) == {"Animal": {player_ids[0]}}

    def test_vetoed_word_invalidates_every_matching_answer(self, client):
        code, _, player_ids = self._create_game(client, n=4)
        room = basta_store.get_room(code)
        assert room is not None
        room.categories = ["Animal"]
        room.current_answers = {
            player_ids[0]: {"Animal": "Mono"},
            player_ids[1]: {"Animal": "mono"},
            player_ids[2]: {"Animal": "Marmota"},
            player_ids[3]: {"Animal": "Mapache"},
        }
        room.current_vetoes = {
            "Animal": {
                player_ids[0]: {player_ids[2]},
                player_ids[1]: {player_ids[3]},
            }
        }

        vetoed = _vetoed_answers(room)
        assert vetoed == {"Animal": {player_ids[0], player_ids[1]}}

        result = score_round(
            room.current_answers,
            player_ids,
            room.categories,
            "M",
            vetoed,
        )

        assert result.points[player_ids[0]] == 0
        assert result.points[player_ids[1]] == 0
        assert result.points[player_ids[2]] == 100
        assert result.points[player_ids[3]] == 100

    def test_host_can_advance_manual_review_category(self, client):
        code, host_id, _ = self._create_game(client)
        room = basta_store.get_room(code)
        assert room is not None
        room.phase = GamePhase.PLAYING
        room.round_phase = "review"
        room.host_paced = True
        room.review_advance = asyncio.Event()

        res = client.post(
            f"/api/ba/games/{code}/next",
            headers={"X-Player-Id": host_id},
        )

        assert res.status_code == 200
        assert room.review_advance.is_set()
