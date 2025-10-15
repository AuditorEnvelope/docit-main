# API Documentation

*Updated: 2025-10-15*

Lekhak AI Service API Documentation
=====================================

### Introduction

The Lekhak AI Service is a robust architecture for contextual AI assistance in code. It integrates a commit bus for event processing, an indexing service leveraging a vector database (Milvus) for embeddings, and a RAG (Retrieval Augmented Generation) system to interact with various LLMs (Groq, OpenAI, Google Generative AI). This API documentation provides an overview of the new API endpoints, request/response formats, authentication requirements, usage examples, and error handling.

### API Endpoints

The following API endpoints are available:

#### 1. Commit Bus API

* **POST /commit**: Process a commit event
	+ Request Body: `{"commit_id": string, "commit_message": string, "code_changes": array}`
	+ Response: `{"commit_id": string, "status": string}`
* **GET /commits**: Retrieve a list of commit events
	+ Response: `[{"commit_id": string, "commit_message": string, "code_changes": array}]`

#### 2. Event Consumer API

* **POST /event**: Process an event
	+ Request Body: `{"event_id": string, "event_type": string, "event_data": object}`
	+ Response: `{"event_id": string, "status": string}`
* **GET /events**: Retrieve a list of events
	+ Response: `[{"event_id": string, "event_type": string, "event_data": object}]`

#### 3. Indexer Service API

* **POST /index**: Create an index for a codebase
	+ Request Body: `{"codebase_id": string, "codebase_data": object}`
	+ Response: `{"index_id": string, "status": string}`
* **GET /indexes**: Retrieve a list of indexes
	+ Response: `[{"index_id": string, "codebase_id": string, "codebase_data": object}]`

#### 4. RAG API

* **POST /rag**: Retrieve relevant context from Milvus
	+ Request Body: `{"query": string, "context_size": integer}`
	+ Response: `{"context": array, "status": string}`
* **GET /rag**: Retrieve a list of RAG queries
	+ Response: `[{"query": string, "context_size": integer, "context": array}]`

#### 5. LLM API

* **POST /llm**: Interact with a large language model
	+ Request Body: `{"llm_id": string, "input_text": string, "output_size": integer}`
	+ Response: `{"output_text": string, "status": string}`
* **GET /llms**: Retrieve a list of large language models
	+ Response: `[{"llm_id": string, "llm_name": string, "llm_description": string}]`

#### 6. Agent Service API

* **POST /agent**: Orchestrate AI tasks
	+ Request Body: `{"task_id": string, "task_type": string, "task_data": object}`
	+ Response: `{"task_id": string, "status": string}`
* **GET /agents**: Retrieve a list of AI tasks
	+ Response: `[{"task_id": string, "task_type": string, "task_data": object}]`

#### 7. Overlay Service API

* **POST /overlay**: Present AI-generated insights
	+ Request Body: `{"insight_id": string, "insight_data": object}`
	+ Response: `{"insight_id": string, "status": string}`
* **GET /overlays**: Retrieve a list of AI-generated insights
	+ Response: `[{"insight_id": string, "insight_data": object}]`

### Request/Response Formats

All API endpoints accept and return JSON data.

### Authentication Requirements

API endpoints require authentication using a JSON Web Token (JWT). The JWT token can be obtained by sending a POST request to the `/auth` endpoint with a valid username and password.

* **POST /auth**: Authenticate a user
	+ Request Body: `{"username": string, "password": string}`
	+ Response: `{"token": string, "status": string}`

### Usage Examples

#### 1. Process a commit event

```bash
curl -X POST \
  http://localhost:8000/commit \
  -H 'Content-Type: application/json' \
  -d '{"commit_id": "12345", "commit_message": "Initial commit", "code_changes": ["file1.py", "file2.py"]}'
```

#### 2. Retrieve a list of commit events

```bash
curl -X GET \
  http://localhost:8000/commits
```

#### 3. Create an index for a codebase

```bash
curl -X POST \
  http://localhost:8000/index \
  -H 'Content-Type: application/json' \
  -d '{"codebase_id": "12345", "codebase_data": {"language": "python", "files": ["file1.py", "file2.py"]}}'
```

#### 4. Retrieve relevant context from Milvus

```bash
curl -X POST \
  http://localhost:8000/rag \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the meaning of life?", "context_size": 10}'
```

#### 5. Interact with a large language model

```bash
curl -X POST \
  http://localhost:8000/llm \
  -H 'Content-Type: application/json' \
  -d '{"llm_id": "12345", "input_text": "Hello, world!", "output_size": 10}'
```

### Error Handling

API endpoints return error responses in the following format:

```json
{
  "error": {
    "code": integer,
    "message": string,
    "details": object
  }
}
```

Common error codes and messages:

* **401 Unauthorized**: Invalid or missing JWT token
* **404 Not Found**: Resource not found
* **500 Internal Server Error**: Server-side error

Note: This API documentation is subject to change as the Lekhak AI Service evolves.