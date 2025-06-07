# teacher_agent_generator/scripts/main_translator_mtpe.py
import argparse
import datetime
import json
import logging
import os
import time
import pandas as pd # For pd.isna() if used by imported modules

# If this script is run directly, add its directory and project root to sys.path
if __name__ == '__main__' and __package__ is None:
    import sys
    _CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    if _CURRENT_SCRIPT_DIR not in sys.path:
        sys.path.insert(0, _CURRENT_SCRIPT_DIR)
    _PROJECT_ROOT = os.path.dirname(_CURRENT_SCRIPT_DIR)
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

# Custom module imports
import config
import persona_loader
import llm_interface
import task_loader
from main_generator import construct_translator_system_prompt # Import from existing main_generator

# Global logger instance
logger = logging.getLogger(__name__)

def setup_translator_arg_parser():
    """Sets up the command-line argument parser for the MTPE translator agent generator."""
    parser = argparse.ArgumentParser(description="Generate MTPE agent responses based on translator personas.")

    # File paths
    parser.add_argument("--translator_personas_file", type=str,
                        default=config.DEFAULT_TRANSLATOR_PERSONAS_CSV_PATH,
                        help="Path to translator personas CSV file.")
    parser.add_argument("--mtpe_tasks_file", type=str,
                        default=config.DEFAULT_MTPE_TASKS_PATH,
                        help="Path to MTPE tasks JSONL file.")
    parser.add_argument("--output_dir", type=str,
                        default=config.GENERATED_AGENTS_DIR, # Re-use existing output dir
                        help="Directory to save generated MTPE agent data.")

    # LLM settings
    parser.add_argument("--provider", type=str,
                        help="LLM provider (e.g., 'ollama', 'qwen', 'deepseek'). Overrides config.DEFAULT_MODEL's provider part.")
    parser.add_argument("--model_name", type=str,
                        help="LLM model name (e.g., 'llama3:8b-instruct', 'qwen-turbo'). Overrides config.DEFAULT_MODEL's model part.")
    parser.add_argument("--temperature", type=float,
                        help="Generation temperature. Overrides config.DEFAULT_TEMPERATURE.")
    parser.add_argument("--max_tokens", type=int,
                        help="Max tokens for generation. Overrides config.MAX_TOKENS.")

    # Processing controls
    parser.add_argument("--limit_personas", type=int, default=0,
                        help="Limit the number of personas to process (0 for all).")
    parser.add_argument("--limit_tasks", type=int, default=0,
                        help="Limit the number of MTPE tasks per persona to process (0 for all).")

    parser.add_argument("--log_level", type=str,
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        default=config.LOG_LEVEL,
                        help="Logging level.")
    return parser.parse_args()

def configure_translator_logging(log_level_str, log_file_path):
    """Configures console and file logging for the translator script."""
    # This is similar to configure_logging in main_generator.py
    # Adapting for potential separate log file or behavior if needed.
    # For now, keeps it consistent.
    numeric_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # Ensure this logger is specifically configured or use root.
    # Using root configuration for simplicity, assuming one main process.
    # If running simultaneously, might need separate log files.
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    logger.setLevel(numeric_level) # Configure this specific logger

    if log_file_path:
        log_file_dir = os.path.dirname(log_file_path)
        if log_file_dir and not os.path.exists(log_file_dir):
            os.makedirs(log_file_dir, exist_ok=True)

        file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        # Avoid duplicate handlers if this function or basicConfig is called multiple times
        if not any(isinstance(h, logging.FileHandler) and h.baseFilename == file_handler.baseFilename for h in logger.handlers):
            logger.addHandler(file_handler)

    logger.info(f"Translator MTPE logging configured. Level: {log_level_str}, File: {log_file_path}")


def main_translator():
    args = setup_translator_arg_parser()

    # Determine LLM settings, using CLI args if provided, else config defaults
    provider = args.provider
    model_name = args.model_name
    if not provider and ':' in config.DEFAULT_MODEL: # If provider not set, parse from DEFAULT_MODEL
        provider = config.DEFAULT_MODEL.split(':')[0]
    if not model_name and ':' in config.DEFAULT_MODEL: # If model_name not set, parse from DEFAULT_MODEL
        model_name = config.DEFAULT_MODEL.split(':')[-1]
    if not provider: # Fallback if DEFAULT_MODEL isn't in provider:model format
        provider = 'openai' # A generic fallback, or handle error
    if not model_name:
        model_name = config.DEFAULT_MODEL # Use full name if not parsed

    temperature = args.temperature if args.temperature is not None else config.DEFAULT_TEMPERATURE
    max_tokens = args.max_tokens if args.max_tokens is not None else config.MAX_TOKENS

    # Use a potentially different log file for translator outputs, or append to the main one
    # For now, using the same config.LOG_FILE.
    # A more sophisticated setup might use: translator_log_file = os.path.join(config.OUTPUT_DIR, "translator_generation.log")
    configure_translator_logging(args.log_level, config.LOG_FILE)

    logger.info("--- Starting Translator MTPE Agent Generation Process ---")
    logger.debug(f"CLI Arguments: {args}")
    logger.info(f"Effective LLM settings: Provider={provider}, Model={model_name}, Temp={temperature}, MaxTokens={max_tokens}")

    # Load translator personas
    logger.info(f"Loading translator personas from: {args.translator_personas_file}")
    translator_personas = persona_loader.load_translator_personas(args.translator_personas_file)
    if not translator_personas:
        logger.error("No translator personas loaded. Exiting.")
        return

    # Load MTPE tasks
    logger.info(f"Loading MTPE tasks from: {args.mtpe_tasks_file}")
    tasks_data = task_loader.load_all_tasks(mtpe_tasks_path=args.mtpe_tasks_file, questions_path=None, questionnaire_path=None)
    mtpe_tasks = tasks_data.get("mtpe_tasks", [])
    if not mtpe_tasks:
        logger.error("No MTPE tasks loaded. Exiting.")
        return

    # Apply limits
    if args.limit_personas > 0:
        translator_personas = translator_personas[:args.limit_personas]
        logger.info(f"Limited processing to {len(translator_personas)} personas.")

    logger.info(f"Loaded {len(translator_personas)} translator personas and {len(mtpe_tasks)} MTPE tasks.")

    all_mtpe_results = []
    total_expected_generations = len(translator_personas) * (len(mtpe_tasks) if args.limit_tasks == 0 else min(args.limit_tasks, len(mtpe_tasks)))
    current_generation_count = 0

    for i, persona in enumerate(translator_personas):
        persona_id = persona.get('persona_id', f"persona_index_{i}")
        persona_name = persona.get('persona_name', 'Unknown Translator Persona')
        logger.info(f"Processing Persona ID: {persona_id} ({persona_name}) ({i+1}/{len(translator_personas)})")

        system_prompt = construct_translator_system_prompt(persona)

        tasks_for_this_persona = mtpe_tasks
        if args.limit_tasks > 0:
            tasks_for_this_persona = mtpe_tasks[:args.limit_tasks]
            logger.info(f"  Limiting tasks to {len(tasks_for_this_persona)} for this persona.")

        for j, task in enumerate(tasks_for_this_persona):
            current_generation_count += 1
            task_id = task.get('task_id', f"task_index_{j}")
            source_text_ch = task.get('source_text_ch', '')
            machine_translation_en = task.get('machine_translation_en', '')

            logger.info(f"  Processing MTPE Task ID: {task_id} ({j+1}/{len(tasks_for_this_persona)}) for Persona ID: {persona_id} (Overall: {current_generation_count}/{total_expected_generations})")
            logger.debug(f"    Persona Details: {persona}")
            logger.debug(f"    Task Details: {task}")
            # logger.debug(f"    System Prompt: {system_prompt}") # Can be very long

            user_prompt = (
                f"Chinese Source Text:\n{source_text_ch}\n\n"
                f"English Machine Translation (to be post-edited):\n{machine_translation_en}"
            )
            logger.debug(f"    User Prompt (MTPE inputs):\n{user_prompt}")

            llm_response_raw = None
            llm_response_parsed = None
            generation_error = None
            duration = 0.0

            start_time = time.time()
            try:
                llm_response_raw = llm_interface.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    provider=provider,
                    model_name=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens # Ensure this is adequate for JSON + TAP
                )
                duration = time.time() - start_time

                if llm_response_raw:
                    logger.info(f"    LLM call completed in {duration:.2f}s. Attempting to parse JSON response.")
                    logger.debug(f"    Raw LLM Response String: {llm_response_raw[:500]}...") # Log snippet
                    try:
                        # The LLM is instructed to return a single JSON string.
                        # Sometimes, models might wrap it in backticks or add explanations.
                        # Basic cleanup:
                        cleaned_response_str = llm_response_raw.strip()
                        if cleaned_response_str.startswith("```json"):
                            cleaned_response_str = cleaned_response_str[7:]
                        if cleaned_response_str.endswith("```"):
                            cleaned_response_str = cleaned_response_str[:-3]
                        cleaned_response_str = cleaned_response_str.strip()

                        llm_response_parsed = json.loads(cleaned_response_str)
                        logger.info("    Successfully parsed LLM JSON response.")
                    except json.JSONDecodeError as jde:
                        logger.error(f"    Failed to parse JSON from LLM response: {jde}")
                        logger.debug(f"    Full Raw LLM Response causing JSON error: {llm_response_raw}")
                        generation_error = f"JSONDecodeError: {jde}. Raw response logged."
                        # Keep llm_response_raw for inspection
                else:
                    generation_error = "No content returned from LLM provider (see LLM interface logs for specific error)."
                    logger.warning(f"    {generation_error} for Persona ID: {persona_id}, Task ID: {task_id}. LLM call took {duration:.2f}s.")

            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"    Exception during LLM call for Persona ID: {persona_id}, Task ID: {task_id}: {e}", exc_info=True)
                generation_error = str(e)

            result_record = {
                "persona_id": persona_id,
                "persona_name": persona_name,
                "task_id": task_id,
                "source_text_ch": source_text_ch,
                "machine_translation_en": machine_translation_en,
                "domain": task.get("domain"),
                "difficulty_level": task.get("difficulty_level"),
                "llm_provider": provider,
                "llm_model": model_name,
                "system_prompt_hash": hash(system_prompt), # To save space, log full prompt separately if needed
                "generation_timestamp_utc": datetime.datetime.utcnow().isoformat(),
                "generation_time_seconds": round(duration, 2),
                "generation_error": generation_error,
                "llm_response_raw_text": llm_response_raw, # Store raw text
            }
            if llm_response_parsed: # Add parsed fields if successful
                result_record.update(llm_response_parsed)

            all_mtpe_results.append(result_record)

            # Optional delay
            # time.sleep(1)

    # Save all generated MTPE data
    if all_mtpe_results:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"generated_translator_mtpe_results_{timestamp}.jsonl"
        output_filepath = os.path.join(args.output_dir, output_filename)

        try:
            os.makedirs(args.output_dir, exist_ok=True)
            with open(output_filepath, 'w', encoding='utf-8') as f_out:
                for entry in all_mtpe_results:
                    f_out.write(json.dumps(entry) + '\n')
            logger.info(f"Successfully saved {len(all_mtpe_results)} MTPE results to {output_filepath}")
        except Exception as e:
            logger.error(f"Failed to save MTPE results to {output_filepath}: {e}", exc_info=True)
    else:
        logger.warning("No MTPE data was generated to save.")

    logger.info("--- Translator MTPE Agent Generation Process Finished ---")

if __name__ == '__main__':
    # Pandas check (mainly for pd.isna() in construct_translator_system_prompt)
    try:
        import pandas
        logger.debug("Pandas library found.")
    except ImportError:
        # This is not a critical error if persona_loader doesn't use pandas for CSV reading
        # and if NaN values are not expected in a way that breaks string conversion.
        # construct_translator_system_prompt uses pd.isna, so it's a dependency.
        print("CRITICAL ERROR: Pandas library not found, but it is required for this script (e.g., for pd.isna()). Please install it.")
        logger.critical("Pandas library not found, but it is required. Exiting.")
        sys.exit(1) # Exit if pandas is missing, as it's used in imported function

    main_translator()
