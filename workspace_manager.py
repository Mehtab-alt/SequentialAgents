# workspace_manager.py
import os
import fnmatch

class WorkspaceManager:
    def __init__(self, workspace_path=None):
        self.workspace_path = os.path.abspath(workspace_path) if workspace_path else None

    def set_workspace_path(self, path):
        self.workspace_path = os.path.abspath(path)

    def _resolve_and_check_path(self, path):
        """
        Resolves the relative path to an absolute path and ensures it is within the workspace.
        Renamed back to match main.py requirements.
        """
        if not self.workspace_path:
            return "", "Error: Workspace path is not set."
        
        # Normalize path to handle ../ and ./
        # Use realpath to resolve symlinks for security
        workspace_root = os.path.realpath(self.workspace_path)
        full_path = os.path.realpath(os.path.join(workspace_root, path))
        
        # Security check: Ensure the resolved path starts with the workspace path
        if not full_path.startswith(workspace_root):
            return "", f"Security Error: Path '{path}' attempts to access outside the workspace."
        
        return full_path, None

    def _is_binary(self, filepath):
        """Checks if a file is binary by looking for null bytes in the first 1KB."""
        try:
            with open(filepath, 'rb') as f:
                return b'\0' in f.read(1024)
        except IOError:
            return True

    def get_all_files_in_workspace(self):
        """
        Recursively finds all text files in the workspace, respecting ignore patterns.
        Required for the /load command.
        """
        if not self.workspace_path:
            return {'text_files': [], 'skipped_binaries': []}

        # Default ignore patterns
        ignore_patterns = {'.git', '.*.swp', '.DS_Store', '*.pyc', '*~', '.env', 'venv', '__pycache__'}
        dir_ignore_patterns = {'.git', '__pycache__', '.vscode', '.idea', 'node_modules', 'build', 'dist', 'venv', 'env'}
        
        # Load .agentignore if it exists
        agent_ignore_path = os.path.join(self.workspace_path, '.agentignore')
        if os.path.exists(agent_ignore_path):
            try:
                with open(agent_ignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped and not stripped.startswith('#'):
                            if stripped.endswith('/'):
                                dir_ignore_patterns.add(stripped.rstrip('/'))
                            else:
                                ignore_patterns.add(stripped)
            except Exception:
                pass

        text_files = []
        skipped_binaries = []

        for root, dirs, files in os.walk(self.workspace_path, topdown=True):
            # Modify dirs in-place to skip ignored directories
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pat) for pat in dir_ignore_patterns)]
            
            for file in files:
                if any(fnmatch.fnmatch(file, pat) for pat in ignore_patterns):
                    continue
                
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, self.workspace_path).replace('\\', '/')
                
                if self._is_binary(full_path):
                    skipped_binaries.append(relative_path)
                else:
                    text_files.append(relative_path)
                    
        return {'text_files': sorted(text_files), 'skipped_binaries': sorted(skipped_binaries)}

    def list_files(self, path="."):
        full_path, error = self._resolve_and_check_path(path)
        if error: return {'success': False, 'error': error}
        
        if not os.path.exists(full_path):
            return {'success': False, 'error': f"Directory not found: '{path}'"}
            
        try:
            entries = sorted(os.listdir(full_path))
            result = []
            for entry in entries:
                if entry.startswith('.'): continue # Skip hidden files
                
                entry_path = os.path.join(full_path, entry)
                if os.path.isdir(entry_path):
                    result.append(f"{entry}/")
                else:
                    result.append(entry)
            return {'success': True, 'files': result}
        except Exception as e:
            return {'success': False, 'error': f"Failed to list files: {str(e)}"}

    def read_file(self, path):
        full_path, error = self._resolve_and_check_path(path)
        if error: return {'success': False, 'error': error}
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {'success': True, 'content': content}
        except FileNotFoundError:
            return {'success': False, 'error': f"File not found: '{path}'"}
        except UnicodeDecodeError:
            return {'success': False, 'error': f"File '{path}' appears to be binary and cannot be read as text."}
        except Exception as e:
            return {'success': False, 'error': f"Error reading file: {str(e)}"}

    def write_file(self, path, content):
        full_path, error = self._resolve_and_check_path(path)
        if error: return {'success': False, 'error': error}
        
        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {'success': True, 'message': f"File '{path}' written successfully."}
        except Exception as e:
            return {'success': False, 'error': f"Error writing file: {str(e)}"}

    def create_directory(self, path):
        full_path, error = self._resolve_and_check_path(path)
        if error: return {'success': False, 'error': error}
        
        try:
            os.makedirs(full_path, exist_ok=True)
            return {'success': True, 'message': f"Directory '{path}' created successfully."}
        except Exception as e:
            return {'success': False, 'error': f"Error creating directory: {str(e)}"}

    def delete_file(self, path):
        full_path, error = self._resolve_and_check_path(path)
        if error: return {'success': False, 'error': error}
        
        try:
            if not os.path.isfile(full_path):
                return {'success': False, 'error': f"File not found: '{path}'"}
            os.remove(full_path)
            return {'success': True, 'message': f"File '{path}' deleted successfully."}
        except Exception as e:
            return {'success': False, 'error': f"Error deleting file: {str(e)}"}

    def apply_file_edit(self, path, search_block, replace_block):
        """
        Applies a replacement to a file with high accuracy.
        Strategies:
        1. Exact Match: Locates the `search_block` exactly.
        2. Fuzzy Match: If exact match fails, locates lines matching `search_block` 
           ignoring leading/trailing whitespace.
        """
        full_path, error = self._resolve_and_check_path(path)
        if error: return {'success': False, 'error': error}
        
        if not os.path.exists(full_path):
            return {'success': False, 'error': f"File not found: '{path}'"}

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # --- Strategy A: Exact Match ---
            if search_block in original_content:
                count = original_content.count(search_block)
                if count > 1:
                    return {
                        'success': False, 
                        'error': "Ambiguous match: The 'search_block' was found multiple times in the file. Please provide more surrounding lines to make the search unique."
                    }
                
                # Perform exact replacement
                new_content = original_content.replace(search_block, replace_block, 1)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return {'success': True, 'message': "Edit applied successfully using exact match."}

            # --- Strategy B: Fuzzy Match (Whitespace Insensitive) ---
            
            file_lines = original_content.splitlines()
            search_lines = search_block.splitlines()
            
            stripped_search_lines = [line.strip() for line in search_lines]
            stripped_file_lines = [line.strip() for line in file_lines]
            
            matches = []
            n_search = len(stripped_search_lines)
            
            if n_search == 0:
                 return {'success': False, 'error': "Search block is empty."}

            # Scan for sequence
            for i in range(len(stripped_file_lines) - n_search + 1):
                segment = stripped_file_lines[i : i + n_search]
                if segment == stripped_search_lines:
                    matches.append(i)

            if len(matches) == 0:
                return {
                    'success': False, 
                    'error': "Match not found. The 'search_block' could not be located even with fuzzy matching (ignoring whitespace). Please verify the code exists in the file."
                }
            
            if len(matches) > 1:
                return {
                    'success': False, 
                    'error': f"Ambiguous fuzzy match: Found {len(matches)} occurrences ignoring whitespace. Please provide more unique surrounding lines."
                }

            # Match found at index matches[0]
            start_index = matches[0]
            end_index = start_index + n_search
            
            # --- Indentation Auto-Correction ---
            # Check indentation of the first line in the ORIGINAL file (not stripped)
            original_first_match_line = file_lines[start_index]
            current_indent = original_first_match_line[:len(original_first_match_line) - len(original_first_match_line.lstrip())]
            
            replace_lines = replace_block.splitlines()
            
            # If replacement has content but seemingly no indentation, and the original did, inject it.
            if replace_lines and current_indent:
                first_replace_line = replace_lines[0]
                if not first_replace_line.startswith(' ') and not first_replace_line.startswith('\t'):
                    # Apply the detected indentation to all lines in the replacement block
                    replace_block = "\n".join([current_indent + line for line in replace_lines])

            # Reconstruct file
            pre_content = "\n".join(file_lines[:start_index])
            post_content = "\n".join(file_lines[end_index:])
            
            final_content = ""
            if pre_content: final_content += pre_content + "\n"
            final_content += replace_block
            if post_content:
                if not replace_block.endswith('\n') and replace_block: 
                    final_content += "\n"
                final_content += post_content

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            return {'success': True, 'message': "Edit applied successfully using fuzzy match (indentation corrected)."}

        except Exception as e:
            return {'success': False, 'error': f"An unexpected error occurred during file edit: {str(e)}"}