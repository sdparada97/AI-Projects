from collections import defaultdict
from threading import Lock


class ConversationStore:
    def __init__(self, history_limit: int = 20) -> None:
        self._history_limit = history_limit
        self._data: dict[str, list[dict[str, str]]] = defaultdict(list)
        self._lock = Lock()

    def get(self, conversation_id: str) -> list[dict[str, str]]:
        with self._lock:
            return list(self._data.get(conversation_id, []))

    def append_turn(self, conversation_id: str, role: str, content: str) -> None:
        with self._lock:
            history = self._data[conversation_id]
            history.append({"role": role, "content": content})
            if len(history) > self._history_limit:
                self._data[conversation_id] = history[-self._history_limit :]


conversation_store = ConversationStore()
