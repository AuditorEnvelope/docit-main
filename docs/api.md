# API Documentation

*Updated: 2025-10-11*

API Documentation: Enhanced Documentation Generation and Analysis Capabilities
====================================================================

### Overview

The Enhanced Documentation Generation and Analysis Capabilities feature introduces significant changes to the documentation generation and analysis capabilities of the system. This API documentation outlines the new API endpoints, request/response formats, authentication requirements, usage examples, and error handling for the feature.

### New API Endpoints

The following new API endpoints have been added:

* **POST /github/push/events**: Triggers smart processing for GitHub push events, allowing for comprehensive change analysis and documentation creation.
* **GET /analysis**: Retrieves comprehensive change analysis results.
* **POST /documentation**: Creates documentation based on the analysis results.
* **GET /llm/providers**: Retrieves a list of available LLM providers.
* **POST /llm/providers**: Adds a new LLM provider.

### Request/Response Formats

The API endpoints use the following request/response formats:

* **JSON**: All API endpoints use JSON as the request and response format.
* **Content-Type**: The `Content-Type` header should be set to `application/json` for all API requests.

### Authentication Requirements

The API endpoints require the following authentication:

* **API Key**: An API key is required for all API requests. The API key should be passed in the `Authorization` header using the `Bearer` scheme.
* **GitHub Token**: A GitHub token is required for the **POST /github/push/events** endpoint. The GitHub token should be passed in the `GitHub-Token` header.

### Usage Examples

The following usage examples demonstrate how to use the new API endpoints:

#### Trigger Smart Processing for GitHub Push Events

```bash
curl -X POST \
  https://api.example.com/github/push/events \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'GitHub-Token: YOUR_GITHUB_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"event": "push", "repository": "example/repo"}'
```

#### Retrieve Comprehensive Change Analysis Results

```bash
curl -X GET \
  https://api.example.com/analysis \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json'
```

#### Create Documentation

```bash
curl -X POST \
  https://api.example.com/documentation \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"analysis_id": "example_analysis_id"}'
```

#### Retrieve Available LLM Providers

```bash
curl -X GET \
  https://api.example.com/llm/providers \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json'
```

#### Add a New LLM Provider

```bash
curl -X POST \
  https://api.example.com/llm/providers \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"provider_name": "example_provider", "provider_config": {"example_config": "example_value"}}'
```

### Error Handling

The API endpoints return the following error codes:

* **200 OK**: The request was successful.
* **401 Unauthorized**: The API key or GitHub token is invalid.
* **403 Forbidden**: The user does not have permission to access the endpoint.
* **404 Not Found**: The requested resource was not found.
* **500 Internal Server Error**: An internal server error occurred.

The API endpoints return error responses in the following format:

```json
{
  "error": {
    "code": 401,
    "message": "Invalid API key"
  }
}
```

### API Endpoint Documentation

#### POST /github/push/events

* **Description**: Triggers smart processing for GitHub push events, allowing for comprehensive change analysis and documentation creation.
* **Request Body**:
	+ `event`: The GitHub event type (e.g. `push`).
	+ `repository`: The GitHub repository name (e.g. `example/repo`).
* **Response**:
	+ `analysis_id`: The ID of the created analysis.
	+ `documentation_id`: The ID of the created documentation.

#### GET /analysis

* **Description**: Retrieves comprehensive change analysis results.
* **Response**:
	+ `analysis_results`: The analysis results.

#### POST /documentation

* **Description**: Creates documentation based on the analysis results.
* **Request Body**:
	+ `analysis_id`: The ID of the analysis.
* **Response**:
	+ `documentation_id`: The ID of the created documentation.

#### GET /llm/providers

* **Description**: Retrieves a list of available LLM providers.
* **Response**:
	+ `providers`: A list of available LLM providers.

#### POST /llm/providers

* **Description**: Adds a new LLM provider.
* **Request Body**:
	+ `provider_name`: The name of the LLM provider.
	+ `provider_config`: The configuration for the LLM provider.
* **Response**:
	+ `provider_id`: The ID of the created LLM provider.