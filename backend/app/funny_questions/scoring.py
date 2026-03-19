"""Pure scoring function for funny questions rounds."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RoundResult:
    """Result of scoring a single round."""
    # {player_id: points_delta}
    points: dict[str, int]
    # player_id who got the most votes (None if tie)
    most_voted: str | None
    # {player_id: list of voter ids}
    vote_breakdown: dict[str, list[str]]
    # player_id who earns shame this round (None if nobody)
    new_shame: str | None
    # Whether existing shame is cleared
    shame_cleared: bool


def score_round(
    votes: dict[str, str],
    player_ids: list[str],
    current_shame_holder: str | None,
) -> RoundResult:
    """Score a round of funny questions.

    Args:
        votes: {voter_id: voted_for_id} — only players who voted in time.
        player_ids: list of all player ids (excludes host).
        current_shame_holder: player_id currently holding the mark of shame (or None).

    Returns:
        RoundResult with point deltas, vote breakdown, and shame updates.

    Scoring rules:
        +1 if you voted for the majority pick
        +2 if you got most votes AND voted for yourself
        -2 if you got most votes but DIDN'T vote for yourself
        -1 if you didn't vote in time
        Mark of Shame: self-vote but nobody else votes for you → shame
        While shamed, you can't earn points (deltas clamped to <= 0)
        Shame clears when: (a) self-vote and someone else also votes, or (b) someone else earns shame
    """
    points: dict[str, int] = {pid: 0 for pid in player_ids}

    # Build vote breakdown: {target_id: [voter_ids]}
    vote_breakdown: dict[str, list[str]] = {pid: [] for pid in player_ids}
    for voter, target in votes.items():
        if target in vote_breakdown:
            vote_breakdown[target].append(voter)

    # Find the majority pick (most votes received)
    max_votes = 0
    most_voted: str | None = None
    tied = False
    for target, voters in vote_breakdown.items():
        if len(voters) > max_votes:
            max_votes = len(voters)
            most_voted = target
            tied = False
        elif len(voters) == max_votes and max_votes > 0:
            tied = True

    if tied or max_votes == 0:
        most_voted = None

    # Determine majority target for +1 bonus
    majority_target = most_voted

    # Score each player
    for pid in player_ids:
        if pid not in votes:
            # Didn't vote in time: -1
            points[pid] = -1
            continue

        delta = 0
        voted_for = votes[pid]

        # +1 if voted for majority pick
        if majority_target and voted_for == majority_target:
            delta += 1

        points[pid] = delta

    # Most-voted bonus/penalty
    if most_voted is not None:
        if most_voted in votes and votes[most_voted] == most_voted:
            # Voted for themselves AND got most votes: +2
            points[most_voted] += 2
        else:
            # Got most votes but didn't vote for themselves: -2
            points[most_voted] -= 2

    # Mark of Shame logic
    new_shame: str | None = None
    shame_cleared = False

    for pid in player_ids:
        if pid in votes and votes[pid] == pid:
            # Self-voted
            other_voters = [v for v in vote_breakdown[pid] if v != pid]
            if len(other_voters) == 0 and len(vote_breakdown[pid]) == 1:
                # Only voter for themselves — shame candidate
                new_shame = pid

    # Check if current shame holder's shame clears
    if current_shame_holder is not None:
        if current_shame_holder in votes and votes[current_shame_holder] == current_shame_holder:
            other_voters = [v for v in vote_breakdown[current_shame_holder] if v != current_shame_holder]
            if len(other_voters) > 0:
                # Self-voted and someone else also voted for them
                shame_cleared = True

        if new_shame is not None and new_shame != current_shame_holder:
            # Someone else earned shame — clears existing
            shame_cleared = True

    # Apply shame: shamed player can't earn positive points
    effective_shame_holder = current_shame_holder
    if shame_cleared:
        effective_shame_holder = None

    if effective_shame_holder is not None and effective_shame_holder in points:
        if points[effective_shame_holder] > 0:
            points[effective_shame_holder] = 0

    return RoundResult(
        points=points,
        most_voted=most_voted,
        vote_breakdown=vote_breakdown,
        new_shame=new_shame,
        shame_cleared=shame_cleared,
    )
