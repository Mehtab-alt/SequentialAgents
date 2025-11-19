# services/chat_session_service.py
from typing import Any, Dict, List, Optional

class ChatSessionService:
    """Manages the state of a single chat session, including messages, context, and history."""
    def __init__(self, system_prompt: str):
        """Initializes a new chat session."""
        self.system_prompt = system_prompt
        self.messages: List[Dict[str, Any]] = []
        self.managed_context: Dict[str, str] = {}  # {file_path: content}
        self.command_history: List[str] = []
        self.history_index: int = -1
        self.start_new_session()

    def start_new_session(self) -> None:
        """Clears messages and context to start a new session."""
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.clear_context()

    def add_message(self, message: Dict[str, Any]) -> None:
        """Adds a message to the current session's message list."""
        self.messages.append(message)

    def get_messages(self) -> List[Dict[str, Any]]:
        """Returns a copy of the current messages in the session."""
        return self.messages.copy()

    def add_to_context(self, file_path: str, content: str) -> None:
        """Adds or updates file content in the managed context."""
        self.managed_context[file_path] = content

    def get_context_files(self) -> List[str]:
        """Returns a list of file paths currently in the context."""
        return list(self.managed_context.keys())

    def clear_context(self) -> None:
        """Clears all files from the managed context."""
        self.managed_context.clear()
        
    def add_to_command_history(self, user_input: str) -> None:
        """Adds a unique command to the history and resets the index."""
        if user_input not in self.command_history:
            self.command_history.insert(0, user_input)
        self.history_index = -1

    def get_previous_history(self) -> Optional[str]:
        """Retrieves the previous item from command history."""
        if self.command_history:
            self.history_index = min(self.history_index + 1, len(self.command_history) - 1)
            return self.command_history[self.history_index]
        return None

    def get_next_history(self) -> str:
        """Retrieves the next item from command history."""
        if self.command_history and self.history_index > -1:
            self.history_index = max(self.history_index - 1, -1)
            if self.history_index == -1:
                return ""
            return self.command_history[self.history_index]
        return ""

    def get_messages_with_injected_context(self) -> List[Dict[str, Any]]:
        """
        Creates a temporary message list for an API call by injecting the
        managed context into the last user message.
        """
        if not self.managed_context:
            return self.get_messages()

        temp_messages = self.get_messages()
        context_str = "--- CONTEXT START ---\n"
        for path, content in self.managed_context.items():
            context_str += f"--- FILE: {path} ---\n{content}\n--- END FILE: {path} ---\n\n"
        context_str += "--- CONTEXT END ---\n\n"

        last_user_msg_idx = -1
        for i in reversed(range(len(temp_messages))):
            if temp_messages[i]['role'] == 'user':
                last_user_msg_idx = i
                break
        
        if last_user_msg_idx != -1:
            original_content = temp_messages[last_user_msg_idx].get("content", "")
            temp_messages[last_user_msg_idx]['content'] = context_str + original_content

        return temp_messages
