"""Tests for the funny questions game."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.funny_questions.game_state import store as fq_store
from app.funny_questions.scoring import score_round


@pytest.fixture(autouse=True)
def clean_store():
    """Reset the store between tests."""
    fq_store._rooms.clear()
    yield
    fq_store._rooms.clear()


@pytest.fixture
def client():
    return TestClient(app)


class TestScoring:
    """Tests for the pure score_round function."""

    def test_majority_vote_bonus(self):
        """Players who vote for the majority pick get +1."""
        votes = {"p1": "p3", "p2": "p3", "p3": "p1"}
        result = score_round(votes, ["p1", "p2", "p3"], None)
        # p3 got the most votes (2)
        assert result.most_voted == "p3"
        # p1 and p2 voted for majority → +1 each
        assert result.points["p1"] == 1
        assert result.points["p2"] == 1
        # p3 got most votes but didn't self-vote → -2
        # p3 voted for p1 (not majority) → no +1
        assert result.points["p3"] == -2

    def test_self_vote_with_most_votes(self):
        """Self-voting and getting most votes gives +2."""
        votes = {"p1": "p2", "p2": "p2", "p3": "p2"}
        result = score_round(votes, ["p1", "p2", "p3"], None)
        assert result.most_voted == "p2"
        # p2 self-voted and got most votes: +1 (majority) + 2 (self+most) = 3
        assert result.points["p2"] == 3
        # p1 and p3 voted for majority
        assert result.points["p1"] == 1
        assert result.points["p3"] == 1

    def test_most_voted_no_self_vote_penalty(self):
        """Getting most votes without self-voting gives -2."""
        votes = {"p1": "p3", "p2": "p3", "p3": "p1"}
        result = score_round(votes, ["p1", "p2", "p3"], None)
        assert result.most_voted == "p3"
        # p3 didn't self-vote, got most votes → -2
        assert result.points["p3"] == -2

    def test_no_vote_penalty(self):
        """Not voting gives -1."""
        votes = {"p1": "p2"}  # only p1 voted
        result = score_round(votes, ["p1", "p2", "p3"], None)
        # p2 didn't vote (-1) AND got most votes without self-voting (-2) = -3
        assert result.points["p2"] == -3
        assert result.points["p3"] == -1

    def test_tie_no_majority(self):
        """Tied votes means no majority and no most_voted bonus/penalty."""
        votes = {"p1": "p2", "p2": "p1", "p3": "p3"}
        result = score_round(votes, ["p1", "p2", "p3"], None)
        # All have 1 vote → tie → no majority
        assert result.most_voted is None
        # No majority bonus for anyone, no most_voted penalty
        assert result.points["p1"] == 0
        assert result.points["p2"] == 0
        assert result.points["p3"] == 0

    def test_shame_earned(self):
        """Self-voting with no other votes earns shame."""
        votes = {"p1": "p1", "p2": "p3", "p3": "p2"}
        result = score_round(votes, ["p1", "p2", "p3"], None)
        # p1 self-voted, nobody else voted for p1 → shame
        assert result.new_shame == "p1"

    def test_shame_not_earned_when_others_also_vote(self):
        """Self-voting doesn't earn shame if others also vote for you."""
        votes = {"p1": "p1", "p2": "p1", "p3": "p2"}
        result = score_round(votes, ["p1", "p2", "p3"], None)
        # p1 self-voted but p2 also voted for p1 → no shame
        assert result.new_shame is None

    def test_shame_clears_on_new_shame_holder(self):
        """Existing shame clears when someone else earns shame."""
        votes = {"p1": "p2", "p2": "p2", "p3": "p3"}
        result = score_round(votes, ["p1", "p2", "p3"], current_shame_holder="p1")
        # p3 self-voted alone → new shame
        assert result.new_shame == "p3"
        # p1's shame clears because someone else earned it
        assert result.shame_cleared is True

    def test_shame_clears_on_self_vote_with_support(self):
        """Shame clears when shame holder self-votes and someone else also votes for them."""
        votes = {"p1": "p1", "p2": "p1", "p3": "p2"}
        result = score_round(votes, ["p1", "p2", "p3"], current_shame_holder="p1")
        # p1 self-voted, p2 also voted for p1 → shame clears
        assert result.shame_cleared is True

    def test_shame_blocks_positive_points(self):
        """Shamed player can't earn positive points."""
        votes = {"p1": "p2", "p2": "p2", "p3": "p2"}
        result = score_round(votes, ["p1", "p2", "p3"], current_shame_holder="p2")
        # p2 would normally get +1 (majority) + 2 (self+most) = 3
        # But p2 has shame → clamped to 0
        # Wait: shame_cleared check - p2 self-voted and got others votes → shame clears
        # Actually let's check: p2 self-voted, p1 and p3 also voted for p2 → shame clears
        assert result.shame_cleared is True
        # Since shame cleared, p2 gets full points
        assert result.points["p2"] == 3

    def test_shame_blocks_when_not_cleared(self):
        """Shamed player's positive points blocked when shame not cleared."""
        # p1 has shame, votes for p2 (doesn't self-vote) so shame doesn't clear
        votes = {"p1": "p2", "p2": "p2", "p3": "p2"}
        result = score_round(votes, ["p1", "p2", "p3"], current_shame_holder="p1")
        # p1 voted for majority → would get +1, but shamed → clamped to 0
        assert result.points["p1"] == 0

    def test_empty_votes(self):
        """All players miss the vote."""
        result = score_round({}, ["p1", "p2", "p3"], None)
        assert result.points == {"p1": -1, "p2": -1, "p3": -1}
        assert result.most_voted is None


class TestFQAPI:
    """Tests for the funny questions API endpoints."""

    def _create_fq_game(self, client, n=3):
        """Create a FQ game with n players."""
        create_res = client.post("/api/fq/games", json={"host_name": "Host"})
        code = create_res.json()["code"]
        host_id = create_res.json()["host_id"]
        player_ids = []

        names = ["Alice", "Bob", "Charlie", "Diana", "Eve"]
        for i in range(n):
            res = client.post(
                f"/api/fq/games/{code}/join", json={"player_name": names[i]}
            )
            player_ids.append(res.json()["player_id"])

        return code, host_id, player_ids

    def test_create_and_join(self, client):
        code, host_id, player_ids = self._create_fq_game(client)
        assert len(code) == 4
        assert len(player_ids) == 3

        info = client.get(f"/api/fq/games/{code}").json()
        assert info["phase"] == "lobby"
        assert len(info["players"]) == 3

    def test_start_game(self, client):
        code, host_id, player_ids = self._create_fq_game(client)

        res = client.post(
            f"/api/fq/games/{code}/start",
            json={"max_spice": 1, "points_to_win": 5},
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 200

        info = client.get(f"/api/fq/games/{code}").json()
        assert info["phase"] == "playing"
        assert info["points_to_win"] == 5

    def test_non_host_cannot_start(self, client):
        code, host_id, player_ids = self._create_fq_game(client)

        res = client.post(
            f"/api/fq/games/{code}/start",
            headers={"X-Player-Id": player_ids[0]},
        )
        assert res.status_code == 403

    def test_vote(self, client):
        code, host_id, player_ids = self._create_fq_game(client)

        client.post(
            f"/api/fq/games/{code}/start",
            json={"max_spice": 1, "points_to_win": 20},
            headers={"X-Player-Id": host_id},
        )

        # Wait a moment for game loop to start
        import time
        time.sleep(0.2)

        # Vote
        res = client.post(
            f"/api/fq/games/{code}/vote",
            json={"voted_for": player_ids[1]},
            headers={"X-Player-Id": player_ids[0]},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "voted"

    def test_double_vote_rejected(self, client):
        code, host_id, player_ids = self._create_fq_game(client)

        client.post(
            f"/api/fq/games/{code}/start",
            json={"max_spice": 1, "points_to_win": 20},
            headers={"X-Player-Id": host_id},
        )

        import time
        time.sleep(0.2)

        client.post(
            f"/api/fq/games/{code}/vote",
            json={"voted_for": player_ids[1]},
            headers={"X-Player-Id": player_ids[0]},
        )
        res = client.post(
            f"/api/fq/games/{code}/vote",
            json={"voted_for": player_ids[2]},
            headers={"X-Player-Id": player_ids[0]},
        )
        assert res.status_code == 400

    def test_host_cannot_vote(self, client):
        code, host_id, player_ids = self._create_fq_game(client)

        client.post(
            f"/api/fq/games/{code}/start",
            json={"max_spice": 1, "points_to_win": 20},
            headers={"X-Player-Id": host_id},
        )

        import time
        time.sleep(0.2)

        res = client.post(
            f"/api/fq/games/{code}/vote",
            json={"voted_for": player_ids[0]},
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 403

    def test_get_scores(self, client):
        code, host_id, player_ids = self._create_fq_game(client)

        client.post(
            f"/api/fq/games/{code}/start",
            json={"max_spice": 1, "points_to_win": 20},
            headers={"X-Player-Id": host_id},
        )

        res = client.get(f"/api/fq/games/{code}/scores")
        assert res.status_code == 200
        scores = res.json()
        assert len(scores) == 3
        assert all(s["score"] == 0 for s in scores)

    def test_not_enough_players(self, client):
        create_res = client.post("/api/fq/games", json={"host_name": "Host"})
        code = create_res.json()["code"]
        host_id = create_res.json()["host_id"]

        # Only 2 players (need 3)
        client.post(f"/api/fq/games/{code}/join", json={"player_name": "Alice"})
        client.post(f"/api/fq/games/{code}/join", json={"player_name": "Bob"})

        res = client.post(
            f"/api/fq/games/{code}/start",
            headers={"X-Player-Id": host_id},
        )
        assert res.status_code == 400
