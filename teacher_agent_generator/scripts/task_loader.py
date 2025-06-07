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

def _load_open_ended_questions(file_path=config.QUESTIONS_FILE):
    """Loads open-ended questions from a text file."""
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

def load_all_tasks(questions_path=config.QUESTIONS_FILE, questionnaire_path=config.QUESTIONNAIRE_FILE):
    """
    Loads all tasks (open-ended questions and questionnaire items).

    Args:
        questions_path (str): Path to the open-ended questions file.
        questionnaire_path (str): Path to the questionnaire JSON file.

    Returns:
        dict: A dictionary with keys 'open_ended_questions' and 'questionnaire_items',
              containing lists of tasks. Returns empty lists if loading fails.
    """
    logging.info(f"Loading all tasks from questions_path: {questions_path} and questionnaire_path: {questionnaire_path}")
    open_ended = _load_open_ended_questions(questions_path)
    questionnaire = _load_questionnaire_items(questionnaire_path)

    return {
        "open_ended_questions": open_ended,
        "questionnaire_items": questionnaire
    }

if __name__ == '__main__':
    print("Task Loader Module - Test Run")
    logging.info("Task Loader Module - Test Run Started")

    # For testing, ensure dummy files exist or create them if they don't.
    # This makes the test self-contained.

    # Ensure DATA_DIR exists (it should via config.py, but double check for standalone test)
    if not os.path.exists(config.DATA_DIR):
        os.makedirs(config.DATA_DIR)
        print(f"Created data directory for tests: {config.DATA_DIR}")

    # Default content for questions.txt
    default_questions_content = [
        "What is your primary motivation for teaching?",
        "Describe a challenging teaching situation and how you handled it."
    ]
    # Default content for questionnaire.json
    default_questionnaire_content = [
        {"id": "q1", "type": "multiple_choice", "text": "Which age group do you prefer teaching?", "options": ["K-5", "6-8", "9-12", "Adults"]},
        {"id": "q2", "type": "likert_scale", "text": "Rate your comfort with using technology in the classroom (1=Low, 5=High)."},
        {"id": "q3", "type": "short_answer", "text": "What are your strengths as an educator?"}
    ]

    # Check and create/overwrite questions.txt for testing
    if not os.path.exists(config.QUESTIONS_FILE) or os.path.getsize(config.QUESTIONS_FILE) == 0:
        print(f"Creating/Overwriting dummy '{config.QUESTIONS_FILE}' for testing.")
        with open(config.QUESTIONS_FILE, 'w', encoding='utf-8') as f:
            for q_text in default_questions_content:
                f.write(q_text + "\n")
    else:
        print(f"Using existing '{config.QUESTIONS_FILE}' for testing.")


    # Check and create/overwrite questionnaire.json for testing
    # The original questionnaire.json was created with just `[]`.
    # The test here will overwrite it with more comprehensive test data if it's still empty.
    needs_overwrite_questionnaire = False
    if not os.path.exists(config.QUESTIONNAIRE_FILE):
        needs_overwrite_questionnaire = True
    else:
        try:
            with open(config.QUESTIONNAIRE_FILE, 'r', encoding='utf-8') as f_check:
                content = json.load(f_check)
                if not content: # If it's an empty list or empty file
                    needs_overwrite_questionnaire = True
        except (json.JSONDecodeError, FileNotFoundError): # File exists but malformed or truly empty
             needs_overwrite_questionnaire = True
        except Exception: # Any other read error
            needs_overwrite_questionnaire = True


    if needs_overwrite_questionnaire:
        print(f"Creating/Overwriting dummy '{config.QUESTIONNAIRE_FILE}' for testing.")
        with open(config.QUESTIONNAIRE_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_questionnaire_content, f, indent=2)
    else:
        print(f"Using existing '{config.QUESTIONNAIRE_FILE}' for testing (assuming it has content).")

    print("\n--- Loading all tasks ---")
    all_tasks = load_all_tasks()

    if all_tasks["open_ended_questions"]:
        print(f"\nSuccessfully loaded {len(all_tasks['open_ended_questions'])} open-ended questions:")
        for i, task in enumerate(all_tasks['open_ended_questions']):
            print(f"  {i+1}. Type: {task['type']}, Text: {task['text'][:50]}...")
    else:
        print("\nNo open-ended questions loaded or an error occurred. Check logs.")

    if all_tasks["questionnaire_items"]:
        print(f"\nSuccessfully loaded {len(all_tasks['questionnaire_items'])} questionnaire items:")
        for i, task in enumerate(all_tasks['questionnaire_items']):
            print(f"  {i+1}. ID: {task['id']}, Type: {task['type']}, Text: {task['text'][:50]}...")
    else:
        print("\nNo questionnaire items loaded or an error occurred. Check logs.")

    print("\n--- Testing with non-existent files ---")
    non_existent_tasks = load_all_tasks(
        questions_path=os.path.join(config.DATA_DIR, "non_existent_questions.txt"),
        questionnaire_path=os.path.join(config.DATA_DIR, "non_existent_questionnaire.json")
    )
    if not non_existent_tasks["open_ended_questions"] and not non_existent_tasks["questionnaire_items"]:
        print("Correctly handled non-existent task files (returned empty lists).")
    else:
        print("ERROR: Did not correctly handle non-existent task files.")

    print("\nTask Loader Module - Test Run Finished")
    logging.info("Task Loader Module - Test Run Finished")
