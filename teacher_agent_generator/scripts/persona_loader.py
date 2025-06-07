# teacher_agent_generator/scripts/persona_loader.py
import csv
import logging
import os
import sys

# If this script is run directly, add its directory to sys.path
# to allow direct import of 'config' from the same directory.
# This needs to be done before 'import config'
_CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_SCRIPT_DIR)

import config # Should now work when run as script (due to sys.path modification above)
             # and when imported as a module if 'scripts/' is in Python's search path.

# Configure basic logging
# Note: The global basicConfig might be overridden if main_generator calls its own configure_logging.
# For standalone script testing, this is fine.
logging.basicConfig(level=config.LOG_LEVEL.upper() if hasattr(config, 'LOG_LEVEL') else logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')


# Define required columns for personas.csv
REQUIRED_COLUMNS = [
    "name", "gender", "title",
    "teaching_experience_years", "professional_background", "teaching_plan"
]

# Define optional columns for richer persona definition
OPTIONAL_PERSONA_COLUMNS = [
    "tone_keywords",             # e.g., "formal, academic", "warm, encouraging"
    "communication_style",       # e.g., "prefers analogies", "uses rhetorical questions"
    "key_terminology",           # e.g., "pedagogy, constructivism"
    "role_specific_directives",  # e.g., "As a historian, always contextualize..."
    "example_phrase"             # e.g., "In my view...", "Let's explore..."
]

# Ensure the config path is correctly set up for generated_agents directory creation
# This happens when config is imported, so ensure it's imported early enough if scripts run standalone.
# The following line in config.py `os.makedirs(GENERATED_AGENTS_DIR, exist_ok=True)`
# depends on BASE_DIR being correct.

def load_personas(file_path=config.PERSONAS_FILE):
    """
    Loads personas from a CSV file.

    Args:
        file_path (str): The path to the personas CSV file.
                         Defaults to config.PERSONAS_FILE.

    Returns:
        list: A list of dictionaries, where each dictionary represents a persona.
              Returns an empty list if the file is not found, is empty,
              or if headers are incorrect.
    """
    personas = []
    try:
        with open(file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            # Validate headers
            if not reader.fieldnames:
                logging.error(f"Personas file is empty or has no headers: {file_path}")
                return []

            if not all(col in reader.fieldnames for col in REQUIRED_COLUMNS):
                missing_cols = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
                extra_cols = [col for col in reader.fieldnames if col not in REQUIRED_COLUMNS]
                logging.error(f"Personas file header mismatch in {file_path}.")
                if missing_cols:
                    logging.error(f"Missing required columns: {', '.join(missing_cols)}")
                if extra_cols:
                    logging.warning(f"Found unexpected columns: {', '.join(extra_cols)}")
                # Allow processing if all REQUIRED_COLUMNS are present, even with extras.
                # If critical columns are missing, perhaps return [] or raise error.
                # For now, we'll log error and proceed if vital ones are missing based on all() check.
                # Re-evaluating the condition: if not all required columns are present, it's an error.
                if any(col not in reader.fieldnames for col in REQUIRED_COLUMNS):
                     logging.error("Due to missing required columns, cannot process personas.")
                     return []

            # Check for optional columns
            detected_optional_cols = [col for col in OPTIONAL_PERSONA_COLUMNS if col in reader.fieldnames]
            if detected_optional_cols:
                logging.info(f"Detected optional persona refinement columns: {', '.join(detected_optional_cols)}")
            else:
                logging.info("No optional persona refinement columns (e.g., tone_keywords) detected. Using basic persona attributes.")

            for row in reader:
                # Basic validation for teaching_experience_years
                try:
                    if row.get("teaching_experience_years"): # Check if None or empty
                        row["teaching_experience_years"] = int(row["teaching_experience_years"])
                    else: # Handle empty string for years of experience as None or 0
                        row["teaching_experience_years"] = 0
                        logging.warning(f"Persona '{row.get('name', 'Unknown')}' has missing teaching_experience_years. Defaulting to 0.")
                except ValueError:
                    logging.error(f"Invalid format for 'teaching_experience_years' for persona '{row.get('name', 'Unknown')}'. Must be an integer. Skipping persona.")
                    continue # Skip this persona

                personas.append(row)

        if not personas and reader.fieldnames : # File had headers but no data rows
            logging.warning(f"Personas file {file_path} contains headers but no data rows.")

        logging.info(f"Successfully loaded {len(personas)} personas from {file_path}")
        return personas

    except FileNotFoundError:
        logging.error(f"Personas file not found: {file_path}")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading personas from {file_path}: {e}")
        return []

if __name__ == '__main__':
    # Ensure logging is configured for standalone testing of this module
    # (The global basicConfig above might be too late or not specific enough for some contexts)
    if not logging.getLogger().hasHandlers(): # Re-check or be more specific if needed
        logging.basicConfig(level=config.LOG_LEVEL.upper() if hasattr(config, 'LOG_LEVEL') else logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    logger = logging.getLogger(__name__) # Get a logger for this module specifically for __main__
    logger.info("--- Starting Persona Loader Self-Test ---")

    # Test 1: Loading from the default personas.csv (likely no optional columns)
    logger.info(f"Test 1: Loading from default personas file: {config.PERSONAS_FILE}")
    personas_data_default = load_personas(config.PERSONAS_FILE)
    if personas_data_default:
        logger.info(f"Test 1: Successfully loaded {len(personas_data_default)} personas from default file.")
        # print(f"Test 1: Loaded {len(personas_data_default)} personas from {config.PERSONAS_FILE}")
    else:
        logger.warning(f"Test 1: No personas loaded from default file or an error occurred. Check previous logs.")
        # print(f"Test 1: No personas loaded from {config.PERSONAS_FILE}. Check logs.")
    print("-" * 30)

    # Test 2: Test with a non-existent file
    logger.info("Test 2: Testing with a non-existent file.")
    non_existent_file = os.path.join(config.DATA_DIR, "non_existent_personas_test.csv")
    personas_data_non_existent = load_personas(non_existent_file)
    if not personas_data_non_existent:
        logger.info(f"Test 2: Correctly handled non-existent file: {non_existent_file}")
        # print(f"Test 2: Correctly handled non-existent file.")
    else:
        logger.error(f"Test 2: ERROR - Loaded {len(personas_data_non_existent)} personas from a non-existent file.")
        # print(f"Test 2: ERROR - Loaded {len(personas_data_non_existent)} personas from a non-existent file.")
    print("-" * 30)

    # Test 3: Test with a file with incorrect headers
    logger.info("Test 3: Testing with a file with incorrect headers.")
    dummy_bad_header_file = os.path.join(config.DATA_DIR, "dummy_bad_headers_test.csv")
    try:
        with open(dummy_bad_header_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["name", "gender", "WRONG_COLUMN_NAME"]) # Missing many required, one wrong
            writer.writerow(["TestBadPersona", "Male", "Some Role"])

        personas_bad_headers = load_personas(dummy_bad_header_file)
        if not personas_bad_headers:
            logger.info(f"Test 3: Correctly handled file with bad headers: {dummy_bad_header_file}")
            # print(f"Test 3: Correctly handled file with bad headers.")
        else:
            logger.error(f"Test 3: ERROR - Loaded {len(personas_bad_headers)} personas despite bad headers.")
            # print(f"Test 3: ERROR - Loaded {len(personas_bad_headers)} personas despite bad headers.")
    finally:
        if os.path.exists(dummy_bad_header_file):
            os.remove(dummy_bad_header_file)
    print("-" * 30)

    # Test 4: Test with an empty file (just headers, no data)
    logger.info("Test 4: Testing with an empty file (headers only).")
    dummy_empty_data_file = os.path.join(config.DATA_DIR, "dummy_empty_data_test.csv")
    try:
        with open(dummy_empty_data_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(REQUIRED_COLUMNS) # Correct headers, but no data rows

        personas_empty_data = load_personas(dummy_empty_data_file)
        if not personas_empty_data:
            logger.info(f"Test 4: Correctly handled empty data file (loaded 0 personas): {dummy_empty_data_file}")
            # print(f"Test 4: Loaded 0 personas (file has headers but no data rows), as expected.")
        else:
            logger.error(f"Test 4: ERROR - Loaded {len(personas_empty_data)} personas from an empty data file. Expected 0.")
            # print(f"Test 4: ERROR - Loaded {len(personas_empty_data)} personas from an empty data file. Expected 0.")
    finally:
        if os.path.exists(dummy_empty_data_file):
            os.remove(dummy_empty_data_file)
    print("-" * 30)

    # Test 5: Test with a file containing optional persona columns
    logger.info("Test 5: Testing with a file that includes optional persona columns.")
    dummy_optional_cols_file = os.path.join(config.DATA_DIR, "dummy_personas_optional_test.csv")
    optional_test_header = REQUIRED_COLUMNS + [OPTIONAL_PERSONA_COLUMNS[0], OPTIONAL_PERSONA_COLUMNS[2]] # name, gender, ..., tone_keywords, key_terminology

    try:
        with open(dummy_optional_cols_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(optional_test_header)
            writer.writerow([
                "Opti Persona", "Non-binary", "Specialist", 3, "Research & Development", "Inquiry-based learning",
                "curious, analytical", "metaphysics, epistemology" # Values for tone_keywords, key_terminology
            ])

        personas_optional = load_personas(dummy_optional_cols_file)
        if personas_optional and len(personas_optional) == 1:
            logger.info(f"Test 5: Successfully loaded 1 persona from file with optional columns: {dummy_optional_cols_file}")
            # print(f"Test 5: Successfully loaded 1 persona from {dummy_optional_cols_file} (Check logs for optional column detection).")
            # Expected log: "Detected optional persona refinement columns: tone_keywords, key_terminology"
        else:
            logger.error(f"Test 5: Failed to load personas from {dummy_optional_cols_file} or loaded incorrect number.")
            # print(f"Test 5: Failed to load personas from {dummy_optional_cols_file}.")

    finally:
        if os.path.exists(dummy_optional_cols_file):
            os.remove(dummy_optional_cols_file)
    print("-" * 30)

    logger.info("--- Persona Loader Self-Test Finished ---")
