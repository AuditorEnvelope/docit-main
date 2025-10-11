# Migration Guide

*Updated: 2025-10-11*

This migration guide details the breaking changes introduced in the "Enhanced Documentation Generation and Analysis Capabilities" update, helping you seamlessly transition your existing setup to the new version.

---

## Migration Guide: Enhanced Documentation Generation and Analysis Capabilities

This guide covers the necessary steps to migrate your application to the new version featuring enhanced documentation generation, comprehensive change analysis, and multi-provider LLM support.

### 1. What Changed and Why

This release introduces significant improvements to how our system processes GitHub events, analyzes code changes, and generates documentation. The core of these enhancements involves a more robust and flexible LLM integration, moving from a single, generic provider to a multi-provider architecture.

**Key Changes:**

*   **Multi-Provider LLM Support:** The most significant breaking change is the deprecation of the old, single-provider LLM interface (`llm_provider.py`). It has been replaced with a new, extensible architecture (`llm_provider_v2.py`) that allows for easy integration with various LLM providers (e.g., OpenAI, Anthropic, Google). This enables greater flexibility, cost optimization, and access to advanced models.
*   **Smart GitHub Push Event Processing:** The system now includes `smart_processor.py` for intelligent handling of GitHub push events. This involves comprehensive change analysis to identify relevant modifications, which then inform the documentation generation process. This streamlines the creation of up-to-date documentation.
*   **Comprehensive Change Analysis:** New logic has been added (`processor.py` updates) to perform deeper analysis of code changes, ensuring that generated documentation accurately reflects the latest modifications.
*   **Dedicated Documentation Creation:** The system now has enhanced capabilities for generating and updating documentation based on code changes and analyses, likely utilizing the new `gitbook_config_helper.py` for integration with GitBook.
*   **Configuration Updates:** Due to the multi-provider LLM support, the way LLM API keys and provider types are configured has changed.

**Reason for Changes:**

The primary motivation for these changes is to elevate the quality, accuracy, and flexibility of our documentation generation and change analysis features. By supporting multiple LLM providers, we can leverage the best models for specific tasks, improve content generation, and reduce dependency on a single vendor. The smart processing of GitHub events and comprehensive analysis ensures that documentation remains consistently updated with minimal manual intervention, enhancing the overall development workflow.

### 2. Step-by-Step Migration Instructions

Follow these steps to migrate your existing application.

#### Step 1: Update Project Dependencies

First, ensure your project's dependencies are updated to the latest version that includes these changes.

```bash
# If you manage dependencies via requirements.txt
pip install -r requirements.txt --upgrade

# If you install your application as a package
pip install your-package-name --upgrade
```

#### Step 2: Update LLM Configuration

The old generic LLM API key environment variable is likely no longer sufficient. You will need to define which LLM provider to use and its specific API key.

1.  **Identify New Environment Variables:**
    The new LLM provider system relies on specific environment variables. At a minimum, you will need:
    *   `LLM_PROVIDER_TYPE`: (Required) Specifies which LLM provider to use (e.g., `openai`, `anthropic`, `google`).
    *   **Provider-Specific API Key:** Based on `LLM_PROVIDER_TYPE`, you'll need the corresponding API key:
        *   `OPENAI_API_KEY` (if `LLM_PROVIDER_TYPE=openai`)
        *   `ANTHROPIC_API_KEY` (if `LLM_PROVIDER_TYPE=anthropic`)
        *   `GOOGLE_API_KEY` (if `LLM_PROVIDER_TYPE=google`)
    *   **(Optional) Other provider-specific configurations:** Consult the new documentation for any additional parameters (e.g., `OPENAI_MODEL_NAME`, `ANTHROPIC_MODEL_NAME`).

2.  **Update your `.env` file or deployment environment:**
    Example for OpenAI:
    ```ini
    # .env
    LLM_PROVIDER_TYPE=openai
    OPENAI_API_KEY=sk-your_openai_api_key_here
    # (Optional) LLM_MODEL_NAME=gpt-4-turbo
    ```
    Example for Anthropic:
    ```ini
    # .env
    LLM_PROVIDER_TYPE=anthropic
    ANTHROPIC_API_KEY=sk-your_anthropic_api_key_here
    # (Optional) LLM_MODEL_NAME=claude-3-opus-20240229
    ```

#### Step 3: Update LLM Provider Instantiation and Usage in Code

Anywhere you previously imported and used the old `llm_provider.LLMProvider` class, you must update your code to use the new multi-provider interface.

1.  **Remove Old Imports:**
    Delete lines like:
    ```python
    from llm_provider import LLMProvider # DEPRECATED
    ```

2.  **Import New LLM Manager:**
    Import the new LLM manager (e.g., `LLMManager` from `llm_provider_v2`). The exact class name and module might vary slightly, so check the latest API documentation.
    ```python
    from llm_provider_v2 import LLMManager # New multi-provider interface
    ```

3.  **Instantiate and Use the New Manager:**
    The `LLMManager` will typically auto-configure itself based on the environment variables set in Step 2. You then interact with this manager to generate text.

    ```python
    # Before (DEPRECATED):
    # llm = LLMProvider(api_key=os.getenv("LLM_API_KEY"))
    # response = llm.generate_text("prompt")

    # After:
    llm_manager = LLMManager() # Instantiates the appropriate provider based on LLM_PROVIDER_TYPE
    prompt = "Generate a summary of the given text."
    response = llm_manager.generate_text(prompt, max_tokens=200, temperature=0.7)
    ```

#### Step 4: Review GitHub Integration (if applicable)

If you have custom logic or direct integrations that interact with the system's GitHub event processing (e.g., by directly calling functions within `processor.py`), you should review these for compatibility.

*   The introduction of `smart_processor.py` implies a potentially new interface or expected data structure for processing GitHub push events.
*   For most users interacting via a standard webhook endpoint (e.g., `/github-webhook`), the endpoint itself should remain stable, but internal processing has changed. Ensure your webhooks are still correctly configured to point to your application's `/github-webhook` endpoint.
*   Check application logs for any errors related to GitHub event handling.

#### Step 5: Test Thoroughly

After making the necessary code and configuration changes, thoroughly test all functionalities, especially:

*   **Documentation Generation:** Trigger a GitHub push event (if integrated) or manually initiate documentation generation.
*   **Change Analysis:** Verify that the system correctly identifies and analyzes code changes.
*   **LLM-Dependent Features:** Ensure all features relying on LLM input (e.g., summarization, content creation) work as expected with the new provider setup.

### 3. Code Examples (Before/After)

Here's a common scenario: using the LLM to generate content.

**Before (Deprecated `llm_provider.py`):**

```python
# old_module.py
import os
from llm_provider import LLMProvider # Old, single-provider module

# Assume LLM_API_KEY was set in environment
api_key = os.getenv("LLM_API_KEY")

def generate_old_summary(text: str) -> str:
    try:
        # Direct instantiation with a generic API key
        llm = LLMProvider(api_key=api_key)
        prompt = f"Summarize the following text concisely: {text}"
        summary = llm.generate_text(prompt, max_tokens=150)
        return summary
    except Exception as e:
        print(f"Error using old LLMProvider: {e}")
        return "Failed to generate summary."

if __name__ == "__main__":
    sample_text = "The latest software update introduces several new features including dark mode and improved performance. Users are encouraged to update soon."
    print("--- Before Migration ---")
    print(f"Generated summary: {generate_old_summary(sample_text)}")
```

**After (New `llm_provider_v2.py` / Multi-provider interface):**

```python
# new_module.py
import os
from llm_provider_v2 import LLMManager # New, multi-provider manager

# Ensure these environment variables are set before running:
# LLM_PROVIDER_TYPE=openai
# OPENAI_API_KEY=sk-...

def generate_new_summary(text: str) -> str:
    try:
        # LLMManager automatically configures based on LLM_PROVIDER_TYPE and respective API key env vars
        llm_manager = LLMManager() 
        prompt = f"Provide a brief, key-point summary of the following: {text}"
        summary = llm_manager.generate_text(prompt, max_tokens=180, temperature=0.7)
        return summary
    except Exception as e:
        print(f"Error using new LLMManager: {e}")
        print("Please ensure LLM_PROVIDER_TYPE and its corresponding API key are set in your environment.")
        return "Failed to generate summary with new LLM."

if __name__ == "__main__":
    sample_text = "The latest software update introduces several new features including dark mode and improved performance. Users are encouraged to update soon."
    print("\n--- After Migration ---")
    print(f"Generated summary: {generate_new_summary(sample_text)}")

    # Example of using a specific provider if needed (though LLMManager abstracts this for general use)
    # try:
    #     anthropic_manager = LLMManager("anthropic") # Explicitly choose provider
    #     anthropic_summary = anthropic_manager.generate_text("Explain quantum entanglement simply.", model="claude-3-haiku-20240307")
    #     print(f"Anthropic Summary: {anthropic_summary}")
    # except Exception as e:
    #     print(f"Error with Anthropic provider: {e}")
```

### 4. Common Issues and Solutions

1.  **`ImportError: cannot import name 'LLMProvider' from 'llm_provider'`**
    *   **Issue:** Your code is still trying to import the deprecated LLM provider class.
    *   **Solution:** Update your import statements and LLM instantiation logic to use the new `LLMManager` from `llm_provider_v2` (or the equivalent new module/class). Refer to Step 3.

2.  **`ValueError: LLM_PROVIDER_TYPE environment variable not set.` or `KeyError` for API Key**
    *   **Issue:** The new `LLMManager` cannot determine which LLM provider to use or find its required API key.
    *   **Solution:** Ensure you have correctly set the `LLM_PROVIDER_TYPE` environment variable (e.g., `openai`, `anthropic`) and the corresponding API key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) in your environment or `.env` file. Double-check for typos.

3.  **Documentation generation or change analysis not triggering/working correctly after a GitHub push.**
    *   **Issue:** The new `smart_processor` might have different internal expectations, or your existing GitHub webhook setup needs verification.
    *   **Solution:**
        *   **Check Application Logs:** Look for errors originating from `processor.py` or `smart_processor.py`. These logs will often pinpoint issues with parsing the GitHub payload or processing the changes.
        *   **Verify GitHub Webhook:** Ensure your GitHub webhook is correctly configured to send `push` events to your application's endpoint. If your application endpoint changed, update the webhook.
        *   **Payload Structure:** While less likely for standard webhooks, if you're sending custom GitHub event payloads, ensure they conform to the expected structure of the new `smart_processor`.

4.  **Application fails to start or encounters runtime errors due to missing dependencies.**
    *   **Issue:** The new features (e.g., multi-provider LLM) may have introduced new Python package dependencies (e.g., `openai`, `anthropic`).
    *   **Solution:** Re-run `pip install -r requirements.txt --upgrade` to ensure all new required packages are installed. If you installed your application as a package, ensure you're on the latest version (`pip install your-package-name --upgrade`).

5.  **LLM responses are different or of lower quality.**
    *   **Issue:** You might be using a different default model or configuration parameters compared to the old setup.
    *   **Solution:**
        *   **Model Selection:** Check if the new `LLMManager` allows specifying a model name (e.g., `LLM_MODEL_NAME` env var or `model` parameter in `generate_text`). Ensure you're using a comparable model to your previous setup.
        *   **Parameters:** Review LLM generation parameters like `temperature`, `top_p`, `max_tokens`. These can significantly impact output quality. The new interface might have different defaults or parameter names.

### 5. Rollback Instructions

If you encounter critical issues during or after the migration and need to revert to the previous version, follow these steps:

1.  **Revert Code Changes:**
    *   If you're using Git, discard your local changes and revert to the commit just before the upgrade:
        ```bash
        git reset --hard <previous-successful-commit-hash>
        # Or if you were working on a feature branch:
        git checkout <previous-stable-branch-name>
        ```
    *   Manually revert any file modifications made during the migration, especially those related to LLM integration (`llm_provider_v2.py`, `app.py`, `processor.py`) and configuration.

2.  **Revert Environment Variables:**
    *   Remove the newly introduced environment variables (`LLM_PROVIDER_TYPE`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.).
    *   Restore any previously used generic LLM API key environment variables (e.g., `LLM_API_KEY`) if your old setup relied on them.

3.  **Reinstall Previous Dependencies:**
    *   If your `requirements.txt` was updated, revert it to the previous version.
    *   Reinstall the dependencies corresponding to the previous version of your application:
        ```bash
        pip install -r requirements_old_version.txt # If you have a versioned requirements file
        # Or, if installing a specific package version:
        pip install your-package-name==<previous-version-number>
        ```

4.  **Restore Old Configuration Files (if any):**
    *   If any configuration files (e.g., specific GitBook configurations or other `.json`/`.yaml` files) were modified or added, revert them to their state prior to the upgrade.

5.  **Restart Services:**
    *   After reverting all code and configuration, restart your application services to ensure they load the previous version correctly.

---

We recommend testing this migration in a staging environment before deploying to production. If you encounter any issues not covered here, please consult the official documentation or contact support.