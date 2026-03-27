"""Tests for the API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.murder_mystery.game_state import store


@pytest.fixture(autouse=True)
def clean_store():
    """Reset the store between tests."""
    store._rooms.clear()
    yield
    store._rooms.clear()


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthCheck:
    def test_health(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}


class TestLobby:
    def test_create_game(self, client):
        res = client.post("/api/mm/games", json={"host_name": "Alice"})
        assert res.status_code == 200
        data = res.json()
        assert "code" in data
        assert "host_id" in data
        assert len(data["code"]) == 4

    def test_join_game(self, client):
        create_res = client.post("/api/mm/games", json={"host_name": "Alice"})
        code = create_res.json()["code"]

        res = client.post(f"/api/mm/games/{code}/join", json={"player_name": "Bob"})
        assert res.status_code == 200
        assert "player_id" in res.json()

    def test_join_nonexistent_game(self, client):
        res = client.post("/api/mm/games/ZZZZ/join", json={"player_name": "Bob"})
        assert res.status_code == 404

    def test_join_duplicate_name(self, client):
        create_res = client.post("/api/mm/games", json={"host_name": "Alice"})
        code = create_res.json()["code"]
        # Join with same name as another player
        client.post(f"/api/mm/games/{code}/join", json={"player_name": "Bob"})
        res = client.post(f"/api/mm/games/{code}/join", json={"player_name": "Bob"})
        assert res.status_code == 400

    def test_join_duplicate_host_name(self, client):
        create_res = client.post("/api/mm/games", json={"host_name": "Alice"})
        code = create_res.json()["code"]
        res = client.post(f"/api/mm/games/{code}/join", json={"player_name": "Alice"})
        assert res.status_code == 400

    def test_get_game_info(self, client):
        create_res = client.post("/api/mm/games", json={"host_name": "Alice"})
        code = create_res.json()["code"]
        client.post(f"/api/mm/games/{code}/join", json={"player_name": "Bob"})

        res = client.get(f"/api/mm/games/{code}")
        assert res.status_code == 200
        data = res.json()
        assert data["code"] == code
        assert data["phase"] == "lobby"
        assert data["host_name"] == "Alice"
        # Players list does not include the host
        assert len(data["players"]) == 1
        assert data["players"][0]["name"] == "Bob"
        # No is_host field
        assert "is_host" not in data["players"][0]


class TestGameFlow:
    def _create_full_game(self, client, n=4):
        """Helper to create a game with n players (host is separate)."""
        create_res = client.post("/api/mm/games", json={"host_name": "Host"})
        code = create_res.json()["code"]
        host_id = create_res.json()["host_id"]
        player_ids = []

        names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        for i in range(n):
            res = client.post(
                f"/api/mm/games/{code}/join", json={"player_name": names[i]}
            )
            player_ids.append(res.json()["player_id"])

        return code, host_id, player_ids

    def _start_game(self, client, code, host_id):
        """Helper to start game with default round durations."""
        return client.post(
            f"/api/mm/games/{code}/start",
            json={"difficulty": "medium", "round_minutes": 5},
            headers={"X-Player-Id": host_id},
        )

    def _begin_game(self, client, code, host_id):
        """Helper to begin game (starts round 1)."""
        return client.post(
            f"/api/mm/games/{code}/begin",
            headers={"X-Player-Id": host_id},
        )

    def _advance_round(self, client, code, host_id):
        """Helper to advance to next round."""
        return client.post(
            f"/api/mm/games/{code}/advance",
            headers={"X-Player-Id": host_id},
        )

    def test_start_game(self, client):
        code, host_id, player_ids = self._create_full_game(client)

        res = self._start_game(client, code, host_id)
        assert res.status_code == 200

        # Verify game is now in playing phase but rounds not yet started
        info = client.get(f"/api/mm/games/{code}").json()
        assert info["phase"] == "playing"
        assert info["current_round"] == 0
        assert info["round_durations"] == [300, 300, 300]
        assert info["started_at"] is None

        # Begin the game (starts round 1)
        res = self._begin_game(client, code, host_id)
        assert res.status_code == 200

        info = client.get(f"/api/mm/games/{code}").json()
        assert info["current_round"] == 1
        assert info["round_started_at"] is not None
        assert info["started_at"] is not None

    def test_non_host_cannot_start(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        non_host_id = player_ids[0]

        res = client.post(
            f"/api/mm/games/{code}/start",
            headers={"X-Player-Id": non_host_id},
        )
        assert res.status_code == 403

    def test_get_card(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)

        for pid in player_ids:
            res = client.get(
                f"/api/mm/games/{code}/card",
                headers={"X-Player-Id": pid},
            )
            assert res.status_code == 200
            data = res.json()
            assert "character_name" in data
            assert "clues" in data
            assert len(data["clues"]) > 0
            # Each clue should have a round field
            for clue in data["clues"]:
                assert "round" in clue

    def test_card_returns_round_filtered_clues(self, client):
        """Card in round 1 returns only round-1 clues; after advance, more appear."""
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)
        self._begin_game(client, code, host_id)

        # Round 1: only round 1 clues
        res = client.get(
            f"/api/mm/games/{code}/card",
            headers={"X-Player-Id": player_ids[0]},
        )
        round1_clues = res.json()["clues"]
        assert all(c["round"] == 1 for c in round1_clues)
        round1_count = len(round1_clues)

        # Advance to round 2
        self._advance_round(client, code, host_id)

        res = client.get(
            f"/api/mm/games/{code}/card",
            headers={"X-Player-Id": player_ids[0]},
        )
        round2_clues = res.json()["clues"]
        assert len(round2_clues) >= round1_count
        assert all(c["round"] in (1, 2) for c in round2_clues)

    def test_host_cannot_get_card(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)

        res = client.get(
            f"/api/mm/games/{code}/card",
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 403

    def test_host_cannot_guess(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)
        self._begin_game(client, code, host_id)
        self._advance_round(client, code, host_id)  # round 2

        res = client.post(
            f"/api/mm/games/{code}/guess",
            json={"suspect_name": "Nobody"},
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 403

    def test_guess_blocked_in_round_1(self, client):
        """Guessing should be blocked during round 1."""
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)
        self._begin_game(client, code, host_id)

        # Still in round 1
        res = client.post(
            f"/api/mm/games/{code}/guess",
            json={"suspect_name": "Nobody"},
            headers={"X-Player-Id": player_ids[0]},
        )
        assert res.status_code == 400
        assert "Round 2" in res.json()["detail"]

    def test_guess_allowed_in_round_2(self, client):
        """Guessing should work after advancing to round 2."""
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)
        self._begin_game(client, code, host_id)
        self._advance_round(client, code, host_id)  # round 2

        room = store.get_room(code)
        murderer = room.murderer_name

        res = client.post(
            f"/api/mm/games/{code}/guess",
            json={"suspect_name": murderer},
            headers={"X-Player-Id": player_ids[0]},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "locked_in"
        assert "guessed_at" in data

    def test_advance_round(self, client):
        """Host can advance from round 1 to 2."""
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)
        self._begin_game(client, code, host_id)

        room = store.get_room(code)
        assert room.current_round == 1

        res = self._advance_round(client, code, host_id)
        assert res.status_code == 200
        assert res.json()["round"] == 2
        assert room.current_round == 2

    def test_advance_round_3_finishes_game(self, client):
        """Advancing from round 3 should finish the game."""
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)
        self._begin_game(client, code, host_id)
        self._advance_round(client, code, host_id)  # round 2
        self._advance_round(client, code, host_id)  # round 3

        res = self._advance_round(client, code, host_id)  # end game
        assert res.status_code == 200
        assert res.json()["status"] == "finished"

        info = client.get(f"/api/mm/games/{code}").json()
        assert info["phase"] == "finished"

    def test_non_host_cannot_advance(self, client):
        """Non-host player cannot advance rounds."""
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)
        self._begin_game(client, code, host_id)

        res = client.post(
            f"/api/mm/games/{code}/advance",
            headers={"X-Player-Id": player_ids[0]},
        )
        assert res.status_code == 403

    def test_all_guesses_ends_game(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)
        self._begin_game(client, code, host_id)
        self._advance_round(client, code, host_id)  # round 2

        for pid in player_ids:
            client.post(
                f"/api/mm/games/{code}/guess",
                json={"suspect_name": "Nobody"},
                headers={"X-Player-Id": pid},
            )

        # Game should be finished
        info = client.get(f"/api/mm/games/{code}").json()
        assert info["phase"] == "finished"

    def test_end_game_by_host(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)

        res = client.post(
            f"/api/mm/games/{code}/end",
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 200

        info = client.get(f"/api/mm/games/{code}").json()
        assert info["phase"] == "finished"

    def test_non_host_cannot_end_game(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)

        res = client.post(
            f"/api/mm/games/{code}/end",
            headers={"X-Player-Id": player_ids[0]},
        )
        assert res.status_code == 403

    def test_get_results_after_finish(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)
        self._begin_game(client, code, host_id)
        self._advance_round(client, code, host_id)  # round 2

        for pid in player_ids:
            client.post(
                f"/api/mm/games/{code}/guess",
                json={"suspect_name": "Nobody"},
                headers={"X-Player-Id": pid},
            )

        res = client.get(f"/api/mm/games/{code}/results")
        assert res.status_code == 200
        data = res.json()
        assert "murderer_name" in data
        assert "murder_weapon" in data
        assert "leaderboard" in data
        assert "murder_clues" in data
        assert len(data["leaderboard"]) == len(player_ids)

    def test_results_not_available_before_finish(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        self._start_game(client, code, host_id)

        res = client.get(f"/api/mm/games/{code}/results")
        assert res.status_code == 400
