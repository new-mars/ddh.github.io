# teacher_agent_generator/scripts/main_generator.py
import argparse
import datetime
import json
import logging
import os
import time
import pandas as pd # Added for pd.isna()

# If this script is run directly, add its directory to sys.path
# to allow direct import of local modules.
if __name__ == '__main__' and __package__ is None: # __package__ check is more robust
    import sys
    _CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    if _CURRENT_SCRIPT_DIR not in sys.path:
        sys.path.insert(0, _CURRENT_SCRIPT_DIR)
    # Also add project root to sys.path if not already there for broader imports
    _PROJECT_ROOT = os.path.dirname(_CURRENT_SCRIPT_DIR)
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

# Now local modules can be imported
import config
import persona_loader
import llm_interface
import task_loader

# Global logger instance (will be configured in main)
logger = logging.getLogger(__name__)

def setup_arg_parser():
    """Sets up the command-line argument parser."""
    parser = argparse.ArgumentParser(description="Generate teacher agent profiles and responses.")
    parser.add_argument("--provider", type=str, help="LLM provider (e.g., 'ollama', 'qwen', 'deepseek')", default=None)
    parser.add_argument("--model", type=str, help="LLM model name (e.g., 'llama2', 'qwen-turbo', 'deepseek-chat')", default=None)
    parser.add_argument("--temperature", type=float, help="Generation temperature", default=None)
    parser.add_argument("--max_tokens", type=int, help="Max tokens for generation", default=None)
    parser.add_argument("--personas_file", type=str, help="Path to personas CSV file", default=config.PERSONAS_FILE)
    parser.add_argument("--questions_file", type=str, help="Path to open-ended questions text file", default=config.QUESTIONS_FILE)
    parser.add_argument("--questionnaire_file", type=str, help="Path to questionnaire JSON file", default=config.QUESTIONNAIRE_FILE)
    parser.add_argument("--output_dir", type=str, help="Directory to save generated agent data", default=config.GENERATED_AGENTS_DIR)
    parser.add_argument("--log_level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default=config.LOG_LEVEL)
    return parser.parse_args()

def configure_logging(log_level_str, log_file_path):
    """Configures console and file logging."""
    numeric_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # Basic config for the root logger (affects all loggers)
    # Ensure this is only called once, or guard it.
    # For simplicity here, we assume this is the main configuration point.
    if not logging.getLogger().hasHandlers(): # Configure root logger only if no handlers exist
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Specific configuration for this script's logger
    logger.setLevel(numeric_level)

    # Console Handler (if not already configured by basicConfig)
    # basicConfig adds a StreamHandler by default. We can customize it or add another.
    # For now, basicConfig handles console. If more control is needed, add specific handlers.

    # File Handler
    if log_file_path:
        # Ensure the directory for the log file exists
        log_file_dir = os.path.dirname(log_file_path)
        if log_file_dir and not os.path.exists(log_file_dir):
            os.makedirs(log_file_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler) # Add to specific logger, not root, to avoid duplicate console logs from root
        # If basicConfig was used, root logger also has handlers.
        # To avoid duplicate file logs if this script is run multiple times or modules also log:
        # Clear existing handlers for this specific logger if needed:
        # logger.handlers = [h for h in logger.handlers if not isinstance(h, logging.FileHandler)]
        # Or ensure this configuration happens once.
        # For this script, adding to its own logger should be fine.

    logger.info(f"Logging configured. Level: {log_level_str}, File: {log_file_path}")


def construct_system_prompt(persona: dict) -> str:
    """
    Constructs a detailed system prompt based on the persona, including optional attributes.
    """
    prompt_parts = []

    # Basic persona information
    name = str(persona.get('name', 'a teacher')).strip()
    title = str(persona.get('title', 'an educator')).strip()
    gender = str(persona.get('gender', 'not specified')).strip()
    experience_years = persona.get('teaching_experience_years', 'some') # Already int or string "some"
    professional_background = str(persona.get('professional_background', 'various roles in education')).strip()

    prompt_parts.append(f"You are {name}, {title}.")
    if gender and gender.lower() != 'not specified':
        prompt_parts.append(f"You identify as {gender}.")
    prompt_parts.append(f"You have {experience_years} years of teaching experience.")
    if professional_background:
        prompt_parts.append(f"Your professional background includes: {professional_background}.")

    # Optional attributes for nuanced persona definition
    optional_attributes_map = {
        "tone_keywords": "Your communication tone should be generally: {}.",
        "communication_style": "Your communication style includes: {}.",
        "key_terminology": "You often use key terminology such as: {}.",
        "example_phrase": "You might start some responses with a phrase like: \"{}\".", # Note: curly braces escaped for f-string if value has them. Here, value is inserted.
        "role_specific_directives": "{}" # This one is a direct directive
    }

    for key, format_string in optional_attributes_map.items():
        value = persona.get(key)
        # Check if value is not None, not NaN (if from pandas), and not an empty/whitespace string
        if value is not None and not (isinstance(value, float) and pd.isna(value)) and str(value).strip():
            cleaned_value = str(value).strip()
            prompt_parts.append(format_string.format(cleaned_value))

    # Teaching plan (handle if missing or empty)
    teaching_plan_raw = persona.get('teaching_plan')
    teaching_plan = ''
    if teaching_plan_raw is not None and not (isinstance(teaching_plan_raw, float) and pd.isna(teaching_plan_raw)):
        teaching_plan = str(teaching_plan_raw).strip()

    if teaching_plan:
        prompt_parts.append(f"Your teaching plan emphasizes: {teaching_plan}.")
    else:
        prompt_parts.append("You have a teaching plan focused on student engagement and success.") # Default if empty

    # General instruction
    prompt_parts.append("Please respond to the following question or task from this perspective, fully embodying this persona in your language, tone, and focus.")

    return "\n".join(prompt_parts)

def construct_translator_system_prompt(persona: dict) -> str:
    """
    Constructs a detailed system prompt for a Translator Persona for MTPE tasks.
    """
    prompt_parts = []

    # Core Identity
    name = str(persona.get('persona_name', 'a professional translator')).strip()
    native_lang = str(persona.get('native_language', 'not specified')).strip()
    education = str(persona.get('education_level', 'not specified')).strip()
    major = str(persona.get('major_subject', 'not specified')).strip()

    prompt_parts.append(f"You are {name}, a professional translator.")
    prompt_parts.append(f"Your native language is {native_lang}.")
    if education.lower() != 'not specified':
        prompt_parts.append(f"You hold a {education} in {major}.")

    # Experience and Skills
    adj_exp = persona.get('translation_experience_years_adjusted', 0.0)
    skill_level = str(persona.get('translation_skill_level', 'Junior')).strip() # Default to Junior
    cat_tools_raw = persona.get('cat_tool_familiarity')
    cat_tools = str(cat_tools_raw).strip() if cat_tools_raw and not (isinstance(cat_tools_raw, float) and pd.isna(cat_tools_raw)) else "not specified"

    prompt_parts.append(f"You have {adj_exp:.1f} years of adjusted professional translation experience, and your skill level is considered {skill_level}.")
    if cat_tools.lower() != 'not specified':
        prompt_parts.append(f"You are familiar with CAT tools such as: {cat_tools}.")
    else:
        prompt_parts.append("You may or may not be familiar with specific CAT tools.")

    # English Proficiency & Linguistic Style Simulation (if Chinese native speaker translating to English)
    # This section needs to be adapted if the translation direction changes.
    # Current assumption: CH -> EN translation task.
    eng_prof_score_raw = persona.get('english_proficiency_score')
    eng_prof_score = None
    is_native_english = native_lang.lower().startswith('english')

    if not is_native_english:
        try:
            eng_prof_score = float(eng_prof_score_raw) # Assuming score is out of 100 for this logic
            # Example: IELTS scores are 0-9. TOEFL 0-120. Let's assume a generic 0-100 scale for this example.
            # This part MUST be adapted based on the actual scale of 'english_proficiency_score'.
            # For this example, let's imagine it's a percentile or a score where <85 and <100 are meaningful.
            # This logic is highly dependent on the specific meaning of 'english_proficiency_score'.
            # IF THE SCORE IS IELTS (0-9), then thresholds need to be e.g. <7.0, <8.0 etc.
            # The sample data has scores like 7.5, 8.0 - these look like IELTS. Let's use that.
            # IELTS 7.0 (Competent), 8.0 (Very Good), 9.0 (Expert)

            # Let's adjust for IELTS-like scores (0-9 scale)
            if eng_prof_score < 7.0: # e.g., below "Competent User"
                 prompt_parts.append("Your English proficiency is good, but not native. You might occasionally make minor grammatical errors or choose slightly unnatural phrasing typical of a non-native speaker at your proficiency level (e.g., issues with articles, prepositions, or complex sentence structures). Please subtly reflect this in your post-edited output if appropriate for realism, but prioritize clarity and accuracy.")
            elif eng_prof_score < 8.0: # e.g., "Good User" up to "Very Good User"
                 prompt_parts.append("Your English proficiency is very good. While generally accurate and fluent, your phrasing might sometimes lack full idiomatic naturalness compared to a native speaker. Aim for high-quality, natural-sounding English, but slight non-native patterns are acceptable if they occur organically.")
            else: # 8.0 and above
                 prompt_parts.append("Your English proficiency is excellent, near-native or native-like. Your post-edited output should reflect a high command of English, with natural and idiomatic phrasing.")

        except (ValueError, TypeError):
            if eng_prof_score_raw and str(eng_prof_score_raw).strip().lower() not in ['n/a', 'na', 'native', 'n/a (native speaker)']:
                prompt_parts.append(f"Your English proficiency score is '{eng_prof_score_raw}'. Interpret this score appropriately to reflect language quality in your output.")
            elif not eng_prof_score_raw:
                 prompt_parts.append("Your English proficiency is not specified. Assume a professional working proficiency.")
    else: # Native English speaker
        prompt_parts.append("You are a native English speaker. Your English output should be of native quality, fluent, and idiomatic.")

    # Linguistic Traits and Style
    common_traits_raw = persona.get('common_linguistic_traits')
    common_traits = str(common_traits_raw).strip() if common_traits_raw and not (isinstance(common_traits_raw, float) and pd.isna(common_traits_raw)) else ""
    if common_traits:
        prompt_parts.append(f"Your known linguistic traits include: {common_traits}.")

    sample_source_exists = persona.get('sample_source_text_ch') and not (isinstance(persona.get('sample_source_text_ch'), float) and pd.isna(persona.get('sample_source_text_ch'))) and "[Chinese Source Sample" not in str(persona.get('sample_source_text_ch'))
    sample_translation_exists = persona.get('sample_translation_en') and not (isinstance(persona.get('sample_translation_en'), float) and pd.isna(persona.get('sample_translation_en'))) and "[English Translation Sample" not in str(persona.get('sample_translation_en'))

    if sample_source_exists and sample_translation_exists:
        prompt_parts.append("Strive for consistency with the style demonstrated in your provided sample translation (details of which are not directly shown here but assume you know your style).")
    else:
        prompt_parts.append("Translate and post-edit according to your described linguistic traits and professional standards.")

    # MTPE Task Instructions
    prompt_parts.append("\n--- MTPE Task Instructions ---")
    prompt_parts.append("You will be given a Chinese source text and its corresponding English machine translation (MT). Your task is to:")
    prompt_parts.append("1.  **Post-edit** the English machine translation to produce a high-quality, accurate, fluent, and natural-sounding English translation that reflects your persona's skill level and linguistic style. The post-edited text should be ready for publication or use in a professional context, correcting all errors in the MT.")
    prompt_parts.append("2.  **Produce a Think Aloud Protocol (TAP)**: While you perform the post-editing, verbalize your thought process. This should include identifying issues in the MT, explaining your correction strategies, and noting any challenges or interesting linguistic points. Be detailed and specific.")
    prompt_parts.append("3.  **Estimate Post-Editing Time**: Provide an estimated time in minutes that it would take you to complete the post-editing for this segment.")
    prompt_parts.append("4.  **Rate Perceived MT Quality**: On a scale of 1 (Very Poor) to 5 (Very Good), rate the quality of the original machine translation *before* your edits.")
    prompt_parts.append("5.  **Rate Confidence in MTPE Output**: On a scale of 1 (Not Confident) to 5 (Very Confident), rate your confidence in the quality and accuracy of *your own* final post-edited translation.")
    prompt_parts.append("6.  **Identify Simulated Edit Categories**: List up to three primary categories of edits you made (e.g., 'Grammar', 'Terminology', 'Style', 'Fluency', 'Mistranslation', 'Omission', 'Addition').")
    prompt_parts.append("7.  **Linguistic Error Simulation Notes** (If applicable based on your English proficiency): Briefly note if you intentionally introduced or retained any minor non-native patterns as per your persona's proficiency level. If native or high proficiency, this might be 'N/A'.")

    # Output Format Requirement
    prompt_parts.append("\n--- Output Format Requirement ---")
    prompt_parts.append("Your entire response MUST be a single, valid JSON object string. Do NOT include any text outside of this JSON object. The JSON object must have the following fields:")
    prompt_parts.append("- `mtpe_output_en` (string): Your final post-edited English translation.")
    prompt_parts.append("- `think_aloud_protocol` (string): Your detailed think-aloud protocol.")
    prompt_parts.append("- `estimated_time_minutes` (integer): Your time estimate in minutes.")
    prompt_parts.append("- `perceived_mt_quality_rating` (integer, 1-5): Your rating of the original MT quality.")
    prompt_parts.append("- `confidence_rating_of_mtpe_output` (integer, 1-5): Your confidence in your MTPE output.")
    prompt_parts.append("- `simulated_edit_categories` (list of strings): Up to three main edit categories.")
    prompt_parts.append("- `linguistic_error_simulation_notes` (string): Notes on any simulated linguistic errors, or 'N/A'.")
    prompt_parts.append("\nExample of the required JSON output structure string (DO NOT include markdown backticks in your actual response):")
    prompt_parts.append("```json")
    prompt_parts.append("{")
    prompt_parts.append("  \"mtpe_output_en\": \"This is the final, high-quality English translation after post-editing...\",")
    prompt_parts.append("  \"think_aloud_protocol\": \"First, I noticed the term '...' was mistranslated in the MT as '...'. I corrected it to '...'. Then, the sentence structure '...' was awkward, so I rephrased it to '...'. I also corrected a grammatical error related to subject-verb agreement...\",")
    prompt_parts.append("  \"estimated_time_minutes\": 15,")
    prompt_parts.append("  \"perceived_mt_quality_rating\": 3,")
    prompt_parts.append("  \"confidence_rating_of_mtpe_output\": 5,")
    prompt_parts.append("  \"simulated_edit_categories\": [\"Terminology\", \"Fluency\", \"Grammar\"],")
    prompt_parts.append("  \"linguistic_error_simulation_notes\": \"As a non-native speaker with a score of 7.5, I allowed a minor prepositional choice that might not be the most common but is understandable, to reflect subtle non-native patterns.\"`")
    prompt_parts.append("}")
    prompt_parts.append("```")

    return "\n\n".join(prompt_parts) # Use double newline for better readability of the final prompt

def main():
    args = setup_arg_parser()

    # Use config defaults if CLI args are not provided
    provider = args.provider if args.provider else (config.DEFAULT_MODEL.split(':')[0] if ':' in config.DEFAULT_MODEL else 'openai')
    model_name = args.model if args.model else (config.DEFAULT_MODEL.split(':')[-1] if ':' in config.DEFAULT_MODEL else config.DEFAULT_MODEL)
    temperature = args.temperature if args.temperature is not None else config.DEFAULT_TEMPERATURE
    max_tokens = args.max_tokens if args.max_tokens is not None else config.MAX_TOKENS

    # Setup logging (using the global logger instance)
    # The log file path comes from config.py by default, can be overridden if needed
    # For now, config.LOG_FILE is used.
    configure_logging(args.log_level, config.LOG_FILE)

    logger.info("Starting Teacher Agent Generation Process")
    logger.debug(f"CLI Arguments: {args}")
    logger.debug(f"Effective LLM settings: Provider={provider}, Model={model_name}, Temp={temperature}, MaxTokens={max_tokens}")

    # Load personas
    logger.info(f"Loading personas from: {args.personas_file}")
    personas = persona_loader.load_personas(args.personas_file)
    if not personas:
        logger.error("No personas loaded. Exiting.")
        return

    # Load tasks
    logger.info(f"Loading tasks from: {args.questions_file} and {args.questionnaire_file}")
    tasks_data = task_loader.load_all_tasks(args.questions_file, args.questionnaire_file)
    all_task_items = tasks_data["open_ended_questions"] + tasks_data["questionnaire_items"]
    if not all_task_items:
        logger.error("No tasks loaded. Exiting.")
        return

    logger.info(f"Loaded {len(personas)} personas and {len(all_task_items)} total tasks.")

    all_generated_data = []
    total_generations = len(personas) * len(all_task_items)
    current_generation_count = 0

    for i, persona in enumerate(personas):
        logger.info(f"Processing persona {i+1}/{len(personas)}: {persona.get('name', 'Unknown Persona')}")
        system_prompt_for_persona = construct_system_prompt(persona)

        for j, task in enumerate(all_task_items):
            current_generation_count += 1
            task_text = task.get("text", "No task text provided.")
            task_type = task.get("type", "unknown_task_type")
            task_id = task.get("id", f"task_{j}") # Use 'id' if available (from questionnaire), else generate one

            logger.info(f"  Processing task {j+1}/{len(all_task_items)} for persona {persona.get('name', 'Unknown Persona')} (Overall: {current_generation_count}/{total_generations})")
            logger.debug(f"    Persona: {persona}")
            logger.debug(f"    Task: {task}")
            logger.debug(f"    System Prompt: {system_prompt_for_persona}")
            logger.debug(f"    User Prompt (Task Text): {task_text}")

            # The user prompt is essentially the task text itself.
            user_prompt_for_llm = task_text

            # The user prompt is essentially the task text itself.
            user_prompt_for_llm = task_text

            response_content = None  # Initialize
            llm_error_message = None # Initialize
            duration = 0.0

            start_time = time.time()
            try:
                temp_response_content = llm_interface.generate_response(
                    system_prompt=system_prompt_for_persona,
                    user_prompt=user_prompt_for_llm,
                    provider=provider,
                    model_name=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                duration = time.time() - start_time # Capture duration for successful or no-content responses

                if temp_response_content:
                    response_content = temp_response_content
                    logger.info(f"    LLM call successfully completed in {duration:.2f} seconds (received content).")
                    logger.debug(f"    Raw LLM Response: {response_content[:100]}...")
                else:
                    # No exception in this script, but llm_interface returned None
                    llm_error_message = "No content returned from LLM provider (see LLM interface logs for specific error)."
                    logger.warning(f"    {llm_error_message} for persona '{persona.get('name')}' and task '{task_text[:50]}...'. LLM call took {duration:.2f}s.")

            except Exception as e:
                duration = time.time() - start_time # Capture duration even if exception occurs early
                logger.error(f"    Exception during LLM call for persona '{persona.get('name')}' and task '{task_text[:50]}...': {e}", exc_info=True)
                llm_error_message = str(e) # Capture str(e) from the exception

            # Common append operation for all outcomes (success, no content, exception)
            all_generated_data.append({
                "persona_name": persona.get("name"),
                "persona_details": persona,
                "task_id": task_id,
                "task_type": task_type,
                "task_text": task_text,
                "system_prompt": system_prompt_for_persona,
                "user_prompt": user_prompt_for_llm,
                "llm_response": response_content, # Will be None if error or no content from LLM
                "llm_provider": provider,
                "llm_model": model_name,
                "generation_time_seconds": duration,
                "error": llm_error_message # Contains str(e) or the "no content from provider" message, or None if successful
            })

            # Optional: Add a small delay to avoid hitting rate limits if any
            # time.sleep(1)

    # Save all generated data
    if all_generated_data:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"generated_teacher_agents_{timestamp}.jsonl"
        output_filepath = os.path.join(args.output_dir, output_filename)

        try:
            # Ensure output directory exists (config.py also tries, but good to double check here)
            os.makedirs(args.output_dir, exist_ok=True)

            with open(output_filepath, 'w', encoding='utf-8') as f_out:
                for entry in all_generated_data:
                    f_out.write(json.dumps(entry) + '\n')
            logger.info(f"Successfully saved {len(all_generated_data)} generated entries to {output_filepath}")
        except Exception as e:
            logger.error(f"Failed to save generated data to {output_filepath}: {e}", exc_info=True)
    else:
        logger.warning("No data was generated to save.")

    logger.info("Teacher Agent Generation Process Finished.")

if __name__ == '__main__':
    # --- Pandas Check (Placeholder) ---
    # The persona_loader.py currently uses the 'csv' module, not pandas.
    # If pandas were a requirement for persona_loader or other parts, this check would be relevant.
    try:
        import pandas
        PANDAS_AVAILABLE = True
    except ImportError:
        PANDAS_AVAILABLE = False
        print("WARNING: Pandas library not found. If CSV processing relies on it, errors may occur.")
        # Potentially log this warning too, if logging is configured before this point.
        # However, logger is configured in main(). For a startup check, print is fine.

    # if not PANDAS_AVAILABLE and "persona_loader_uses_pandas": # Example condition
    #     print("Critical Error: Pandas is required for persona loading but not installed. Exiting.")
    #     sys.exit(1)

    main()
