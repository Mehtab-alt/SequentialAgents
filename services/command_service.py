# services/command_service.py
import os
import asyncio
from typing import Dict, Any, List

# Forward declarations for type hinting
from ..config_manager import ConfigManager
from ..workspace_manager import WorkspaceManager
from ..api_client import APIClient
from .chat_session_service import ChatSessionService
from ..exceptions import InvalidCommandError

class CommandService:
    """Handles the execution of all user-facing slash commands."""

    def __init__(self, config: ConfigManager, workspace: WorkspaceManager, session: ChatSessionService, api: APIClient):
        self.config = config
        self.workspace = workspace
        self.session = session
        self.api = api
        self.commands = {
            "/help": self._handle_help, "/new": self._handle_new, "/exit": self._handle_exit,
            "/status": self._handle_status, "/context": self._handle_context, "/workspace": self._handle_workspace,
            "/debug": self._handle_debug, "/providers": self._handle_providers, "/provider": self._handle_provider,
            "/model": self._handle_model, "/api": self._handle_api, "/verify": self._handle_verify,
        }

    async def execute(self, user_input: str) -> Dict[str, Any]:
        """Parses and executes a command, returning a structured result."""
        parts = user_input.strip().split()
        command_name = parts[0].lower()
        handler = self.commands.get(command_name)
        if not handler:
            raise InvalidCommandError(f"Unknown command '{command_name}'.")
        
        # Await if the handler is async, otherwise call it directly
        if asyncio.iscoroutinefunction(handler):
            return await handler(parts)
        else:
            return handler(parts)

    def _handle_help(self, parts: List[str]) -> Dict[str, Any]:
        help_text = """
--- Help & Commands ---
/help              : Show this help message.
/new               : Start a new conversation.
/exit              : Exit the application.
/status            : Show current configuration status.
/workspace <path>  : Set or show the workspace directory.
/context <add|list|clear> [path]: Manage files in the agent's context.
/provider <name>   : Switch the active API provider.
/model <name>      : Set the model for the active provider.
/api <key>         : Set the API key for the active provider.
/verify            : Test the connection to the current provider.
/debug             : Toggle debug mode.
/providers         : List all configured providers.
"""
        return {'success': True, 'message': help_text}

    def _handle_new(self, parts: List[str]) -> Dict[str, Any]:
        self.session.start_new_session()
        return {'success': True, 'message': "New chat session started."}

    def _handle_exit(self, parts: List[str]) -> Dict[str, Any]:
        # The UI will interpret this success as a signal to exit.
        return {'success': True}

    async def _handle_context(self, parts: List[str]) -> Dict[str, Any]:
        if len(parts) < 2:
            raise InvalidCommandError("Usage: /context <add|list|clear> [path]")
        subcommand = parts[1].lower()
        if subcommand == "add":
            if len(parts) < 3:
                raise InvalidCommandError("Usage: /context add <path/to/file_or_dir>")
            path_str = " ".join(parts[2:])
            return await self._handle_context_add(path_str)
        elif subcommand == "list":
            files = self.session.get_context_files()
            msg = "Files in context:\n- " + "\n- ".join(files) if files else "Context is empty."
            return {'success': True, 'message': msg}
        elif subcommand == "clear":
            self.session.clear_context()
            return {'success': True, 'message': "Context cleared."}
        else:
            raise InvalidCommandError(f"Unknown subcommand '{subcommand}'. Use add, list, or clear.")

    async def _handle_context_add(self, path_str: str) -> Dict[str, Any]:
        """Adds file(s) to the context with a safety check."""
        files_to_read = await self.workspace.get_text_files_in_path(path_str)
        if not files_to_read:
            return {'success': False, 'error': f"No text files found at '{path_str}'."}

        total_chars = 0
        content_to_load = {}
        for file_path in files_to_read:
            result = await self.workspace.read_file(file_path)
            if result.get('success'):
                content = result['content']
                total_chars += len(content)
                content_to_load[file_path] = content
        
        if total_chars > 100000:
            print(f"Warning: You are about to load {len(content_to_load)} files with a total of {total_chars:,} characters into the context. This may incur high API costs.")
            confirm = input("Continue? (y/n): ").lower()
            if confirm not in ['y', 'yes']:
                return {'success': False, 'error': "Load operation cancelled by user."}

        for path, content in content_to_load.items():
            self.session.add_to_context(path, content)
            
        return {'success': True, 'message': f"Added {len(content_to_load)} file(s) to the context."}

    def _handle_workspace(self, parts: List[str]) -> Dict[str, Any]:
        if len(parts) > 1:
            path = ' '.join(parts[1:])
            if os.path.isdir(path):
                abs_path = os.path.abspath(path)
                self.workspace.set_workspace_path(abs_path)
                self.config.set_setting("workspace_path", abs_path)
                self.session.start_new_session()
                return {'success': True, 'message': f"Workspace set to: {abs_path}"}
            else:
                return {'success': False, 'error': "Directory not found."}
        else:
            path = self.workspace.workspace_path or 'Not set'
            return {'success': True, 'message': f"Current workspace: {path}"}
    
    # ... other command handlers (_handle_status, _handle_provider, etc.) would be similarly refactored ...
