import threading


class LamportClock:
    """
    Thread-safe implementation of a Lamport Logical Clock for establishing
    a strict causal partial order of events in a decentralized distributed system.
    
    Rules:
    1. Before an event is generated locally (send/message), increment clock: L = L + 1.
    2. When receiving a message with timestamp L_msg, update: L = max(L, L_msg) + 1.
    """

    def __init__(self, initial_value: int = 0) -> None:
        self._lock = threading.Lock()
        self._value = initial_value

    def tick(self) -> int:
        """Increments the logical clock and returns the new value for a local event."""
        with self._lock:
            self._value += 1
            return self._value

    def update(self, received_time: int) -> int:
        """Updates the local clock upon receiving a remote event timestamp."""
        with self._lock:
            self._value = max(self._value, received_time) + 1
            return self._value

    @property
    def value(self) -> int:
        """Returns the current logical clock value."""
        with self._lock:
            return self._value
