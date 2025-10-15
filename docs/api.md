# API Documentation

## Overview
### API Purpose
The Lekhak AI API is designed to provide a comprehensive and reliable documentation generation service. It aims to assist developers in creating high-quality documentation for their projects, ensuring that the documentation is accurate, complete, and easy to understand.

### Base URL
The base URL for the Lekhak AI API is `https://api.lekhak.ai`.

### Authentication
To use the Lekhak AI API, you need to authenticate your requests using a valid API token. You can obtain an API token by registering on the Lekhak AI website and following the instructions in the dashboard. Once you have your API token, you can include it in your requests using the `Authorization` header with the format `Bearer YOUR_API_TOKEN`.

## Endpoints

### Endpoint 1: POST /generate-documentation
**Description**: This endpoint generates comprehensive documentation for a given project. It takes a JSON payload with the project details and returns a JSON response with the generated documentation.

**Request**:
```json
{
  "project_name": "string",
  "project_description": "string",
  "project_files": ["string"]
}
```

**Response**:
```json
{
  "documentation": "string"
}
```

**Errors**:
- 400: Bad Request (invalid payload or missing required fields)
- 401: Unauthorized (invalid or missing API token)
- 500: Internal Server Error (documentation generation failed)

### Endpoint 2: GET /health-check
**Description**: This endpoint checks the health and status of the Lekhak AI API.

**Request**: None

**Response**:
```json
{
  "status": "string"
}
```

**Errors**:
- 500: Internal Server Error (health check failed)

## Data Models
### Project Model
```json
{
  "project_name": "string",
  "project_description": "string",
  "project_files": ["string"]
}
```

### Documentation Model
```json
{
  "documentation": "string"
}
```

## Authentication
To authenticate your requests, you need to include a valid API token in the `Authorization` header. You can obtain an API token by registering on the Lekhak AI website and following the instructions in the dashboard.

### Token Management
API tokens are valid for a limited time and can be refreshed using the `POST /refresh-token` endpoint. To refresh your token, send a JSON payload with your current token and a new token will be generated and returned in the response.

## Rate Limiting
The Lekhak AI API has a rate limit of 100 requests per hour per IP address. If you exceed this limit, you will receive a 429 response with a `Retry-After` header indicating when you can make another request.

### Headers
The following headers are included in the response to help you manage rate limiting:
- `X-Rate-Limit-Limit`: The maximum number of requests allowed per hour.
- `X-Rate-Limit-Remaining`: The number of requests remaining in the current hour.
- `X-Rate-Limit-Reset`: The time when the rate limit will be reset.

## Examples
### Example 1: Generate Documentation
```bash
curl -X POST \
  https://api.lekhak.ai/generate-documentation \
  -H 'Authorization: Bearer YOUR_API_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
        "project_name": "My Project",
        "project_description": "This is my project",
        "project_files": ["file1.txt", "file2.txt"]
      }'
```

### Example 2: Health Check
```bash
curl -X GET \
  https://api.lekhak.ai/health-check
```

## SDKs & Libraries
The Lekhak AI API has SDKs available for the following programming languages:
- Python
- Java
- JavaScript

You can find the SDKs and usage examples on the Lekhak AI GitHub page.

### Python SDK Example
```python
import requests

api_token = "YOUR_API_TOKEN"
project_name = "My Project"
project_description = "This is my project"
project_files = ["file1.txt", "file2.txt"]

response = requests.post(
    "https://api.lekhak.ai/generate-documentation",
    headers={"Authorization": f"Bearer {api_token}"},
    json={"project_name": project_name, "project_description": project_description, "project_files": project_files}
)

if response.status_code == 200:
    print(response.json()["documentation"])
else:
    print(f"Error: {response.status_code}")
```