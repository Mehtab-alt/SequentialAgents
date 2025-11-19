# api_client.py
import json
import urllib.request
import urllib.error
from colorama import Style
from config_manager import ConfigManager, Colors

# --- TOOL DEFINITIONS ---

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Lists files and directories at a given path within the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The relative path from the workspace root. Defaults to '.'."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the full content of a file within the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The relative path to the file."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Writes or overwrites an ENTIRE file with new content. WARNING: Do not use for small edits; use apply_file_edit instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The relative path to the file."},
                    "content": {"type": "string", "description": "The full content to write to the file."}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Creates a new directory (and any parent directories).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The relative path for the new directory."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Deletes a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The relative path of the file to delete."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "apply_file_edit",
            "description": "Applies a precise search-and-replace edit to a file. The search_block must match existing content exactly (or close enough for fuzzy matching) and be unique.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The relative path to the file to modify."},
                    "search_block": {"type": "string", "description": "The exact block of code to find. Must be unique in the file."},
                    "replace_block": {"type": "string", "description": "The new block of code to insert in place of the search_block."}
                },
                "required": ["path", "search_block", "replace_block"]
            }
        }
    }
]

GOOGLE_TOOLS = [tool["function"] for tool in OPENAI_TOOLS]

class APIClient:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager

    def _transform_messages_for_google(self, messages):
        transformed = []
        system_prompt = ""
        
        if messages and messages[0].get("role") == "system":
            system_prompt = messages[0].get("content", "")

        for msg in messages:
            role = msg.get("role")
            if role == "system":
                continue
            
            if role == "assistant":
                if "tool_calls" in msg and msg["tool_calls"]:
                    function_calls = []
                    for tc in msg['tool_calls']:
                        if isinstance(tc, dict):
                            args_str = tc['function']['arguments']
                            name = tc['function']['name']
                        else:
                            args_str = tc.function.arguments
                            name = tc.function.name
                            
                        try:
                            args = json.loads(args_str)
                        except (json.JSONDecodeError, TypeError):
                            args = {}
                        function_calls.append({"functionCall": {"name": name, "args": args}})
                    transformed.append({"role": "model", "parts": function_calls})
                else:
                    transformed.append({"role": "model", "parts": [{"text": msg.get("content", "")}]})
            
            elif role == "tool":
                content_obj = json.loads(msg.get("content", "{}"))
                transformed.append({"role": "function", "parts": [{"functionResponse": {"name": msg.get("name"), "response": {"content": content_obj}}}]})
            
            elif role == "user":
                content = msg.get("content", "")
                if system_prompt:
                    content = f"{system_prompt}\n\n--- USER'S TASK ---\n\n{content}"
                    system_prompt = ""
                transformed.append({"role": "user", "parts": [{"text": content}]})

        final_transformed = []
        if not transformed: return []
        
        i = 0
        while i < len(transformed):
            current_msg = transformed[i]
            if current_msg["role"] == "function":
                function_parts = []
                while i < len(transformed) and transformed[i]["role"] == "function":
                    function_parts.extend(transformed[i]["parts"])
                    i += 1
                final_transformed.append({"role": "function", "parts": function_parts})
            else:
                final_transformed.append(current_msg)
                i += 1
        return final_transformed

    def _send_request(self, url, data, headers):
        if self.config.get_setting("debug_mode"):
            print(f"\n{Colors.GRAY}--- DEBUG: Request Start ---\n{Colors.CYAN}URL:{Style.RESET_ALL} {url}\n{Colors.CYAN}Headers:{Style.RESET_ALL} {json.dumps(headers, indent=2)}\n{Colors.CYAN}Payload:{Style.RESET_ALL} {json.dumps(data, indent=2)}\n{Colors.GRAY}--- DEBUG: Request End ---\n")
        
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method="POST")
        return urllib.request.urlopen(req, timeout=300)

    def _handle_request_error(self, e):
        if isinstance(e, urllib.error.HTTPError):
            error_body = e.read().decode('utf-8', errors='ignore')
            try:
                detailed_error = json.dumps(json.loads(error_body).get('error', json.loads(error_body)), indent=2)
            except (json.JSONDecodeError, AttributeError):
                detailed_error = error_body
            return f"\n{Colors.RED}[API Request Failed: {e}]\n{Colors.YELLOW}Server Response:\n{detailed_error}", False
        return f"\n{Colors.RED}[Request Error: {e}]", False

    def get_response(self, messages, stream=False, tools=None):
        active_provider = self.config.get_active_provider_key()
        api_key = self.config.get_provider_setting("api_key")
        model = self.config.get_provider_setting("model")
        url = self.config.get_provider_setting("api_url")

        if not api_key or "YOUR_" in (api_key or ""):
            if active_provider not in ['ollama', 'lmstudio']:
                return f"{Colors.BOLD}{Colors.RED}Error: API key for '{active_provider}' is not set.", False

        current_tools = tools if tools is not None else (GOOGLE_TOOLS if active_provider == 'google' else OPENAI_TOOLS)

        if active_provider == 'google':
            return self._get_google_response(messages, api_key, model, url, current_tools, stream)
        else:
            return self._get_openai_compatible_response(messages, api_key, model, url, current_tools, stream)

    def _get_google_response(self, messages, api_key, model, base_url, tools, stream=False):
        url = f"{base_url}/{model}:streamGenerateContent?key={api_key}&alt=sse" if stream else f"{base_url}/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        transformed_messages = self._transform_messages_for_google(messages)
        
        data = {
            "contents": transformed_messages,
            "safetySettings": [{"category": f"HARM_CATEGORY_{c}", "threshold": "BLOCK_NONE"} for c in ["HARASSMENT", "HATE_SPEECH", "SEXUALLY_EXPLICIT", "DANGEROUS_CONTENT"]]
        }
        
        if tools:
            data["tools"] = [{"function_declarations": tools}]
            data["tool_config"] = {"function_calling_config": {"mode": "AUTO"}}

        try:
            resp = self._send_request(url, data, headers)
            if stream:
                return self._stream_google_response(resp), True
            
            with resp:
                response_data = json.loads(resp.read().decode('utf-8'))
                if 'candidates' not in response_data or not response_data['candidates']:
                    return f"\n{Colors.RED}[API Error: Invalid response. {response_data}]", False
                
                parts = response_data['candidates'][0].get('content', {}).get('parts', [])
                tool_calls = [part['functionCall'] for part in parts if 'functionCall' in part]
                
                if tool_calls:
                    return {'type': 'tool_call', 'calls': tool_calls}, True
                elif parts and 'text' in parts[0]:
                    return {'type': 'text', 'content': parts[0]['text']}, True
                else:
                    return f"\n{Colors.RED}[API Error: No text or tool_calls. {response_data}]", False
        except Exception as e:
            return self._handle_request_error(e)

    def _stream_google_response(self, response_iterator):
        with response_iterator as resp:
            for line in resp:
                line = line.decode('utf-8', errors='ignore').strip()
                if line.startswith('data:'):
                    try:
                        chunk = json.loads(line[len('data:'):].strip())
                        if 'candidates' in chunk and chunk['candidates']:
                            parts = chunk['candidates'][0].get('content', {}).get('parts', [{}])
                            if 'text' in parts[0]:
                                yield parts[0]['text']
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    def _get_openai_compatible_response(self, messages, api_key, model, url, tools, stream=False):
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {"model": model, "messages": messages, "stream": stream}
        
        if tools:
            data["tools"] = tools
            data["tool_choice"] = "auto"

        try:
            resp = self._send_request(url, data, headers)
            if stream:
                return self._stream_openai_compatible_response(resp), True
            
            with resp:
                response_json = json.loads(resp.read().decode('utf-8'))
                if "choices" not in response_json or not response_json["choices"]:
                    return f"\n{Colors.RED}[API Error: Invalid response. {response_json}]", False
                
                message = response_json["choices"][0]["message"]
                if message.get("tool_calls"):
                    return {'type': 'tool_call', 'calls': message["tool_calls"]}, True
                elif message.get("content"):
                    return {'type': 'text', 'content': message["content"]}, True
                else:
                    return f"\n{Colors.RED}[API Error: No content or tool_calls. {response_json}]", False
        except Exception as e:
            return self._handle_request_error(e)

    def _stream_openai_compatible_response(self, response_iterator):
        with response_iterator as resp:
            for line in resp:
                line = line.decode('utf-8', errors='ignore').strip()
                if line.startswith('data:'):
                    if line == 'data: [DONE]': break
                    try:
                        chunk = json.loads(line[len('data:'):].strip())
                        if "choices" in chunk and chunk["choices"]:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue