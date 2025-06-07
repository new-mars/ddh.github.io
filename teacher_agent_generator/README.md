# Teacher Agent Generator

## Overview

The Teacher Agent Generator is a Python-based tool designed to create simulated teacher "agents" by generating responses to a series of predefined tasks (questions and questionnaire items) from various Language Learning Models (LLMs). Each agent is based on a persona defined in a CSV file, allowing for diverse and character-rich interactions. This tool can be used for educational research, developing AI-driven teaching simulations, or exploring LLM capabilities in persona adoption and response generation.

## Features

*   **Persona-Driven Responses:** Generates text based on detailed teacher personas.
*   **Multiple Task Types:** Supports open-ended questions and structured questionnaire items.
*   **Flexible LLM Integration:** Designed to interface with multiple LLM providers (e.g., Ollama, OpenAI-compatible APIs like DeepSeek, Qwen via Dashscope).
*   **Configurable Generation:** Allows customization of LLM provider, model, temperature, and max tokens via command-line arguments or a configuration file.
*   **Advanced Persona Refinement:** Supports additional optional attributes in `personas.csv` for more nuanced and detailed persona definitions, leading to more sophisticated system prompts.
*   **Detailed Output:** Saves generated data in JSONL format, including persona details, task information, prompts, LLM responses, and any errors encountered.
*   **Batch Processing:** Processes multiple personas against multiple tasks in a single run.
*   **Extensible:** Easily add new personas, tasks, or LLM providers.

## Project Structure

```
teacher_agent_generator/
├── data/                     # Input data files
│   ├── personas.csv          # CSV file defining teacher personas
│   ├── questions.txt         # Text file for open-ended questions
│   └── questionnaire.json    # JSON file for questionnaire items
├── outputs/                  # Output directory
│   ├── generated_agents/     # Directory for JSONL output files from main_generator.py
│   └── generation.log        # Log file for script operations
├── scripts/                  # Python scripts
│   ├── config.py             # Project configuration (API keys, paths, LLM defaults)
│   ├── persona_loader.py     # Loads and validates personas from personas.csv
│   ├── task_loader.py        # Loads tasks from questions.txt and questionnaire.json
│   ├── llm_interface.py      # Interface for communicating with various LLMs
│   └── main_generator.py     # Main script to orchestrate the generation process
├── .env_example              # Example environment file for API keys
└── README.md                 # This file
```

## Setup Instructions

### 1. Prerequisites

*   Python 3.8 or higher
*   `pip` for installing Python packages
*   Access to at least one LLM provider (e.g., Ollama installed locally, or API keys for cloud-based LLMs like Qwen, DeepSeek).

### 2. Installation

1.  **Clone the repository (if applicable) or download the project files.**
    ```bash
    # git clone <repository_url>
    # cd teacher_agent_generator
    ```

2.  **Install required Python libraries:**
    The script currently uses the `csv` module for `personas.csv` and does not strictly require `pandas`. The necessary libraries for LLM providers are installed on demand or checked for by `llm_interface.py`. The core dependency managed by the scripts is `python-dotenv`.
    ```bash
    pip install python-dotenv
    ```
    To use specific LLM providers, you'll need their respective SDKs:
    *   **Ollama:** `pip install ollama`
    *   **Qwen (Dashscope):** `pip install dashscope`
    *   **DeepSeek (or other OpenAI-compatible):** `pip install openai`

### 3. Ollama Setup (If using Ollama)

1.  **Install Ollama:** Follow the instructions on the [Ollama website](https://ollama.com/download).
2.  **Download an LLM model:**
    ```bash
    ollama pull llama3:8b-instruct  # Example model
    ollama pull mistral             # Another example
    ```
3.  **Ensure Ollama is running:** Typically, Ollama runs as a background service after installation. You can check its status or run `ollama serve` if needed (though usually not required for client access).

### 4. `.env` Configuration

API keys for LLM providers are managed via a `.env` file.

1.  **Create a `.env` file** in the `teacher_agent_generator` root directory by copying the example:
    ```bash
    cp .env_example .env
    ```
2.  **Edit the `.env` file** and add your actual API keys:
    ```env
    # API Keys - Replace with your actual keys
    OPENAI_API_KEY="your_openai_api_key_here_for_deepseek_or_openai"
    ANTHROPIC_API_KEY="your_anthropic_api_key_here" # Placeholder, update if using Anthropic or for Qwen if not using a dedicated key
    GOOGLE_GEMINI_API_KEY="your_google_gemini_api_key_here"
    # Add other keys as needed, e.g., DASHSCOPE_API_KEY for Qwen
    # DASHSCOPE_API_KEY="your_dashscope_api_key_for_qwen"
    ```
    *Note: `llm_interface.py` needs to be updated to use specific keys like `DASHSCOPE_API_KEY` for Qwen instead of the placeholder `ANTHROPIC_API_KEY`.*

## Data Format

### `data/personas.csv`
A CSV file where each row defines a teacher persona.
*   **Required Columns:**
    *   `name`: Full name of the persona (e.g., "Dr. Ada Coder").
    *   `gender`: Gender identity (e.g., "Female", "Male", "Non-binary").
    *   `title`: Professional title (e.g., "CS Professor", "Art Teacher").
    *   `teaching_experience_years`: Integer number of years (e.g., `10`).
    *   `professional_background`: Text describing their background, expertise, and interests.
    *   `teaching_plan`: Text describing their teaching philosophy, methods, or focus areas.
*   **Optional Columns for Enhanced Specificity:**
    These columns can be added to your `personas.csv` to provide more granular control over persona characteristics. They are highly recommended for generating more distinct and believable agent responses. If present and filled, they are used by `main_generator.py` to construct more detailed system prompts.
    *   `tone_keywords`: A comma-separated list of keywords describing the persona's typical tone (e.g., "formal, academic, inquisitive", "warm, encouraging, patient", "direct, concise").
    *   `communication_style`: Describes how the persona tends to communicate (e.g., "prefers analogies and storytelling", "often uses rhetorical questions to engage", "very direct and to-the-point").
    *   `key_terminology`: Comma-separated list of specific terms, jargon, or concepts the persona is likely to use frequently (e.g., "pedagogy, constructivism, differentiated instruction", "algorithm, data structure, computational thinking").
    *   `role_specific_directives`: Specific instructions or constraints for the LLM based on the persona's role or beliefs (e.g., "As a firm believer in student-led inquiry, always try to guide rather than directly answer.", "When discussing historical events, always mention primary sources if relevant.").
    *   `example_phrase`: A characteristic phrase or sentence the persona might use, helping to set the voice (e.g., "In my considered view...", "Alright team, let's explore this concept further!", "That's an excellent question; let's break it down.").
*   **Example with Optional Columns:**
    ```csv
    name,gender,title,teaching_experience_years,professional_background,teaching_plan,tone_keywords,communication_style,example_phrase
    Dr. Ada Coder,Female,CS Professor,10,"Loves Python and AI ethics","My teaching plan focuses on hands-on Python projects...","analytical, precise, encouraging","explains complex topics with code examples","Alright, let's debug this problem step-by-step."
    Mr. Bob Artist,Male,Art Teacher,5,"Prefers traditional media...","My teaching plan emphasizes mastering classical art techniques...","passionate, expressive, patient","uses vivid descriptions and historical context","Ah, a wonderful choice of medium! Let's explore its unique properties."
    ```
*   **Encoding:** It is highly recommended to save your `personas.csv` file with UTF-8 encoding, especially if it includes non-English characters (e.g., for names, background details, or teaching plans in other languages like Chinese). The script attempts to read the file as UTF-8 by default.

### `data/questions.txt`
A plain text file where each line represents an open-ended question.
*   Lines starting with `#` are treated as comments and ignored.
*   Empty lines are ignored.
*   **Example:**
    ```txt
    # Section: Teaching Philosophy
    What is your core teaching philosophy?
    How do you adapt your teaching style to different student needs?

    # Section: Classroom Management
    Describe a challenging classroom situation and how you resolved it.
    ```

### `data/questionnaire.json`
A JSON file containing a list of questionnaire items. Each item is an object with the following fields:
*   `id` (string): A unique identifier for the question (e.g., "q1_engagement").
*   `type` (string): The type of question (e.g., "multiple_choice", "likert_scale", "short_answer", "scenario_response"). This informs how the agent might be expected to respond or how the response is structured.
*   `text` (string): The text of the questionnaire item/prompt.
*   `options` (list, optional): For `multiple_choice` or similar types, a list of strings representing the available choices.
*   **Example:**
    ```json
    [
      {
        "id": "q1_engagement",
        "type": "multiple_choice",
        "text": "Which method do you find most effective for student engagement?",
        "options": ["Interactive lectures", "Group projects", "Gamification", "Inquiry-based learning"]
      },
      {
        "id": "q2_tech_comfort",
        "type": "likert_scale",
        "text": "Rate your comfort with integrating new technologies into your teaching (1=Very Uncomfortable, 5=Very Comfortable)."
      },
      {
        "id": "q3_feedback",
        "type": "short_answer",
        "text": "How do you typically provide feedback to students on their assignments?"
      }
    ]
    ```

## Usage

The main script for generating teacher agent responses is `scripts/main_generator.py`.

### Running the Script

Navigate to the project root directory (`teacher_agent_generator`) and run:
```bash
python scripts/main_generator.py [OPTIONS]
```

### Command-Line Arguments

The script accepts several command-line arguments to customize its behavior:

| Argument               | Description                                                                 | Default (from `config.py`) |
|------------------------|-----------------------------------------------------------------------------|----------------------------|
| `--provider`           | LLM provider (e.g., 'ollama', 'qwen', 'deepseek').                          | Based on `DEFAULT_MODEL`   |
| `--model`              | LLM model name (e.g., 'llama3:8b-instruct', 'qwen-turbo', 'deepseek-chat'). | Based on `DEFAULT_MODEL`   |
| `--temperature`        | Generation temperature (float).                                             | `DEFAULT_TEMPERATURE`      |
| `--max_tokens`         | Max tokens for generation (int).                                            | `MAX_TOKENS`               |
| `--personas_file`      | Path to personas CSV file.                                                  | `data/personas.csv`        |
| `--questions_file`     | Path to open-ended questions text file.                                     | `data/questions.txt`       |
| `--questionnaire_file` | Path to questionnaire JSON file.                                            | `data/questionnaire.json`  |
| `--output_dir`         | Directory to save generated agent data.                                     | `outputs/generated_agents/`|
| `--log_level`          | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).                      | `LOG_LEVEL` (e.g. INFO)    |

*(Note: `config.DEFAULT_MODEL` is often specified as `provider:model_name`, e.g., `ollama:llama3:8b-instruct`. The script parses this.)*

### Examples

1.  **Run with default settings (defined in `config.py`):**
    ```bash
    python scripts/main_generator.py
    ```

2.  **Run with Ollama provider and a specific model:**
    ```bash
    python scripts/main_generator.py --provider ollama --model llama3:8b-instruct
    ```
    *(Ensure Ollama is running and the model is downloaded: `ollama pull llama3:8b-instruct`)*

3.  **Run with DeepSeek provider and custom temperature:**
    ```bash
    python scripts/main_generator.py --provider deepseek --model deepseek-chat --temperature 0.8
    ```
    *(Requires DeepSeek API key in `.env` as `OPENAI_API_KEY`)*

4.  **Run with Qwen provider (Dashscope) and specific persona file:**
    ```bash
    python scripts/main_generator.py --provider qwen --model qwen-turbo --personas_file ./data/custom_personas.csv
    ```
    *(Requires Dashscope API key in `.env` and `llm_interface.py` updated to use it for Qwen)*

5.  **Set log level to DEBUG for more detailed output:**
    ```bash
    python scripts/main_generator.py --log_level DEBUG
    ```

## Output Format

The script generates a JSONL (JSON Lines) file in the directory specified by `--output_dir` (default: `outputs/generated_agents/`). Each line in the file is a JSON object representing the LLM's response for a single persona-task combination.

*   **Filename:** `generated_teacher_agents_YYYYMMDD_HHMMSS.jsonl` (timestamped)

*   **JSONL Record Structure (Example Fields):**
    ```json
    {
      "persona_name": "Dr. Ada Coder",
      "persona_details": {
        "name": "Dr. Ada Coder", "gender": "Female", "title": "CS Professor",
        "teaching_experience_years": 10,
        "professional_background": "Loves Python and AI ethics",
        "teaching_plan": "My teaching plan focuses on hands-on Python projects, real-world problem-solving, and fostering an understanding of ethical AI development."
      },
      "task_id": "task_0", // or specific ID from questionnaire.json
      "task_type": "open_ended", // or type from questionnaire.json
      "task_text": "What is your core teaching philosophy?",
      "system_prompt": "You are Dr. Ada Coder, CS Professor. You identify as Female. You have 10 years of teaching experience...",
      "user_prompt": "What is your core teaching philosophy?",
      "llm_response": "My core teaching philosophy revolves around empowering students with practical skills and a strong ethical compass, particularly in the realm of technology...",
      "llm_provider": "ollama",
      "llm_model": "llama3:8b-instruct",
      "generation_time_seconds": 5.32,
      "error": null // or error message string if generation failed
    }
    ```

## Troubleshooting (Brief Notes)

*   **`ModuleNotFoundError`:** Ensure all required libraries (e.g., `python-dotenv`, `ollama`, `openai`, `dashscope`) are installed in your Python environment.
*   **API Key Errors:** Double-check that your `.env` file is correctly formatted, populated with valid API keys, and is in the project root. Ensure `llm_interface.py` is using the correct environment variable names for the intended providers.
*   **Ollama Connection Errors:**
    *   Verify the Ollama application/service is running.
    *   Confirm the model specified (e.g., `llama3:8b-instruct`) has been downloaded (`ollama list`).
    *   Check if `OLLAMA_HOST` environment variable needs to be set if Ollama is running on a different host/port (not typically needed for local default installs).
*   **"Unsupported LLM provider"**: This means the `provider` argument passed to `main_generator.py` (or derived from `config.DEFAULT_MODEL`) doesn't have a corresponding handler in `llm_interface.generate_response()`.
*   **Permissions Issues:** Ensure the script has write permissions for the `outputs/` directory (and its subdirectories) and the log file.

## Refinement and Prompt Engineering

The quality of the generated teacher agent responses heavily depends on:
1.  **Persona Detail:** Richer, more specific personas lead to more nuanced agent behavior. Leverage the **optional persona columns** (like `tone_keywords`, `communication_style`, etc.) in `personas.csv` to provide deep contextual information.
2.  **Task Wording:** Clear and unambiguous questions/tasks yield better responses.
3.  **System Prompt Construction:** The `construct_system_prompt()` function in `main_generator.py` dynamically incorporates both required and optional persona attributes. Experiment with different ways to phrase the content within your `personas.csv` (especially the optional fields and `teaching_plan`) to guide the LLM's responses more effectively.
4.  **LLM Choice & Parameters:** Different models and temperature settings will produce varied results. Test and iterate.

It's recommended to start with a small set of personas and tasks, analyze the output, refine your prompts and persona details (including the new optional fields), and then scale up.
