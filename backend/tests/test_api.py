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
        assert "player_id" in data
        assert len(data["code"]) == 4

    def test_join_game(self, client):
        # Create first
        create_res = client.post("/api/games", json={"host_name": "Alice"})
        code = create_res.json()["code"]

        # Join
        res = client.post(f"/api/games/{code}/join", json={"player_name": "Bob"})
        assert res.status_code == 200
        assert "player_id" in res.json()

    def test_join_nonexistent_game(self, client):
        res = client.post("/api/games/ZZZZ/join", json={"player_name": "Bob"})
        assert res.status_code == 404

    def test_join_duplicate_name(self, client):
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
        assert len(data["players"]) == 2


class TestGameFlow:
    def _create_full_game(self, client, n=4):
        """Helper to create a game with n players."""
        create_res = client.post("/api/games", json={"host_name": "Alice"})
        code = create_res.json()["code"]
        host_id = create_res.json()["player_id"]
        player_ids = [host_id]

        names = ["Bob", "Charlie", "Diana", "Eve", "Frank"]
        for i in range(n - 1):
            res = client.post(
                f"/api/games/{code}/join", json={"player_name": names[i]}
            )
            player_ids.append(res.json()["player_id"])

        return code, host_id, player_ids

    def test_start_game(self, client):
        code, host_id, player_ids = self._create_full_game(client)

        res = client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium"},
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 200

        # Verify game is now in playing phase
        info = client.get(f"/api/games/{code}").json()
        assert info["phase"] == "playing"

    def test_non_host_cannot_start(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        non_host_id = player_ids[1]

        res = client.post(
            f"/api/games/{code}/start",
            headers={"X-Player-Id": non_host_id},
        )
        assert res.status_code == 403

    def test_get_card(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium"},
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

    def test_guess_flow(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium"},
            headers={"X-Player-Id": host_id},
        )

        # Get the actual murderer from the room
        room = store.get_room(code)
        murderer = room.murderer_name

        # First player guesses correctly
        res = client.post(
            f"/api/games/{code}/guess",
            json={"suspect_name": murderer},
            headers={"X-Player-Id": player_ids[0]},
        )
        assert res.status_code == 200
        assert res.json()["correct"] is True

    def test_all_guesses_ends_game(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium"},
            headers={"X-Player-Id": host_id},
        )

        # All players guess
        for pid in player_ids:
            client.post(
                f"/api/games/{code}/guess",
                json={"suspect_name": "Nobody"},
                headers={"X-Player-Id": pid},
            )

        # Game should be finished
        info = client.get(f"/api/games/{code}").json()
        assert info["phase"] == "finished"

    def test_get_solution_after_finish(self, client):
        code, host_id, player_ids = self._create_full_game(client)
        client.post(
            f"/api/games/{code}/start",
            json={"difficulty": "medium"},
            headers={"X-Player-Id": host_id},
        )

        for pid in player_ids:
            client.post(
                f"/api/games/{code}/guess",
                json={"suspect_name": "Nobody"},
                headers={"X-Player-Id": pid},
            )

        res = client.get(f"/api/games/{code}/solution")
        assert res.status_code == 200
        data = res.json()
        assert "murderer_name" in data
        assert "solution" in data
        assert "murder_clues" in data
