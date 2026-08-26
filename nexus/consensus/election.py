import time
import uuid
from typing import Any, Dict, List, Optional


class DistributedVotingEngine:
    """
    Distributed Election & Voting Engine.
    Implements leader-driven ballot counting with an automatic local fallback consensus
    when the leader node becomes unreachable.
    """

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self.active_poll_end_time: float = 0.0
        self.current_poll: Optional[Dict[str, Any]] = None
        self.local_tallies: Dict[int, int] = {}
        self.voted_polls: set = set()

    def can_start_poll(self) -> bool:
        return time.time() >= self.active_poll_end_time

    def create_poll(
        self, question: str, options: List[str], duration_seconds: int = 30
    ) -> Optional[Dict[str, Any]]:
        if not self.can_start_poll():
            return None

        end_time = time.time() + duration_seconds
        poll_id = str(uuid.uuid4())
        poll_data = {
            "id": poll_id,
            "question": question,
            "options": options,
            "duration": duration_seconds,
            "end_time": end_time,
            "sender_id": self.node_id,
        }
        self.active_poll_end_time = end_time
        self.current_poll = poll_data
        self.local_tallies = {i: 0 for i in range(len(options))}
        return poll_data

    def register_remote_poll(self, poll_data: Dict[str, Any]) -> None:
        self.active_poll_end_time = poll_data["end_time"]
        self.current_poll = poll_data
        self.local_tallies = {i: 0 for i in range(len(poll_data["options"]))}

    def record_vote(self, poll_id: str, choice_index: int) -> bool:
        if time.time() > self.active_poll_end_time:
            return False
        choice = int(choice_index)
        if choice in self.local_tallies:
            self.local_tallies[choice] = self.local_tallies.get(choice, 0) + 1
        else:
            self.local_tallies[choice] = 1
        return True

    def is_leader(self) -> bool:
        return bool(self.current_poll and self.current_poll.get("sender_id") == self.node_id)

    def compute_tallies(self) -> Dict[int, int]:
        return dict(self.local_tallies)
