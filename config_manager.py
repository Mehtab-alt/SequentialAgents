# config_manager.py
import json
import os
from colorama import Fore, Style

class Colors:
    """ANSI color codes for terminal output."""
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    PURPLE = Fore.MAGENTA
    CYAN = Fore.CYAN
    GRAY = Fore.LIGHTBLACK_EX
    BOLD = Style.BRIGHT
    RESET = Style.RESET_ALL

class ConfigManager:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self.load_and_migrate_config()

    def create_default_config(self):
        """Defines the schema and default values for the application."""
        return {
            "active_provider": "google",
            "debug_mode": False,
            "workspace_path": None,
            "confirm_actions": False,  # Default to False for autonomous behavior
            "providers": {
                "google": {
                    "api_key": "YOUR_GOOGLE_AI_STUDIO_API_KEY_HERE",
                    "api_url": "https://generativelanguage.googleapis.com/v1beta/models",
                    "model": "gemini-2.0-flash-exp" 
                },
                "openai": {
                    "api_key": "YOUR_OPENAI_API_KEY_HERE",
                    "api_url": "https://api.openai.com/v1/chat/completions",
                    "model": "gpt-4o"
                },
                "openrouter": {
                    "api_key": "YOUR_OPENROUTER_KEY_HERE",
                    "api_url": "https://openrouter.ai/api/v1/chat/completions",
                    "model": "anthropic/claude-3.5-sonnet"
                },
                "groq": {
                    "api_key": "YOUR_GROQ_API_KEY_HERE",
                    "api_url": "https://api.groq.com/openai/v1/chat/completions",
                    "model": "llama3-70b-8192"
                },
                "ollama": {
                    "api_key": "ollama",
                    "api_url": "http://localhost:11434/api/chat",
                    "model": "llama3.1"
                },
                "lmstudio": {
                    "api_key": "lm-studio",
                    "api_url": "http://localhost:1234/v1/chat/completions",
                    "model": "local-model"
                }
            }
        }

    def load_and_migrate_config(self):
        """
        Loads the config file. If it doesn't exist, creates it.
        If it exists but lacks new keys (migration), adds them.
        """
        default_config = self.create_default_config()
        
        if not os.path.exists(self.config_file):
            print(f"{Colors.YELLOW}Configuration file not found. Creating '{self.config_file}'...{Colors.RESET}")
            self.save_config(default_config)
            return default_config

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            updated = False
            
            # Migrate top-level keys
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
                    updated = True
            
            # Migrate providers
            if "providers" not in config:
                config["providers"] = default_config["providers"]
                updated = True
            else:
                for provider, settings in default_config["providers"].items():
                    if provider not in config["providers"]:
                        config["providers"][provider] = settings
                        updated = True
                    else:
                        # Migrate missing settings within a provider
                        for setting_key, setting_val in settings.items():
                            if setting_key not in config["providers"][provider]:
                                config["providers"][provider][setting_key] = setting_val
                                updated = True

            if updated:
                print(f"{Colors.GRAY}Configuration migrated to include new defaults.{Colors.RESET}")
                self.save_config(config)
                
            return config
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"{Colors.RED}Error reading config file: {e}. A default config will be used temporarily.{Colors.RESET}")
            return default_config

    def save_config(self, data):
        """Writes the configuration to disk."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            print(f"{Colors.RED}Failed to save configuration: {e}{Colors.RESET}")

    def get_setting(self, key):
        return self.config.get(key)

    def set_setting(self, key, value):
        self.config[key] = value
        self.save_config(self.config)

    def get_active_provider_key(self):
        return self.config.get("active_provider", "google")

    def get_provider_setting(self, key):
        active = self.get_active_provider_key()
        return self.config.get("providers", {}).get(active, {}).get(key)

    def set_provider_setting(self, key, value):
        active = self.get_active_provider_key()
        if "providers" not in self.config:
            self.config["providers"] = {}
        if active not in self.config["providers"]:
            self.config["providers"][active] = {}
            
        self.config["providers"][active][key] = value
        self.save_config(self.config)

    def set_active_provider(self, provider_name):
        provider_name = provider_name.lower()
        if provider_name not in self.config.get("providers", {}):
            default_defaults = self.create_default_config()["providers"].get(provider_name, {"api_key": "", "api_url": "", "model": ""})
            self.config.setdefault("providers", {})[provider_name] = default_defaults
            
        self.config["active_provider"] = provider_name
        self.save_config(self.config)