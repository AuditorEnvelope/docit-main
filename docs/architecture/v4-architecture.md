# Architecture v4

## System Overview
```
                                  +---------------+
                                  |  core        |
                                  +---------------+
                                            |
                                            |
                                            v
                                  +---------------+
                                  |  api         |
                                  +---------------+
                                            |
                                            |
                                            v
                                  +---------------+
                                  |  database    |
                                  +---------------+
                                            |
                                            |
                                            v
                                  +---------------+
                                  |  frontend    |
                                  +---------------+
```

## Actual Components Found
1. core
2. api
3. database
4. frontend

### core
- Purpose: The core component is the central part of the system, responsible for the main application logic.
- Key Files: src/main.py, src/smart_processor.py
- Dependencies: fastapi, uvicorn, PyJWT, PyGithub, python-dotenv, python-dateutil, google-generativeai, groq, openai, requests, gitpython

### api
- Purpose: The api component handles incoming requests and sends responses.
- Key Files: Not specified
- Dependencies: fastapi, uvicorn

### database
- Purpose: The database component is responsible for storing and retrieving data.
- Key Files: Not specified
- Dependencies: asyncpg, pymilvus

### frontend
- Purpose: The frontend component is responsible for the user interface.
- Key Files: Not specified
- Dependencies: Not specified

## Actual Technology Stack
1. Python (py)
2. JavaScript (js)
3. TypeScript (ts)
4. FastAPI
5. Uvicorn
6. PyJWT
7. PyGithub
8. python-dotenv
9. python-dateutil
10. google-generativeai
11. groq
12. openai
13. requests
14. gitpython
15. asyncpg
16. pymilvus
17. sentence-transformers
18. pydantic
19. aiolimiter

## Design Patterns Detected
1. MVC (Model-View-Controller)
2. Repository Pattern

## Current Architecture
The system consists of four main components: core, api, database, and frontend. The core component is responsible for the main application logic and uses various dependencies such as fastapi, uvicorn, and PyJWT. The api component handles incoming requests and sends responses using fastapi and uvicorn. The database component stores and retrieves data using asyncpg and pymilvus. The frontend component is responsible for the user interface.

The system uses the MVC and Repository patterns to organize its code and ensure separation of concerns. The core component invokes the `hierarchical_doc_generator` module to generate hierarchical documentation automatically during application runtime and file processing. The `src/main.py` file triggers documentation generation upon application startup, and the `src/smart_processor.py` file calls the documentation generator during file processing.

The system's technology stack includes Python, JavaScript, and TypeScript, with various dependencies such as FastAPI, Uvicorn, and PyJWT. The system's architecture is designed to ensure efficient and scalable execution of its components and dependencies.