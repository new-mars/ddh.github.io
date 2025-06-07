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

# --- Constants for Translator Personas ---
TRANSLATOR_REQUIRED_COLUMNS = [
    "persona_id", "persona_name", "native_language", "education_level",
    "major_subject", "english_proficiency_score", "has_translation_certification",
    "translation_experience_years_raw", "employment_type",
    "sample_source_text_ch", "sample_translation_en"
]

TRANSLATOR_OPTIONAL_COLUMNS = [
    "gender", "common_linguistic_traits", "cat_tool_familiarity"
]


# --- Helper Functions for Translator Personas ---
def _calculate_adjusted_experience(raw_years_val, employment_type_val: str) -> float:
    """Calculates adjusted translation experience based on employment type."""
    try:
        raw_years = float(raw_years_val)
    except (ValueError, TypeError):
        logging.warning(f"Invalid or missing raw experience years '{raw_years_val}'. Defaulting to 0.")
        return 0.0

    employment_type_lower = str(employment_type_val).lower().strip()
    multiplier = 0.0
    if 'full-time' in employment_type_lower or 'full time' in employment_type_lower: # Making it more robust
        multiplier = 1.0
    elif 'part-time' in employment_type_lower or 'part time' in employment_type_lower:
        multiplier = 0.5
    elif 'freelance' in employment_type_lower:
        multiplier = 0.7
    else:
        logging.warning(f"Unknown or unmatched employment type '{employment_type_val}'. Assuming 0 multiplier for experience adjustment.")

    return raw_years * multiplier

def _determine_skill_level(adjusted_years: float, has_certification_val) -> str:
    """Determines skill level based on adjusted experience and certification."""
    level = ""
    if 0 <= adjusted_years <= 2:
        level = "Junior"
    elif 2 < adjusted_years <= 5:
        level = "Mid-level"
    elif adjusted_years > 5:
        level = "Senior"
    else: # Should not happen if adjusted_years is always >= 0
        level = "Undefined"

    # Robust boolean interpretation for has_certification_val
    has_cert_str = str(has_certification_val).strip().lower()
    has_certification = has_cert_str == 'yes' or has_cert_str == 'true' or has_cert_str == '1'

    if has_certification and level in ["Mid-level", "Senior"]:
        level += " (Certified)"
    elif has_certification and level == "Junior": # Or just add (Certified) to any level if they have it
        level = "Junior (Certified)"

    return level


# --- Main Persona Loading Functions ---
def load_translator_personas(file_path=None) -> list[dict]:
    """
    Loads translator personas from a CSV file, calculates adjusted experience and skill level.

    Args:
        file_path (str, optional): Path to the translator personas CSV file.
                                   Defaults to config.DEFAULT_TRANSLATOR_PERSONAS_CSV_PATH.

    Returns:
        list: A list of dictionaries, where each dictionary represents a translator persona
              with added calculated fields. Returns an empty list on error or if file not found.
    """
    if file_path is None:
        file_path = config.DEFAULT_TRANSLATOR_PERSONAS_CSV_PATH

    translator_personas = []
    try:
        with open(file_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            if not reader.fieldnames:
                logging.error(f"Translator personas file is empty or has no headers: {file_path}")
                return []

            # Validate required columns
            missing_required = [col for col in TRANSLATOR_REQUIRED_COLUMNS if col not in reader.fieldnames]
            if missing_required:
                logging.error(f"Translator personas file {file_path} is missing required columns: {', '.join(missing_required)}")
                return []

            # Check for optional columns
            detected_optional = [col for col in TRANSLATOR_OPTIONAL_COLUMNS if col in reader.fieldnames]
            if detected_optional:
                logging.info(f"Detected optional translator persona columns: {', '.join(detected_optional)}")
            else:
                logging.info("No optional translator persona columns detected.")

            for row_num, row in enumerate(reader):
                persona_id = row.get("persona_id", f"Row_{row_num+1}")

                # Calculate adjusted experience and skill level
                raw_exp = row.get("translation_experience_years_raw")
                emp_type = row.get("employment_type")
                has_cert = row.get("has_translation_certification")

                row["translation_experience_years_adjusted"] = _calculate_adjusted_experience(raw_exp, emp_type)
                row["translation_skill_level"] = _determine_skill_level(row["translation_experience_years_adjusted"], has_cert)

                # Basic validation for crucial fields
                if not row.get("sample_source_text_ch") or "[Chinese Source Sample" in str(row.get("sample_source_text_ch")):
                    logging.warning(f"Persona ID '{persona_id}': Missing or placeholder 'sample_source_text_ch'.")
                if not row.get("sample_translation_en") or "[English Translation Sample" in str(row.get("sample_translation_en")):
                    logging.warning(f"Persona ID '{persona_id}': Missing or placeholder 'sample_translation_en'.")

                score_val = row.get("english_proficiency_score")
                try:
                    if score_val is not None and score_val.lower() != 'n/a (native speaker)':
                        float(score_val)
                except ValueError:
                    logging.warning(f"Persona ID '{persona_id}': Invalid 'english_proficiency_score' ('{score_val}'). Should be float or 'N/A (Native Speaker)'.")

                translator_personas.append(row)

            if not translator_personas and reader.fieldnames:
                logging.warning(f"Translator personas file {file_path} has headers but no data rows.")

            logging.info(f"Successfully loaded and processed {len(translator_personas)} translator personas from {file_path}.")
            return translator_personas

    except FileNotFoundError:
        logging.error(f"Translator personas file not found: {file_path}")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading translator personas from {file_path}: {e}", exc_info=True)
        return []

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

    # --- Tests for original load_personas ---
    logger.info("--- Testing original 'load_personas' function ---")
    # Test 1: Loading from the default personas.csv (likely no optional columns)
    logger.info(f"Test 1: Loading from default personas file: {config.PERSONAS_FILE}")
    personas_data_default = load_personas(config.PERSONAS_FILE)
    if personas_data_default is not None: # load_personas returns list or None
        logger.info(f"Test 1: Successfully processed default personas file. Loaded {len(personas_data_default)} personas.")
    else:
        logger.warning(f"Test 1: Error or no personas loaded from default file. Check previous logs.")
    print("-" * 30)

    # Test 2: Test with a non-existent file for original load_personas
    logger.info("Test 2: Testing with a non-existent file for original personas.")
    non_existent_file_orig = os.path.join(config.DATA_DIR, "non_existent_personas_orig_test.csv")
    personas_data_non_existent_orig = load_personas(non_existent_file_orig)
    if not personas_data_non_existent_orig: # Expecting empty list
        logger.info(f"Test 2: Correctly handled non-existent file: {non_existent_file_orig}")
    else:
        logger.error(f"Test 2: ERROR - Loaded {len(personas_data_non_existent_orig)} personas from a non-existent file.")
    print("-" * 30)

    # Test 3: Test with a file with incorrect headers for original load_personas
    logger.info("Test 3: Testing with a file with incorrect headers for original personas.")
    dummy_bad_header_file_orig = os.path.join(config.DATA_DIR, "dummy_bad_headers_orig_test.csv")
    try:
        with open(dummy_bad_header_file_orig, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["name", "gender", "WRONG_COLUMN_NAME_ORIG"]) # Missing required
            writer.writerow(["TestBadPersonaOrig", "Female", "Another Role"])

        personas_bad_headers_orig = load_personas(dummy_bad_header_file_orig)
        if not personas_bad_headers_orig:
            logger.info(f"Test 3: Correctly handled file with bad headers: {dummy_bad_header_file_orig}")
        else:
            logger.error(f"Test 3: ERROR - Loaded {len(personas_bad_headers_orig)} personas despite bad headers.")
    finally:
        if os.path.exists(dummy_bad_header_file_orig):
            os.remove(dummy_bad_header_file_orig)
    print("-" * 30)

    # Test 4: Test with an empty file (just headers, no data) for original load_personas
    logger.info("Test 4: Testing with an empty file (headers only) for original personas.")
    dummy_empty_data_file_orig = os.path.join(config.DATA_DIR, "dummy_empty_data_orig_test.csv")
    try:
        with open(dummy_empty_data_file_orig, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(REQUIRED_COLUMNS)

        personas_empty_data_orig = load_personas(dummy_empty_data_file_orig)
        if not personas_empty_data_orig:
            logger.info(f"Test 4: Correctly handled empty data file (loaded 0 personas): {dummy_empty_data_file_orig}")
        else:
            logger.error(f"Test 4: ERROR - Loaded {len(personas_empty_data_orig)} personas from an empty data file. Expected 0.")
    finally:
        if os.path.exists(dummy_empty_data_file_orig):
            os.remove(dummy_empty_data_file_orig)
    print("-" * 30)

    # Test 5: Test with a file containing optional persona columns for original load_personas
    logger.info("Test 5: Testing with a file that includes optional persona columns for original personas.")
    dummy_optional_cols_file_orig = os.path.join(config.DATA_DIR, "dummy_personas_optional_orig_test.csv")
    optional_test_header_orig = REQUIRED_COLUMNS + [OPTIONAL_PERSONA_COLUMNS[0], OPTIONAL_PERSONA_COLUMNS[2]]

    try:
        with open(dummy_optional_cols_file_orig, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(optional_test_header_orig)
            writer.writerow([
                "Opti Persona Orig", "Other", "Consultant", 7, "AI Ethics & Policy", "Problem-based learning",
                "thoughtful, precise", "deontology, consequentialism"
            ])

        personas_optional_orig = load_personas(dummy_optional_cols_file_orig)
        if personas_optional_orig and len(personas_optional_orig) == 1:
            logger.info(f"Test 5: Successfully loaded 1 persona from file with optional columns: {dummy_optional_cols_file_orig}")
        else:
            logger.error(f"Test 5: Failed to load personas from {dummy_optional_cols_file_orig} or loaded incorrect number.")
    finally:
        if os.path.exists(dummy_optional_cols_file_orig):
            os.remove(dummy_optional_cols_file_orig)
    print("-" * 30)

    # --- Tests for new 'load_translator_personas' function ---
    logger.info("--- Testing new 'load_translator_personas' function ---")

    # Test 6: Loading from the default translator_personas.csv
    logger.info(f"Test 6: Loading from default translator personas file: {config.DEFAULT_TRANSLATOR_PERSONAS_CSV_PATH}")
    translator_personas_data = load_translator_personas() # Uses default path from config

    if translator_personas_data:
        logger.info(f"Test 6: Successfully loaded {len(translator_personas_data)} translator personas.")
        for i, p_data in enumerate(translator_personas_data):
            logger.info(f"  Translator Persona {i+1}: {p_data.get('persona_name')}")
            logger.info(f"    Raw Exp: {p_data.get('translation_experience_years_raw')}, Employment: {p_data.get('employment_type')}")
            logger.info(f"    Adjusted Exp: {p_data.get('translation_experience_years_adjusted')}")
            logger.info(f"    Skill Level: {p_data.get('translation_skill_level')}")
            logger.info(f"    Has Cert: {p_data.get('has_translation_certification')}")
            if not p_data.get('sample_source_text_ch') or "[Chinese Source Sample" in p_data.get('sample_source_text_ch'):
                logger.warning(f"    Sample source text for {p_data.get('persona_name')} is placeholder or missing.")
            if not p_data.get('sample_translation_en') or "[English Translation Sample" in p_data.get('sample_translation_en'):
                logger.warning(f"    Sample translation text for {p_data.get('persona_name')} is placeholder or missing.")

    else:
        logger.warning("Test 6: No translator personas loaded or an error occurred. Check logs.")
    print("-" * 30)

    # Test 7: Test load_translator_personas with a non-existent file
    logger.info("Test 7: Testing load_translator_personas with a non-existent file.")
    non_existent_translator_file = os.path.join(config.DATA_DIR, "non_existent_translator_personas.csv")
    translator_personas_non_existent = load_translator_personas(file_path=non_existent_translator_file) # Corrected kwarg
    if not translator_personas_non_existent:
        logger.info(f"Test 7: Correctly handled non-existent translator personas file: {non_existent_translator_file}")
    else:
        logger.error(f"Test 7: ERROR - Loaded {len(translator_personas_non_existent)} translator personas from a non-existent file.")
    print("-" * 30)

    logger.info("--- Persona Loader Self-Test Finished ---")
