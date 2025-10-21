# API Documentation

*Updated: 2025-10-21*

This document details the API changes introduced by the "Enhance documentation generation with AI-powered descriptions and metadata extraction" feature.

---

# Lekhak AI Documentation Generation Service API Reference

**Version:** 1.0 (Initial Release - Feature Commit: `[Insert Actual Commit SHA Here]`)

## Introduction

This API provides advanced capabilities for generating comprehensive and AI-enriched documentation directly from source code. By integrating sophisticated Large Language Models (LLMs) such as Gemini, Groq, and DeepSeek, the service automatically produces high-quality, concise descriptions for various code elements across a codebase (including repositories, SDKs, modules, features, functions, and classes).

Beyond AI-generated descriptions, this enhancement introduces robust static code analysis to extract detailed metadata, including function parameters (with their types and default values) and return types, supporting both Python and TypeScript signatures. A resilient fallback mechanism ensures that documentation descriptions are always available, even if external LLM services encounter temporary unavailability, maintaining service reliability.

## Base URL

All API requests should be made to the following base URL:

`https://api.lekhak-ai.com/v1` (Example)

## Authentication

All requests to the Lekhak AI API must be authenticated. You are required to include your API key in the `Authorization` header of every request as a Bearer token.

**Header Example:**
`Authorization: Bearer YOUR_API_KEY`

Please obtain your API key from your Lekhak AI dashboard or contact our support team for assistance.

## Endpoints

### 1. Generate Enriched Documentation

Generates hierarchical documentation for a specified code source, integrating AI-powered descriptions and detailed code metadata.

*   **HTTP Method:** `POST`
*   **Path:** `/docs/generate`

#### Request Body

The request body must be a JSON object with the following properties:

| Field                  | Type      | Required | Description                                                                                                                                                                                                                                                                                       | Example Value                                |
| :--------------------- | :-------- | :------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------- |
| `source_path`          | `string`  | Yes      | The path to the source code. This can be a local file path (if the API service has configured access), a URL to a Git repository (e.g., GitHub, GitLab), or a URL to a specific code file.                                                                                             | `"https://github.com/your-org/your-repo.git"` |
| `target_elements`      | `array`   | No       | A list of code element types to include in the generated documentation. If omitted, the service will attempt to document all recognized hierarchical elements (repo, module, function, class, etc.). <br>**Accepted values:** `"repo"`, `"sdk"`, `"module"`, `"feature"`, `"function"`, `"class"` | `["module", "function"]`                     |
| `output_format`        | `string`  | No       | The desired format for the output documentation. <br>**Accepted values:** `"json"`, `"markdown"`. Defaults to `"json"`.                                                                                                                                                                 | `"markdown"`                                 |
| `llm_preference`       | `string`  | No      | Specifies a preferred Large Language Model for generating descriptions. The service will attempt to use this model first, falling back to other configured LLMs or a default description generation method if the preferred model is unavailable or fails. <br>**Accepted values:** `"gemini"`, `"groq"`, `"deepseek"` | `"gemini"`                                   |
| `max_description_length` | `integer` | No       | The maximum character length for AI-generated descriptions. Descriptions exceeding this length will be truncated. Defaults to `500` characters.                                                                                                                                         | `300`                                        |

**Example Request (JSON):**

```json
{
  "source_path": "https://github.com/AuditorEnvelope/lekhak_ai.git",
  "target_elements": ["repo", "module", "function", "class"],
  "output_format": "json",
  "llm_preference": "groq",
  "max_description_length": 400
}
```

#### Response Body

The response body will be a JSON object containing the generated documentation, structured hierarchically.

**Successful Response (Status: `200 OK`) - JSON Output Example:**

```json
{
  "status": "success",
  "llm_used_for_descriptions": "groq",
  "generated_at": "2023-10-27T10:30:00Z",
  "documentation": {
    "repo": {
      "name": "lekhak_ai",
      "description": "A comprehensive AI-powered documentation generation service that enriches code metadata and provides intelligent descriptions for various code elements.",
      "path": "https://github.com/AuditorEnvelope/lekhak_ai.git",
      "modules": {
        "hierarchical_doc_generator": {
          "name": "hierarchical_doc_generator",
          "path": "src/hierarchical_doc_generator.py",
          "description": "This module orchestrates the entire documentation generation process, integrating LLMs for description creation and advanced parsing for metadata extraction.",
          "functions": {
            "generate_documentation": {
              "name": "generate_documentation",
              "description": "Generates hierarchical documentation for a given source, including AI-powered descriptions and extracted code metadata.",
              "parameters": [
                {
                  "name": "source_path",
                  "type": "str",
                  "default": null,
                  "description": "Path to the code source (e.g., file, repo URL)."
                },
                {
                  "name": "output_format",
                  "type": "str",
                  "default": "'json'",
                  "description": "Desired output format ('json' or 'markdown')."
                },
                {
                  "name": "llm_preference",
                  "type": "Optional[str]",
                  "default": "None",
                  "description": "Preferred LLM for description generation."
                }
              ],
              "returns": {
                "type": "Dict[str, Any]",
                "description": "A dictionary containing the generated hierarchical documentation structure."
              }
            },
            "extract_function_details": {
              "name": "extract_function_details",
              "description": "Analyzes a function's signature to extract its parameters and return type.",
              "parameters": [
                {
                  "name": "function_node",
                  "type": "ASTNode",
                  "default": null,
                  "description": "The AST node representing the function in Python or TypeScript."
                }
              ],
              "returns": {
                "type": "Dict[str, Any]",
                "description": "A dictionary with parameter and return type details."
              }
            }
          },
          "classes": {
            "LLMRotator": {
              "name": "LLMRotator",
              "description": "Manages interaction with multiple LLM providers, ensuring graceful fallback and load balancing for description generation.",
              "methods": {
                "get_description": {
                  "name": "get_description",
                  "description": "Retrieves an AI-generated description for a given code snippet using the best available LLM.",
                  "parameters": [
                    {
                      "name": "code_snippet",
                      "type": "str",
                      "default": null,
                      "description": "The code snippet for which to generate a description."
                    },
                    {
                      "name": "context",
                      "type": "str",
                      "default": null,
                      "description": "Contextual information for the LLM to refine the description."
                    }
                  ],
                  "returns": {
                    "type": "str",
                    "description": "The AI-generated description, or a fallback if LLMs are unavailable."
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**Successful Response (Status: `200 OK`) - Markdown Output Example:**

If `output_format` is `"markdown"`, the `documentation` field will contain a string with Markdown formatted content.

```json
{
  "status": "success",
  "llm_used_for_descriptions": "groq",
  "generated_at": "2023-10-27T10:30:00Z",
  "documentation": "# Repository: Lekhak AI\n\nA comprehensive AI-powered documentation generation service that enriches code metadata and provides intelligent descriptions for various code elements.\n\n## Module: `hierarchical_doc_generator.py`\n\nThis module orchestrates the entire documentation generation process, integrating LLMs for description creation and advanced parsing for metadata extraction.\n\n### Functions:\n\n#### `generate_documentation(source_path: str, output_format: str = 'json', llm_preference: Optional[str] = None) -> Dict[str, Any]`\n\nGenerates hierarchical documentation for a given source, including AI-powered descriptions and extracted code metadata.\n\n- `source_path` (str): Path to the code source (e.g., file, repo URL).\n- `output_format` (str, default='json'): Desired output format ('json' or 'markdown').\n- `llm_preference` (Optional[str], default=None): Preferred LLM for description generation.\n\n**Returns:** A dictionary containing the generated hierarchical documentation structure.\n\n..."
}
```

#### Error Responses

Errors are returned as JSON objects with a `status` of `"error"`, an `code` for programmatic handling, and a human-readable `message`.

| Status Code               | Error Code                | Description                                                                                                                                                                                                         | Example Response                                                                                                                             |
| :------------------------ | :------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------- |
| `400 Bad Request`         | `INVALID_INPUT`           | The request body contains invalid or missing required parameters, or parameters with unsupported values.                                                                                                            | `{"status": "error", "code": "INVALID_INPUT", "message": "Missing required field 'source_path'."}`                                        |
| `401 Unauthorized`        | `UNAUTHENTICATED`         | No API key provided in the `Authorization` header, or the provided API key is invalid or expired.                                                                                                                   | `{"status": "error", "code": "UNAUTHENTICATED", "message": "Invalid API key provided."}`                                                    |
| `404 Not Found`           | `SOURCE_NOT_FOUND`        | The provided `source_path` could not be accessed, does not exist, or points to an unsupported resource (e.g., a private repository without sufficient credentials if local access is not configured).                  | `{"status": "error", "code": "SOURCE_NOT_FOUND", "message": "Repository or file at 'https://github.com/non-existent/repo.git' not found."}` |
| `429 Too Many Requests`   | `RATE_LIMIT_EXCEEDED`     | You have exceeded your API rate limit. This can also occur if the underlying LLM provider (Gemini, Groq, DeepSeek) imposes rate limits that are reached.                                                               | `{"status": "error", "code": "RATE_LIMIT_EXCEEDED", "message": "API rate limit exceeded. Please try again later."}`                       |
| `500 Internal Server Error` | `LLM_SERVICE_UNAVAILABLE` | All configured LLM services (Gemini, Groq, DeepSeek) are currently unavailable or failed to respond after multiple retries. <br>*Note: Due to the graceful fallback, basic descriptions will still be provided in the documentation.* | `{"status": "error", "code": "LLM_SERVICE_UNAVAILABLE", "message": "Failed to generate AI descriptions after multiple LLM retries. Basic documentation provided."}` |
| `500 Internal Server Error` | `CODE_PARSE_ERROR`        | An error occurred during the static analysis or parsing of the provided code source (e.g., malformed syntax, unsupported language construct).                                                                       | `{"status": "error", "code": "CODE_PARSE_ERROR", "message": "Failed to parse Python file at line 10: Unexpected token."}`                 |
| `500 Internal Server Error` | `UNKNOWN_ERROR`           | An unexpected internal server error occurred that is not covered by more specific error codes.                                                                                                                      | `{"status": "error", "code": "UNKNOWN_ERROR", "message": "An unexpected error occurred during documentation generation."}`                |

## Usage Examples

### 1. Generate JSON Documentation via cURL

```bash
curl -X POST \
  https://api.lekhak-ai.com/v1/docs/generate \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -d '{
    "source_path": "https://github.com/AuditorEnvelope/lekhak_ai.git",
    "target_elements": ["repo", "module", "function"],
    "llm_preference": "gemini",
    "max_description_length": 300
  }'
```

### 2. Generate Markdown Documentation (Python)

```python
import requests
import json
import os

# Replace with your actual API key
API_KEY = os.environ.get("LEKHAK_AI_API_KEY", "YOUR_API_KEY") 
BASE_URL = "https://api.lekhak-ai.com/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "source_path": "https://github.com/AuditorEnvelope/lekhak_ai.git",
    "target_elements": ["repo", "module", "class"],
    "output_format": "markdown",
    "llm_preference": "deepseek",
    "max_description_length": 500
}

try:
    response = requests.post(f"{BASE_URL}/docs/generate", headers=headers, data=json.dumps(payload))
    response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

    result = response.json()
    if result.get("status") == "success":
        print("Documentation Generated Successfully:")
        print(f"LLM used for descriptions: {result.get('llm_used_for_descriptions', 'N/A')}")
        print("\n--- Generated Markdown Documentation ---\n")
        print(result["documentation"]) # This will be the Markdown string
        print("\n----------------------------------------\n")
    else:
        print(f"Error generating documentation: {result.get('message', 'Unknown error')}")
        print(f"Error Code: {result.get('code', 'N/A')}")
        if 'documentation' in result:
             print("Partial documentation (without AI descriptions) might be available:")
             print(result['documentation']) # In case of LLM_SERVICE_UNAVAILABLE, this might still contain structured data
except requests.exceptions.HTTPError as err:
    print(f"HTTP Error: {err}")
    try:
        # Attempt to parse error details from response
        error_details = err.response.json()
        print(f"Server responded with error code: {error_details.get('code', 'N/A')}")
        print(f"Message: {error_details.get('message', 'No message')}")
    except json.JSONDecodeError:
        print(f"Server responded with: {err.response.text}") # Raw text if not JSON
except requests.exceptions.ConnectionError as err:
    print(f"Connection Error: Unable to connect to the API. {err}")
except requests.exceptions.Timeout as err:
    print(f"Timeout Error: The request timed out. {err}")
except requests.exceptions.RequestException as err:
    print(f"An unexpected error occurred during the request: {err}")

```

## Changelog

**Version 1.0 (October 27, 2023)**

*   **New Feature:** Introduced AI-powered description generation for all recognized code nodes (repository, SDK, module, feature, function, class) utilizing an intelligent LLM rotator (Gemini, Groq, DeepSeek).
*   **New Feature:** Implemented advanced static analysis for smart extraction of function parameters (including name, type, and default values) and return types from both Python and TypeScript function signatures.
*   **New Feature:** Added a robust graceful fallback mechanism to ensure documentation descriptions are always generated, even if LLM services are temporarily inaccessible or fail.
*   **Enhancement:** Significant improvements to internal code parsing logic for more accurate and comprehensive metadata extraction.
*   **API Endpoint:** `/v1/docs/generate` introduced for documentation generation.
*   **Request Parameters:** Added `llm_preference`, `target_elements`, and `max_description_length` to customize generation.
*   **Response Structure:** Enriched response with hierarchical documentation, AI-generated descriptions, extracted parameters, and return types.

---