# SequentialAgents

**By [Mehtab Gul](https://github.com/Mehtab-alt)**

## Introduction
Welcome to the **SequentialAgents**, a cutting-edge agentic framework designed to perform complex software engineering tasks without constant human supervision. Unlike standard chatbots, this agent operates in a continuous **Autonomous Execution Loop**. It chains tools to list files, read code, apply fuzzy-logic edits, and verify its own work, stopping only when the task is fully complete.

##  Features
*   ** Autonomous Execution Loop:** Chains actions (List → Read → Edit → Verify) automatically without pausing for user input.
*   ** Fuzzy-Logic File Editing:** Includes a smart `apply_file_edit` tool that handles indentation corrections and whitespace mismatches, preventing common AI coding errors.
*   ** Multi-Provider Support:** Pre-configured for **Google Gemini 2.0 Flash** (Free Tier), OpenAI GPT-4o, Claude 3.5, and local models via Ollama.
*   ** Safe Workspace:** Confined to a specific directory to prevent accidental system changes.
*   ** Context Loading:** Can `/load` entire codebases into memory for deep context awareness.

##  Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/MehtabAlt/autonomous-ai-agent.git
    cd autonomous-ai-agent
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Agent:**
    ```bash
    python main.py
    ```

##  Configuration
On the first run, the agent generates a `config.json` file.
1.  Open `config.json`.
2.  Add your API Key (e.g., for Google AI Studio or OpenAI).
3.  Set `"active_provider"` to your choice (default: `google`).

*Note: `config.json` is automatically git-ignored to keep your keys safe.*

##  Usage
*   `/workspace <path>`: **Required.** Set the working directory.
*   `/load`: Load all text files in the workspace into context.
*   `/new`: Start a fresh session.
*   `/debug`: Toggle raw API payload logs.
