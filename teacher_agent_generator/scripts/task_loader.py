# teacher_agent_generator/scripts/task_loader.py
import json
import logging
import os

# If this script is run directly, add its directory to sys.path
# to allow direct import of 'config' from the same directory.
if __name__ == '__main__':
    import sys
    _CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    if _CURRENT_SCRIPT_DIR not in sys.path:
        sys.path.insert(0, _CURRENT_SCRIPT_DIR)

import config

# Configure basic logging (consistent with other modules)
logging.basicConfig(level=config.LOG_LEVEL.upper() if hasattr(config, 'LOG_LEVEL') else logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
                    filename=config.LOG_FILE if hasattr(config, 'LOG_FILE') else None,
                    filemode='a')

# Define required fields for MTPE tasks for basic validation
MTPE_TASK_REQUIRED_FIELDS = ["task_id", "source_text_ch", "machine_translation_en"]

def _load_open_ended_questions(file_path=config.QUESTIONS_FILE):
    """Loads open-ended questions from a text file."""
    if not file_path: # Handle None path
        logging.info("Open-ended questions path not provided. Skipping loading.")
        return []
    questions = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'): # Ignore empty lines and comments
                    questions.append({"type": "open_ended", "text": line})
        logging.info(f"Successfully loaded {len(questions)} open-ended questions from {file_path}.")
        return questions
    except FileNotFoundError:
        logging.error(f"Open-ended questions file not found: {file_path}")
        return []
    except Exception as e:
        logging.error(f"Error loading open-ended questions from {file_path}: {e}")
        return []

def _load_questionnaire_items(file_path=config.QUESTIONNAIRE_FILE):
    """Loads questionnaire items from a JSON file."""
    if not file_path: # Handle None path
        logging.info("Questionnaire file path not provided. Skipping loading.")
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        if not isinstance(items, list):
            logging.error(f"Questionnaire file {file_path} does not contain a valid JSON list.")
            return []

        # Basic validation for expected keys in each item (optional but good practice)
        for item in items:
            if not isinstance(item, dict) or "id" not in item or "text" not in item or "type" not in item:
                logging.warning(f"Invalid item structure in {file_path}: {item}. Skipping.")
                # Decide whether to skip item or entire file. For now, skip item.
        valid_items = [item for item in items if isinstance(item, dict) and "id" in item and "text" in item and "type" in item]

        logging.info(f"Successfully loaded {len(valid_items)} questionnaire items from {file_path}.")
        return valid_items
    except FileNotFoundError:
        logging.error(f"Questionnaire file not found: {file_path}")
        return []
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from questionnaire file: {file_path}")
        return []
    except Exception as e:
        logging.error(f"Error loading questionnaire items from {file_path}: {e}")
        return []

def _load_mtpe_tasks(file_path: str) -> list[dict]:
    """Loads MTPE tasks from a JSONL file."""
    if not file_path or not os.path.exists(file_path):
        logging.info(f"MTPE tasks file not found or path not configured: {file_path}. Skipping MTPE task loading.")
        return []

    mtpe_tasks = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    task = json.loads(line)
                    # Validate required fields
                    missing_fields = [field for field in MTPE_TASK_REQUIRED_FIELDS if field not in task or not task[field]]
                    if missing_fields:
                        logging.warning(f"MTPE task on line {line_num+1} in {file_path} is missing required fields: {', '.join(missing_fields)}. Skipping task.")
                        continue

                    # Add a type field for consistency if desired, or handle in main_generator
                    task["type"] = "mtpe_task"
                    mtpe_tasks.append(task)
                except json.JSONDecodeError:
                    logging.error(f"Error decoding JSON from MTPE task file {file_path} on line {line_num+1}. Skipping line.")
                    continue
        logging.info(f"Successfully loaded {len(mtpe_tasks)} MTPE tasks from {file_path}.")
        return mtpe_tasks
    except FileNotFoundError: # Should be caught by os.path.exists, but as a safeguard
        logging.error(f"MTPE tasks file not found: {file_path}")
        return []
    except Exception as e:
        logging.error(f"Error loading MTPE tasks from {file_path}: {e}", exc_info=True)
        return []

def load_all_tasks(questions_path=config.QUESTIONS_FILE,
                   questionnaire_path=config.QUESTIONNAIRE_FILE,
                   mtpe_tasks_path=None): # Default to None, will be set by config if not passed
    """
    Loads all tasks (open-ended questions, questionnaire items, and MTPE tasks).

    Args:
        questions_path (str): Path to the open-ended questions file.
        questionnaire_path (str): Path to the questionnaire JSON file.
        mtpe_tasks_path (str, optional): Path to the MTPE tasks JSONL file.
                                         Defaults to config.DEFAULT_MTPE_TASKS_PATH if None.

    Returns:
        dict: A dictionary with keys 'open_ended_questions', 'questionnaire_items',
              and 'mtpe_tasks', containing lists of tasks.
              Returns empty lists for specific task types if loading fails or path is not set.
    """
    if mtpe_tasks_path is None:
        mtpe_tasks_path = config.DEFAULT_MTPE_TASKS_PATH if hasattr(config, 'DEFAULT_MTPE_TASKS_PATH') else None

    logging.info(f"Loading tasks: Questions from '{questions_path}', Questionnaire from '{questionnaire_path}', MTPE from '{mtpe_tasks_path}'")

    open_ended = _load_open_ended_questions(questions_path)
    questionnaire = _load_questionnaire_items(questionnaire_path)
    mtpe_tasks = _load_mtpe_tasks(mtpe_tasks_path)

    return {
        "open_ended_questions": open_ended,
        "questionnaire_items": questionnaire,
        "mtpe_tasks": mtpe_tasks
    }

if __name__ == '__main__':
    # Ensure logging is configured for standalone testing of this module
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=config.LOG_LEVEL.upper() if hasattr(config, 'LOG_LEVEL') else logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    logger = logging.getLogger(__name__) # Get a logger for this module specifically for __main__
    logger.info("--- Task Loader Self-Test Started ---")

    # Ensure DATA_DIR exists (it should via config.py, but double check)
    try:
        if not os.path.exists(config.DATA_DIR):
            os.makedirs(config.DATA_DIR)
            logger.info(f"Created data directory for tests: {config.DATA_DIR}")

        # --- Setup for questions.txt and questionnaire.json tests ---
        default_questions_content = [
            "What is your primary motivation for teaching?",
            "Describe a challenging teaching situation and how you handled it."
        ]
        default_questionnaire_content = [
            {"id": "q1", "type": "multiple_choice", "text": "Which age group do you prefer teaching?", "options": ["K-5", "6-8", "9-12", "Adults"]},
            {"id": "q2", "type": "likert_scale", "text": "Rate your comfort with using technology in the classroom (1=Low, 5=High)."},
            {"id": "q3", "type": "short_answer", "text": "What are your strengths as an educator?"}
        ]

        # Use specific test file paths to avoid interfering with actual data files if they exist
        test_questions_file = os.path.join(config.DATA_DIR, "test_questions.txt")
        test_questionnaire_file = os.path.join(config.DATA_DIR, "test_questionnaire.json")
        test_mtpe_tasks_file = os.path.join(config.DATA_DIR, "test_mtpe_tasks.jsonl")

        # Create/Overwrite questions.txt for testing
        logger.info(f"Setting up '{test_questions_file}' for testing.")
        with open(test_questions_file, 'w', encoding='utf-8') as f:
            for q_text in default_questions_content:
                f.write(q_text + "\n")

        # Create/Overwrite questionnaire.json for testing
        logger.info(f"Setting up '{test_questionnaire_file}' for testing.")
        with open(test_questionnaire_file, 'w', encoding='utf-8') as f:
            json.dump(default_questionnaire_content, f, indent=2)

        # --- Setup for mtpe_tasks.jsonl test ---
        default_mtpe_tasks_content = [
            {"task_id": "MTPE_TEST_001", "source_text_ch": "测试源文本。", "machine_translation_en": "Test source text.", "domain": "General", "difficulty_level": 1},
            {"task_id": "MTPE_TEST_002", "source_text_ch": "另一个测试。", "machine_translation_en": "Another test.", "domain": "General", "difficulty_level": 1}
        ]
        logger.info(f"Setting up '{test_mtpe_tasks_file}' for testing.")
        with open(test_mtpe_tasks_file, 'w', encoding='utf-8') as f:
            for task_item in default_mtpe_tasks_content:
                f.write(json.dumps(task_item) + '\n')

        logger.info("\n--- Testing specific loader functions ---")
        loaded_open_ended = _load_open_ended_questions(test_questions_file)
        logger.info(f"Loaded {len(loaded_open_ended)} open-ended questions directly.")

        loaded_questionnaire = _load_questionnaire_items(test_questionnaire_file)
        logger.info(f"Loaded {len(loaded_questionnaire)} questionnaire items directly.")

        loaded_mtpe = _load_mtpe_tasks(test_mtpe_tasks_file)
        logger.info(f"Loaded {len(loaded_mtpe)} MTPE tasks directly.")
        if loaded_mtpe:
            logger.info(f"  Example MTPE Task ID: {loaded_mtpe[0].get('task_id')}, Domain: {loaded_mtpe[0].get('domain')}")

        logger.info("\n--- Testing load_all_tasks with test files ---")
        all_tasks = load_all_tasks(
            questions_path=test_questions_file,
            questionnaire_path=test_questionnaire_file,
            mtpe_tasks_path=test_mtpe_tasks_file
        )

        logger.info(f"Total open-ended questions loaded via load_all_tasks: {len(all_tasks['open_ended_questions'])}")
        logger.info(f"Total questionnaire items loaded via load_all_tasks: {len(all_tasks['questionnaire_items'])}")
        logger.info(f"Total MTPE tasks loaded via load_all_tasks: {len(all_tasks['mtpe_tasks'])}")
        if all_tasks['mtpe_tasks']:
            logger.info(f"  Example MTPE Task from load_all_tasks: {all_tasks['mtpe_tasks'][0].get('task_id')}")

        logger.info("\n--- Testing load_all_tasks with default (production) paths ---")
        # This will use the actual data files if they exist, or log errors if not
        all_tasks_default = load_all_tasks()
        logger.info(f"Default open-ended questions: {len(all_tasks_default['open_ended_questions'])}")
        logger.info(f"Default questionnaire items: {len(all_tasks_default['questionnaire_items'])}")
        logger.info(f"Default MTPE tasks: {len(all_tasks_default['mtpe_tasks'])}")
        if all_tasks_default['mtpe_tasks']:
             logger.info(f"  Example default MTPE Task ID: {all_tasks_default['mtpe_tasks'][0].get('task_id')}")
        else:
            logger.info("No default MTPE tasks loaded (file might be empty or not found as per config).")


        logger.info("\n--- Testing with non-existent files for all types via load_all_tasks ---")
        non_existent_q = os.path.join(config.DATA_DIR, "non_existent_q.txt")
        non_existent_qn = os.path.join(config.DATA_DIR, "non_existent_qn.json")
        non_existent_mtpe = os.path.join(config.DATA_DIR, "non_existent_mtpe.jsonl")

        ne_tasks = load_all_tasks(
            questions_path=non_existent_q,
            questionnaire_path=non_existent_qn,
            mtpe_tasks_path=non_existent_mtpe
        )
        if not ne_tasks["open_ended_questions"] and \
           not ne_tasks["questionnaire_items"] and \
           not ne_tasks["mtpe_tasks"]:
            logger.info("Correctly handled all non-existent task files (returned empty lists for all types).")
        else:
            logger.error("ERROR: Did not correctly handle all non-existent task files.")

    finally:
        # Clean up test files
        if os.path.exists(test_questions_file): os.remove(test_questions_file)
        if os.path.exists(test_questionnaire_file): os.remove(test_questionnaire_file)
        if os.path.exists(test_mtpe_tasks_file): os.remove(test_mtpe_tasks_file)
        logger.info("Cleaned up test files.")

    logger.info("--- Task Loader Self-Test Finished ---")
