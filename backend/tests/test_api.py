"""Tests for the API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.game_state import store


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
        res = client.post("/api/games", json={"host_name": "Alice"})
        assert res.status_code == 200
        data = res.json()
        assert "code" in data
        assert "host_id" in data
        assert len(data["code"]) == 4

    def test_join_game(self, client):
        create_res = client.post("/api/games", json={"host_name": "Alice"})
        code = create_res.json()["code"]

        res = client.post(f"/api/games/{code}/join", json={"player_name": "Bob"})
        assert res.status_code == 200
        assert "player_id" in res.json()

    def test_join_nonexistent_game(self, client):
        res = client.post("/api/games/ZZZZ/join", json={"player_name": "Bob"})
        assert res.status_code == 404

    def test_join_duplicate_name(self, client):
        create_res = client.post("/api/games", json={"host_name": "Alice"})
        code = create_res.json()["code"]
        # Join with same name as another player
        client.post(f"/api/games/{code}/join", json={"player_name": "Bob"})
        res = client.post(f"/api/games/{code}/join", json={"player_name": "Bob"})
        assert res.status_code == 400

    def test_join_duplicate_host_name(self, client):
        create_res = client.post("/api/games", json={"host_name": "Alice"})
        code = create_res.json()["code"]
        res = client.post(f"/api/games/{code}/join", json={"player_name": "Alice"})
        assert res.status_code == 400

    def test_get_game_info(self, client):
        create_res = client.post("/api/games", json={"host_name": "Alice"})
        code = create_res.json()["code"]
        client.post(f"/api/games/{code}/join", json={"player_name": "Bob"})

        res = client.get(f"/api/games/{code}")
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
        create_res = client.post("/api/games", json={"host_name": "Host"})
        code = create_res.json()["code"]
        host_id = create_res.json()["host_id"]
        player_ids = []

        names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
        for i in range(n):
            res = client.post(
                f"/api/games/{code}/join", json={"player_name": names[i]}
            )
            player_ids.append(res.json()["player_id"])

        return code, host_id, player_ids

    def test_start_game(self, client):
        code, host_id, player_ids = self._create_full_game(client)

        res = client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium", "timer_minutes": 10},
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 200

        # Verify game is now in playing phase but timer not yet started
        info = client.get(f"/api/games/{code}").json()
        assert info["phase"] == "playing"
        assert info["started_at"] is None

        # Begin the timer
        res = client.post(
            f"/api/games/{code}/begin",
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 200

        info = client.get(f"/api/games/{code}").json()
        assert info["timer_duration_seconds"] == 600
        assert info["started_at"] is not None

    def test_non_host_cannot_start(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        non_host_id = player_ids[0]

        res = client.post(
            f"/api/games/{code}/start",
            headers={"X-Player-Id": non_host_id},
        )
        assert res.status_code == 403

    def test_get_card(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium", "timer_minutes": 10},
            headers={"X-Player-Id": host_id},
        )

        for pid in player_ids:
            res = client.get(
                f"/api/games/{code}/card",
                headers={"X-Player-Id": pid},
            )
            assert res.status_code == 200
            data = res.json()
            assert "character_name" in data
            assert "clues" in data
            assert len(data["clues"]) > 0

    def test_host_cannot_get_card(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium", "timer_minutes": 10},
            headers={"X-Player-Id": host_id},
        )

        res = client.get(
            f"/api/games/{code}/card",
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 403

    def test_host_cannot_guess(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium", "timer_minutes": 10},
            headers={"X-Player-Id": host_id},
        )

        res = client.post(
            f"/api/games/{code}/guess",
            json={"suspect_name": "Nobody"},
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 403

    def test_guess_deferred(self, client):
        """Guess returns locked_in status, not correctness."""
        code, host_id, player_ids = self._create_full_game(client)
        client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium", "timer_minutes": 10},
            headers={"X-Player-Id": host_id},
        )

        room = store.get_room(code)
        murderer = room.murderer_name

        res = client.post(
            f"/api/games/{code}/guess",
            json={"suspect_name": murderer},
            headers={"X-Player-Id": player_ids[0]},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "locked_in"
        assert "guessed_at" in data
        # No correct/actual_murderer fields
        assert "correct" not in data
        assert "actual_murderer" not in data

    def test_all_guesses_ends_game(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium", "timer_minutes": 10},
            headers={"X-Player-Id": host_id},
        )

        for pid in player_ids:
            client.post(
                f"/api/games/{code}/guess",
                json={"suspect_name": "Nobody"},
                headers={"X-Player-Id": pid},
            )

        # Game should be finished
        info = client.get(f"/api/games/{code}").json()
        assert info["phase"] == "finished"

    def test_end_game_by_host(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium", "timer_minutes": 10},
            headers={"X-Player-Id": host_id},
        )

        res = client.post(
            f"/api/games/{code}/end",
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 200

        info = client.get(f"/api/games/{code}").json()
        assert info["phase"] == "finished"

    def test_non_host_cannot_end_game(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium", "timer_minutes": 10},
            headers={"X-Player-Id": host_id},
        )

        res = client.post(
            f"/api/games/{code}/end",
            headers={"X-Player-Id": player_ids[0]},
        )
        assert res.status_code == 403

    def test_get_results_after_finish(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium", "timer_minutes": 10},
            headers={"X-Player-Id": host_id},
        )

        for pid in player_ids:
            client.post(
                f"/api/games/{code}/guess",
                json={"suspect_name": "Nobody"},
                headers={"X-Player-Id": pid},
            )

        res = client.get(f"/api/games/{code}/results")
        assert res.status_code == 200
        data = res.json()
        assert "murderer_name" in data
        assert "murder_weapon" in data
        assert "leaderboard" in data
        assert "murder_clues" in data
        assert len(data["leaderboard"]) == len(player_ids)

    def test_results_not_available_before_finish(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium", "timer_minutes": 10},
            headers={"X-Player-Id": host_id},
        )

        res = client.get(f"/api/games/{code}/results")
        assert res.status_code == 400
