# tool_executor.py
import json
from colorama import Style
from config_manager import ConfigManager, Colors
from workspace_manager import WorkspaceManager

class ToolExecutor:
    def __init__(self, config_manager: ConfigManager, workspace_manager: WorkspaceManager):
        self.config_manager = config_manager
        self.workspace_manager = workspace_manager
        # Map the tool names from the API schema to the actual methods in WorkspaceManager
        self.tool_map = {
            "list_files": workspace_manager.list_files,
            "read_file": workspace_manager.read_file,
            "write_file": workspace_manager.write_file,
            "create_directory": workspace_manager.create_directory,
            "delete_file": workspace_manager.delete_file,
            "apply_file_edit": workspace_manager.apply_file_edit
        }

    def _display_tool_result(self, result: dict):
        """Helper to pretty-print tool results to the console."""
        if not isinstance(result, dict):
            print(f"   {Colors.RED}Result: Invalid tool output format.{Style.RESET_ALL}")
            return
        
        if result.get('success'):
            if 'message' in result:
                print(f"   {Colors.GREEN}Result: {result['message']}{Style.RESET_ALL}")
            elif 'files' in result:
                file_list = result['files']
                limit = 15
                display_files = file_list[:limit]
                remaining = len(file_list) - limit
                files_str = '\n     - '.join(display_files)
                if remaining > 0:
                    files_str += f"\n     - ... and {remaining} more"
                print(f"   {Colors.GREEN}Result: Successfully listed files:{Style.RESET_ALL}\n     - {files_str if file_list else '(empty directory)'}")
            elif 'content' in result:
                line_count = len(result['content'].splitlines())
                print(f"   {Colors.GREEN}Result: Successfully read file ({line_count} lines).{Style.RESET_ALL}")
            else:
                print(f"   {Colors.GREEN}Result: Operation successful.{Style.RESET_ALL}")
        else:
            print(f"   {Colors.RED}Result: {result.get('error', 'An unknown error occurred.')}{Style.RESET_ALL}")

    def _execute_tool(self, function_name, arguments):
        """Executes the mapped function safely."""
        if function_name not in self.tool_map:
            return {"success": False, "error": f"Unknown tool: {function_name}"}
        
        try:
            # Default path for list_files if missing
            if function_name == 'list_files' and 'path' not in arguments:
                arguments['path'] = '.'
            
            # Call the function
            return self.tool_map[function_name](**arguments)
        except TypeError as e:
            return {"success": False, "error": f"Argument mismatch for {function_name}: {e}"}
        except Exception as e:
            return {"success": False, "error": f"Error executing tool {function_name}: {e}"}

    def process_tool_call(self, tool_call, active_provider):
        """
        Parses and executes a tool call.
        AUTONOMOUS MODE: Executes immediately without user confirmation.
        """
        # 1. Parse Arguments based on Provider
        if active_provider == 'google':
            function_name = tool_call.get('name')
            arguments = tool_call.get('args', {})
            tool_call_id = None
        else:
            function_name = tool_call.get('function', {}).get('name')
            tool_call_id = tool_call.get('id')
            try:
                arguments = json.loads(tool_call.get('function', {}).get('arguments', '{}'))
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"Invalid JSON in arguments: {e}"}, function_name, tool_call_id

        if not function_name:
            return {"success": False, "error": "Could not parse function name from tool call."}, None, None

        # 2. Log Intent (Informational only, non-blocking)
        arg_summary = json.dumps(arguments)
        if len(arg_summary) > 120: 
            arg_summary = arg_summary[:117] + "..."
        print(f"{Colors.CYAN}›› Agent running: {Colors.BOLD}{function_name}{Style.RESET_ALL}{Colors.CYAN}({arg_summary}){Style.RESET_ALL}")

        # 3. Execute Immediately (Autonomous)
        tool_result = self._execute_tool(function_name, arguments)
        
        # 4. Display and Return
        self._display_tool_result(tool_result)
        return tool_result, function_name, tool_call_id