# main.py
import json
import os
import sys
import signal
from prompt_toolkit import prompt as prompt_toolkit_prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from colorama import init
init(autoreset=True)

# Local imports
from config_manager import ConfigManager, Colors
from workspace_manager import WorkspaceManager
from api_client import APIClient
from tool_executor import ToolExecutor
from agent_prompt import TOOL_BASED_AGENT_PROMPT

class UserCancelledException(Exception): pass
def signal_handler(signum, frame): raise UserCancelledException()

class TextualCLI:
    def __init__(self):
        self.config_manager = ConfigManager()
        if "--debug" in sys.argv: 
            self.config_manager.set_setting("debug_mode", True)
            print(f"{Colors.YELLOW}Debug mode is ON.{Colors.RESET}")
            
        self.api_client = APIClient(self.config_manager)
        self.messages = []
        self.workspace_manager = WorkspaceManager(self.config_manager.get_setting("workspace_path"))
        self.tool_executor = ToolExecutor(self.config_manager, self.workspace_manager)
        
        self.loaded_context = None
        self.history = []
        self.history_index = -1
        
        self.bindings = self._setup_key_bindings()
        self.commands = {
            "/help": self._handle_help, "/new": self._handle_new, "/exit": self._handle_exit,
            "/status": self._handle_status, "/load": self._handle_load, "/clear": self._handle_clear_context,
            "/workspace": self._handle_workspace, "/debug": self._handle_debug, "/providers": self._handle_providers,
            "/provider": self._handle_provider, "/model": self._handle_model, "/api": self._handle_api,
            "/verify": self._handle_verify
        }

    def _setup_key_bindings(self):
        bindings = KeyBindings()
        @bindings.add('enter')
        def _(event): event.app.current_buffer.insert_text('\n')
        @bindings.add('c-j', eager=True)
        def _(event): event.app.current_buffer.validate_and_handle()
        @bindings.add('up')
        def _(event):
            if self.history: 
                self.history_index = min(self.history_index + 1, len(self.history) - 1)
                event.app.current_buffer.text = self.history[self.history_index]
                event.app.current_buffer.cursor_position = len(event.app.current_buffer.text)
        @bindings.add('down')
        def _(event):
            if self.history: 
                self.history_index = max(self.history_index - 1, -1)
                event.app.current_buffer.text = '' if self.history_index == -1 else self.history[self.history_index]
                event.app.current_buffer.cursor_position = len(event.app.current_buffer.text)
        return bindings

    def start_new_chat(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        self.messages = [{"role": "system", "content": TOOL_BASED_AGENT_PROMPT}]
        self.loaded_context = None
        print(f"{Colors.BOLD}{Colors.PURPLE}Autonomous AI Agent (Tool-Calling Mode)")
        
        wksp = self.workspace_manager.workspace_path
        print(f"{Colors.CYAN}Workspace:{Colors.RESET} {wksp}" if wksp else f"{Colors.YELLOW}Warning: No workspace set. Use '/workspace <path>'.")
        print(f"{Colors.CYAN}Commands:{Colors.RESET} /help, /status, /load, /verify, /exit")
        print(f"{Colors.GRAY}Press Enter for a new line, Ctrl+J to send. Use Up/Down arrows for history.")

    # --- Command Handlers ---
    
    def display_help(self):
        print(f"""
{Colors.BOLD}{Colors.CYAN}--- Autonomous Agent - Help & Commands ---{Colors.RESET}
/help              : Show this help message.
/new               : Start a new conversation.
/exit              : Exit the application.
/status            : Show current configuration status.
/workspace <path>  : Set or show the workspace directory.
/load              : Load all text files from workspace into context for the next turn.
/clear             : Clear loaded file context.
/provider <name>   : Switch the active API provider (e.g., /provider groq).
/model <name>      : Set the model for the active provider.
/api <key>         : Set the API key for the active provider.
/verify            : Test the connection to the current provider.
/debug             : Toggle debug mode (shows API payloads).
""")

    def _handle_help(self, _): self.display_help()
    def _handle_new(self, _): self.start_new_chat()
    def _handle_exit(self, _): sys.exit("Exiting. Goodbye!")
    def _handle_clear_context(self, _): self.loaded_context = None; print(f"{Colors.GREEN}File context cleared.{Colors.RESET}")
    
    def _handle_debug(self, _): 
        current = self.config_manager.get_setting("debug_mode")
        self.config_manager.set_setting("debug_mode", not current)
        print(f"{Colors.YELLOW}Debug mode is now {Colors.BOLD}{'ON' if not current else 'OFF'}{Colors.RESET}")

    def _handle_workspace(self, parts):
        if len(parts) > 1:
            path = ' '.join(parts[1:])
            if os.path.isdir(path): 
                self.workspace_manager.set_workspace_path(os.path.abspath(path))
                self.config_manager.set_setting("workspace_path", self.workspace_manager.workspace_path)
                print(f"{Colors.GREEN}Workspace set to: {self.workspace_manager.workspace_path}")
                self.start_new_chat()
            else: 
                print(f"{Colors.RED}Error: Directory not found.")
        else: 
            print(f"Current workspace: {self.workspace_manager.workspace_path or 'Not set'}")

    def _handle_providers(self, _):
        providers = self.config_manager.get_setting("providers").keys()
        active = self.config_manager.get_active_provider_key()
        print(f"{Colors.BOLD}{Colors.CYAN}Available Providers:{Colors.RESET}")
        for p in providers:
            print(f"  - {Colors.BOLD}{Colors.GREEN}{p} (active){Colors.RESET}" if p == active else f"  - {p}")

    def _handle_provider(self, parts):
        if len(parts) > 1:
            name = parts[1].lower()
            if name in self.config_manager.get_setting("providers"): 
                self.config_manager.set_active_provider(name)
                print(f"{Colors.GREEN}Active provider set to: {Colors.BOLD}{name}{Colors.RESET} (Model: {self.config_manager.get_provider_setting('model')})")
                self.start_new_chat()
            else: 
                print(f"{Colors.RED}Error: Provider '{name}' not found.")
        else: 
            print(f"{Colors.YELLOW}Usage: /provider <name>")

    def _handle_model(self, parts):
        if len(parts) > 1: 
            model = ' '.join(parts[1:])
            self.config_manager.set_provider_setting("model", model)
            print(f"{Colors.GREEN}Model for '{self.config_manager.get_active_provider_key()}' set to: {Colors.BOLD}{model}{Colors.RESET}")
        else: 
            print(f"{Colors.YELLOW}Usage: /model <model_name>")

    def _handle_api(self, parts):
        if len(parts) > 1: 
            self.config_manager.set_provider_setting("api_key", parts[1])
            print(f"{Colors.GREEN}API key for '{self.config_manager.get_active_provider_key()}' updated.{Colors.RESET}")
        else: 
            print(f"{Colors.YELLOW}Usage: /api <your_api_key>")

    def _handle_load(self, _):
        # Corrected logic using the restored get_all_files_in_workspace
        if not self.workspace_manager.workspace_path:
             print(f"{Colors.RED}Error: Workspace not set.{Colors.RESET}"); return

        print(f"{Colors.YELLOW}Calculating size...{Colors.RESET}", end="\r")
        
        load_result = self.workspace_manager.get_all_files_in_workspace()
        files_to_load = load_result['text_files']
        skipped_binaries = load_result['skipped_binaries']

        if not files_to_load: 
            print(f"{Colors.YELLOW}No text files found in workspace." + " " * 20)
            return

        total_size = 0
        for p in files_to_load:
             full_p, _ = self.workspace_manager._resolve_and_check_path(p)
             if full_p and os.path.exists(full_p):
                 total_size += os.path.getsize(full_p)

        print(" " * 60, end="\r")
        if total_size > 150000:
            print(f"{Colors.BOLD}{Colors.YELLOW}Warning:{Colors.RESET} Loading {len(files_to_load)} files ({total_size:,} bytes). This may incur high costs/latency.")
            if input("Continue? (y/n): ").lower() not in ['y', 'yes']: 
                print(f"{Colors.RED}Load operation cancelled.{Colors.RESET}")
                return

        print(f"{Colors.YELLOW}Loading content...{Colors.RESET}")
        full_context = "The user has loaded the entire workspace. Here are the file contents:\n\n"
        
        for file_path in files_to_load:
            result = self.workspace_manager.read_file(file_path)
            if result.get('success'): 
                full_context += f"--- START OF FILE: {file_path} ---\n{result['content']}\n--- END OF FILE: {file_path} ---\n\n"
            else: 
                print(f"{Colors.RED}Could not read file {file_path}: {result.get('error')}")
        
        self.loaded_context = full_context
        print(f"{Colors.GREEN}Loaded {len(files_to_load)} text files ({total_size:,} bytes). {len(skipped_binaries)} binary files were skipped.{Colors.RESET}")

    def _handle_status(self, _):
        key = self.config_manager.get_provider_setting("api_key") or ""
        masked_key = f"{key[:5]}...{key[-4:]}" if len(key) > 9 else "Not Set"
        print(f"""
{Colors.BOLD}{Colors.CYAN}--- Current Status ---{Colors.RESET}
{Colors.CYAN}Workspace:{Colors.RESET}       {self.workspace_manager.workspace_path or 'Not Set'}
{Colors.CYAN}Provider:{Colors.RESET}        {self.config_manager.get_active_provider_key()}
{Colors.CYAN}Model:{Colors.RESET}           {self.config_manager.get_provider_setting("model")}
{Colors.CYAN}API Key:{Colors.RESET}         {masked_key}
{Colors.CYAN}Auto-Approve:{Colors.RESET}    {'OFF' if self.config_manager.get_setting("confirm_actions") else 'ON'}
{Colors.CYAN}Loaded Context:{Colors.RESET}  {f'{len(self.loaded_context):,} chars' if self.loaded_context else 'None'}
""")

    def _handle_verify(self, _):
        print(f"{Colors.YELLOW}Verifying connection to '{self.config_manager.get_active_provider_key()}'...{Colors.RESET}")
        verify_messages = [
            {"role": "system", "content": "You are a helpful assistant. Please respond with only the word 'Success'."}, 
            {"role": "user", "content": "This is a connection test."}
        ]
        response, success = self.api_client.get_response(verify_messages, tools=[])
        if success and response.get('type') == 'text': 
            print(f"{Colors.BOLD}{Colors.GREEN}Verification successful!{Colors.RESET}")
            print(f"{Colors.GRAY}Model responded: \"{response['content'].strip()}\"")
        else: 
            print(f"{Colors.BOLD}{Colors.RED}Verification failed.{Colors.RESET}")
            print(response)

    def handle_command(self, user_input):
        parts = user_input.strip().split()
        command = parts[0].lower()
        handler = self.commands.get(command)
        if handler: 
            handler(parts)
        else: 
            print(f"{Colors.RED}Unknown command '{command}'. Type /help for assistance.")

    def process_bot_turn(self):
        if not self.workspace_manager.workspace_path:
            print(f"\n{Colors.BOLD}{Colors.RED}Error:{Colors.RESET} No workspace is set. Use `/workspace <path>`.")
            if self.messages and self.messages[-1].get("role") == "user": 
                self.messages.pop()
            return

        # Inject loaded context if available
        if self.loaded_context:
            if self.messages and self.messages[-1].get("role") == "user":
                last_user_message = self.messages[-1]['content']
                self.messages[-1]['content'] = self.loaded_context + "\n--- User's Prompt ---\n" + last_user_message
                self.loaded_context = None
                print(f"{Colors.CYAN}Injecting loaded context into this turn...{Colors.RESET}")

        # AUTONOMOUS LOOP
        MAX_LOOPS = 15
        loop_count = 0
        keep_running = True

        while keep_running and loop_count < MAX_LOOPS:
            loop_count += 1
            try:
                # Prepare messages
                current_messages = list(self.messages)
                
                # Visual Indicator
                print(f"\n{Colors.YELLOW}🤖 Agent is thinking (Step {loop_count})...{Colors.RESET}", end="\r", flush=True)
                
                # API Call
                response, success = self.api_client.get_response(current_messages, stream=False)
                
                print(" " * 60, end="\r") # Clear loading line

                if not success:
                    print(f"\n{Colors.RED}[API Error]{Colors.RESET}: {response}")
                    break

                # --- Case 1: Tool Calls ---
                if response['type'] == 'tool_call':
                    active_provider = self.config_manager.get_active_provider_key()
                    tool_calls = response['calls']

                    # Format calls for history
                    if active_provider == 'google':
                        openai_formatted_tool_calls = [{'id': f"call_{i}", 'type': 'function', 'function': {'name': tc['name'], 'arguments': json.dumps(tc.get('args', {}))}} for i, tc in enumerate(tool_calls)]
                    else:
                        openai_formatted_tool_calls = tool_calls

                    assistant_message = {'role': 'assistant', 'content': None, 'tool_calls': openai_formatted_tool_calls}
                    self.messages.append(assistant_message)
                    
                    print(f"{Colors.CYAN}›› Agent wants to execute {len(tool_calls)} tool(s)...{Colors.RESET}")

                    # Execute Tools
                    for i, tool_call in enumerate(tool_calls):
                        call_id = openai_formatted_tool_calls[i]['id']
                        result, name, _ = self.tool_executor.process_tool_call(tool_call, active_provider)
                        
                        if name:
                            tool_message = {'role': 'tool', 'name': name, 'content': json.dumps(result), 'tool_call_id': call_id}
                            self.messages.append(tool_message)

                    # Continue loop automatically
                    continue

                # --- Case 2: Text Response ---
                elif response['type'] == 'text':
                    content = response['content']
                    print(f"\n{Colors.BOLD}{Colors.BLUE}🤖 Agent:{Colors.RESET} {content}")
                    self.messages.append({'role': 'assistant', 'content': content})

                    if "TASK_FINISHED" in content:
                        print(f"\n{Colors.GREEN}✅ Task Completed.{Colors.RESET}")
                        keep_running = False
                    else:
                        # If no tool called and no finished signal, it's likely a question or interim update.
                        keep_running = False

            except (UserCancelledException, KeyboardInterrupt):
                print("\n" + f"{Colors.YELLOW}--- Agent execution cancelled by user. ---{Colors.RESET}")
                break
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"{Colors.RED}\nAn unexpected error occurred: {e}{Colors.RESET}")
                break
        
        if loop_count >= MAX_LOOPS:
            print(f"\n{Colors.RED}⚠️ Safety Limit Reached ({MAX_LOOPS} turns). Pausing execution.{Colors.RESET}")
            print(f"{Colors.GRAY}Type 'continue' to resume or enter a new prompt.{Colors.RESET}")

    def run(self):
        signal.signal(signal.SIGINT, signal_handler)
        self.start_new_chat()
        
        while True:
            try:
                workspace_name = os.path.basename(self.workspace_manager.workspace_path) if self.workspace_manager.workspace_path else "No-Wksp"
                prompt_message = HTML(f'<bold><ansigreen>You ({workspace_name}):</ansigreen></bold> ')
                print()
                
                user_input = prompt_toolkit_prompt(message=prompt_message, multiline=True, key_bindings=self.bindings)
                
                if not user_input.strip(): 
                    continue
                
                if user_input.strip() not in self.history: 
                    self.history.insert(0, user_input.strip())
                self.history_index = -1
                
                if user_input.startswith('/'): 
                    self.handle_command(user_input)
                else: 
                    self.messages.append({"role": "user", "content": user_input.strip()})
                    self.process_bot_turn()
                    
            except (UserCancelledException, EOFError): 
                sys.exit(f"\n{Colors.YELLOW}Exiting agent. Goodbye!{Colors.RESET}")

if __name__ == "__main__":
    cli = TextualCLI()
    cli.run()