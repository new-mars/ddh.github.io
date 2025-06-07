# teacher_agent_generator/scripts/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")

# LLM Configuration
DEFAULT_MODEL = "gpt-4-turbo" # Example, can be changed
DEFAULT_TEMPERATURE = 0.7
MAX_TOKENS = 1500

# File Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

PERSONAS_FILE = os.path.join(DATA_DIR, "personas.csv")
QUESTIONS_FILE = os.path.join(DATA_DIR, "questions.txt")
QUESTIONNAIRE_FILE = os.path.join(DATA_DIR, "questionnaire.json")

GENERATED_AGENTS_DIR = os.path.join(OUTPUT_DIR, "generated_agents")
LOG_FILE = os.path.join(OUTPUT_DIR, "generation.log")

# Ensure output directories exist
os.makedirs(GENERATED_AGENTS_DIR, exist_ok=True)

# Other configurations
LOG_LEVEL = "INFO"

# --- Optional Persona CSV Columns for Enhanced Specificity ---
# The following columns can be optionally added to your personas.csv file to provide
# more detailed instructions for the LLM on how to embody each persona.
# If present, main_generator.py (once updated) will use them to construct more nuanced system prompts.
# - tone_keywords: (e.g., "formal, academic, precise", "warm, encouraging, patient")
# - communication_style: (e.g., "prefers analogies", "often uses rhetorical questions")
# - key_terminology: (e.g., "pedagogy, constructivism" - key terms persona might use)
# - role_specific_directives: (e.g., "As a historian, always try to contextualize answers...")
# - example_phrase: (e.g., "In my considered view...", "Alright team, let's explore...")
# See README.md for more details on how to use these (once README is updated).
