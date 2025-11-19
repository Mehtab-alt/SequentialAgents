# services/agent_orchestrator_service.py
import json
from typing import AsyncGenerator, Dict, Any

from ..api_client import APIClient
from ..tool_executor import ToolExecutor
from .chat_session_service import ChatSessionService
from ..config_manager import ConfigManager

class AgentOrchestratorService:
    """Orchestrates a single turn of the agent's logic."""
    def __init__(self, api: APIClient, tool_executor: ToolExecutor, session: ChatSessionService, config: ConfigManager):
        self.api = api
        self.tool_executor = tool_executor
        self.session = session
        self.config = config

    async def execute_turn(self, user_prompt: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Executes a full conversational turn as a generator, yielding structured events."""
        self.session.add_message({"role": "user", "content": user_prompt})
        
        yield {"type": "status", "content": "Agent is thinking..."}

        is_final_response = False
        while not is_final_response:
            messages_for_api = self.session.get_messages_with_injected_context()
            should_stream = len(messages_for_api) > 1 and messages_for_api[-1].get('role') == 'tool'
            
            response, success = await self.api.get_response(messages_for_api, stream=should_stream)

            if not success:
                yield {"type": "error", "content": response}
                return

            if should_stream:
                is_final_response = True
                full_content = ""
                async for chunk in response:
                    yield {"type": "response_chunk", "content": chunk}
                    full_content += chunk
                self.session.add_message({'role': 'assistant', 'content': full_content})

            elif response['type'] == 'tool_call':
                yield {"type": "status", "content": "Executing tools..."}
                tool_calls = response['calls']
                # ... (tool call processing logic, including fuzzy match confirmation) ...
                # For brevity, this complex logic is abstracted. The key is that a
                # fuzzy match result would yield a 'confirmation_required' event
                # and then the orchestrator would `return` to end the turn.

            elif response['type'] == 'text':
                is_final_response = True
                yield {"type": "final_response", "content": response['content']}
                self.session.add_message({'role': 'assistant', 'content': response['content']})
