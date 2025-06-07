# teacher_agent_generator/scripts/llm_interface.py
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

# Configure basic logging
logging.basicConfig(level=config.LOG_LEVEL.upper() if hasattr(config, 'LOG_LEVEL') else logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
                    filename=config.LOG_FILE if hasattr(config, 'LOG_FILE') else None,
                    filemode='a')

# Attempt to import provider-specific libraries
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logging.info("Ollama library not found. Ollama provider will not be available.")

try:
    import dashscope
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    logging.info("Dashscope (for Qwen) library not found. Qwen provider will not be available.")

try:
    from openai import OpenAI
    OPENAI_SDK_AVAILABLE = True # For DeepSeek or other OpenAI-compatible APIs
except ImportError:
    OPENAI_SDK_AVAILABLE = False
    logging.info("OpenAI SDK not found. DeepSeek or other OpenAI-compatible providers will not be available.")


def _generate_with_ollama(model_name, system_prompt, user_prompt, temperature, max_tokens):
    if not OLLAMA_AVAILABLE:
        logging.error("Ollama library is not installed. Cannot use Ollama provider.")
        return None
    try:
        client = ollama.Client() # Assumes default host, or configure as needed
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]
        # Ollama's generate API options are slightly different.
        # Temperature is 'temperature', max_tokens is 'num_predict'.
        # It doesn't directly support 'max_tokens' in the same way as OpenAI.
        # 'num_predict' controls the max number of tokens to generate.
        # 'options' parameter takes these.
        options = {
            "temperature": temperature,
            "num_predict": max_tokens if max_tokens > 0 else -1 # -1 for unlimited/model default
        }
        response = client.chat(model=model_name, messages=messages, options=options)
        return response['message']['content']
    except Exception as e:
        logging.error(f"Error generating response with Ollama (model: {model_name}): {e}")
        return None

def _generate_with_qwen(api_key, model_name, system_prompt, user_prompt, temperature, max_tokens):
    if not DASHSCOPE_AVAILABLE:
        logging.error("Dashscope library is not installed. Cannot use Qwen provider.")
        return None
    if not api_key:
        logging.error("Qwen API key not provided. Cannot use Qwen provider.")
        return None
    try:
        dashscope.api_key = api_key
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]
        # Dashscope's call parameters might differ slightly.
        # Assuming 'temperature' and 'max_tokens' are supported or have equivalents.
        # For Qwen models, temperature (0-2, 0 for deterministic), max_tokens.
        # Dashscope uses result_format='message' for chat-like interactions.
        response = dashscope.Generation.call(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens if max_tokens > 0 else None, # None might use model default
            result_format='message'
        )
        if response.status_code == 200:
            return response.output.choices[0].message.content
        else:
            logging.error(f"Error from Qwen API (model: {model_name}): {response.code} - {response.message}")
            return None
    except Exception as e:
        logging.error(f"Error generating response with Qwen (model: {model_name}): {e}")
        return None

def _generate_with_deepseek(api_key, model_name, system_prompt, user_prompt, temperature, max_tokens):
    if not OPENAI_SDK_AVAILABLE:
        logging.error("OpenAI SDK is not installed. Cannot use DeepSeek provider.")
        return None
    if not api_key:
        logging.error("DeepSeek API key not provided. Cannot use DeepSeek provider.")
        return None
    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens if max_tokens > 0 else None # None might use model default
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error generating response with DeepSeek (model: {model_name}): {e}")
        return None

def generate_response(system_prompt, user_prompt,
                      provider=config.DEFAULT_MODEL.split(':')[0] if ':' in config.DEFAULT_MODEL else 'openai',
                      model_name=config.DEFAULT_MODEL.split(':')[-1] if ':' in config.DEFAULT_MODEL else config.DEFAULT_MODEL,
                      temperature=config.DEFAULT_TEMPERATURE,
                      max_tokens=config.MAX_TOKENS):
    """
    Generates a response from a specified LLM provider.

    Args:
        system_prompt (str): The system prompt.
        user_prompt (str): The user prompt.
        provider (str): The LLM provider ('ollama', 'qwen', 'deepseek', 'openai').
                        Defaults based on config.DEFAULT_MODEL or 'openai'.
        model_name (str): The specific model name for the provider.
                          Defaults based on config.DEFAULT_MODEL.
        temperature (float): The generation temperature. Defaults to config.DEFAULT_TEMPERATURE.
        max_tokens (int): The maximum number of tokens to generate. Defaults to config.MAX_TOKENS.

    Returns:
        str: The generated text response, or None if an error occurred.
    """
    logging.info(f"Requesting generation from provider: {provider}, model: {model_name}")

    if provider == 'ollama':
        return _generate_with_ollama(model_name, system_prompt, user_prompt, temperature, max_tokens)
    elif provider == 'qwen':
        # Assuming Qwen uses ANTHROPIC_API_KEY for this example as no specific QWEN_API_KEY is in config
        # This should be config.QWEN_API_KEY or similar in a real setup
        return _generate_with_qwen(config.ANTHROPIC_API_KEY, model_name, system_prompt, user_prompt, temperature, max_tokens)
    elif provider == 'deepseek':
        return _generate_with_deepseek(config.OPENAI_API_KEY, model_name, system_prompt, user_prompt, temperature, max_tokens)
    # Add elif for 'openai' if a generic OpenAI provider is needed (using config.OPENAI_API_KEY)
    # For now, 'openai' provider route is missing, but DeepSeek uses the OpenAI SDK.
    # Let's assume default_model = "deepseek:deepseek-chat" or "qwen:qwen-turbo" or "ollama:llama2"
    else:
        logging.error(f"Unsupported LLM provider: {provider}")
        return None

if __name__ == '__main__':
    print("LLM Interface Module - Test Run")
    logging.info("LLM Interface Module - Test Run Started")

    test_system_prompt = "You are a helpful assistant."
    test_user_prompt = "Explain the concept of recursion in one sentence."

    # --- Ollama Test ---
    print("\n--- Testing Ollama ---")
    if OLLAMA_AVAILABLE:
        # List available Ollama models (optional, requires ollama running)
        try:
            ollama_client = ollama.Client()
            models = ollama_client.list()
            if models and models.get('models'):
                 print(f"Available Ollama models: {[m['name'] for m in models['models']]}")
                 ollama_test_model = models['models'][0]['name'] # Use the first available model
                 print(f"Using Ollama model: {ollama_test_model} for test.")
                 response_ollama = generate_response(test_system_prompt, test_user_prompt,
                                                 provider='ollama', model_name=ollama_test_model)
                 if response_ollama:
                     print(f"Ollama ({ollama_test_model}) Response: {response_ollama}")
                 else:
                     print(f"Failed to get response from Ollama ({ollama_test_model}). Check logs and ensure Ollama is running.")
            else:
                print("No Ollama models found or Ollama not running. Skipping Ollama test.")
        except Exception as e:
            print(f"Could not connect to Ollama or list models: {e}. Skipping Ollama test.")
            logging.warning(f"Could not connect to Ollama or list models: {e}. Skipping Ollama test.")
    else:
        print("Ollama library not available. Skipping Ollama test.")

    # --- Qwen (Dashscope) Test ---
    print("\n--- Testing Qwen (Dashscope) ---")
    if DASHSCOPE_AVAILABLE:
        if config.ANTHROPIC_API_KEY and config.ANTHROPIC_API_KEY != "your_anthropic_api_key_here": # Placeholder for Qwen key
            # Replace with an actual Qwen model name like "qwen-turbo", "qwen-plus", etc.
            qwen_test_model = "qwen-turbo"
            print(f"Using Qwen model: {qwen_test_model} for test.")
            # NB: Using ANTHROPIC_API_KEY as a stand-in for a Qwen/Dashscope key
            response_qwen = generate_response(test_system_prompt, test_user_prompt,
                                            provider='qwen', model_name=qwen_test_model,
                                            # Pass API key directly for testing if needed, or ensure config is set
                                            # For this test, generate_response will pick it from config
                                            )
            if response_qwen:
                print(f"Qwen ({qwen_test_model}) Response: {response_qwen}")
            else:
                print(f"Failed to get response from Qwen ({qwen_test_model}). Check logs and API key.")
        else:
            print("Dashscope API key (used for Qwen, placeholder: ANTHROPIC_API_KEY) not configured in .env. Skipping Qwen test.")
    else:
        print("Dashscope library not available. Skipping Qwen test.")

    # --- DeepSeek Test ---
    print("\n--- Testing DeepSeek ---")
    if OPENAI_SDK_AVAILABLE:
        if config.OPENAI_API_KEY and config.OPENAI_API_KEY != "your_openai_api_key_here":
            deepseek_test_model = "deepseek-chat" # Common model, or "deepseek-coder"
            print(f"Using DeepSeek model: {deepseek_test_model} for test.")
            response_deepseek = generate_response(test_system_prompt, test_user_prompt,
                                                provider='deepseek', model_name=deepseek_test_model)
            if response_deepseek:
                print(f"DeepSeek ({deepseek_test_model}) Response: {response_deepseek}")
            else:
                print(f"Failed to get response from DeepSeek ({deepseek_test_model}). Check logs and API key.")
        else:
            print("DeepSeek API key (OPENAI_API_KEY) not configured in .env. Skipping DeepSeek test.")
    else:
        print("OpenAI SDK (for DeepSeek) not available. Skipping DeepSeek test.")

    print("\nLLM Interface Module - Test Run Finished")
    logging.info("LLM Interface Module - Test Run Finished")
