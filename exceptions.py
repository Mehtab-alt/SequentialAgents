# exceptions.py
"""
Custom exceptions for the Autonomous AI Agent application.

This module defines specific exception types to allow for more granular
error handling and clearer error messages throughout the application.
"""

class AgentException(Exception):
    """Base exception class for all custom exceptions in the agent."""
    pass

class APIKeyMissingError(AgentException):
    """Raised when an API key is required but not found for the active provider."""
    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"API key for provider '{provider}' is not set or invalid.")

class WorkspaceNotSetError(AgentException):
    """Raised when a workspace-dependent operation is attempted without a workspace being set."""
    def __init__(self, message: str = "Operation requires a workspace, but none is set. Use /workspace <path>."):
        self.message = message
        super().__init__(self.message)

class InvalidCommandError(AgentException):
    """Raised when the user enters an unknown or malformed command."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
