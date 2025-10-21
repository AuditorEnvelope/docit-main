# Architecture v7

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
- Purpose: The core component is the central part of the system, but its exact purpose is not specified in the provided analysis.
- Key Files: Not specified in the analysis.
- Dependencies: Not specified in the analysis, but the system uses various dependencies listed in `requirements.txt`.

### api
- Purpose: The api component is likely responsible for handling API requests, given the presence of FastAPI in the dependencies.
- Key Files: Not specified in the analysis.
- Dependencies: fastapi, uvicorn, PyJWT, PyGithub, python-dotenv, python-dateutil, google-generativeai, groq, openai, requests, gitpython.

### database
- Purpose: The database component is responsible for storing and retrieving data, including AI-generated file descriptions.
- Key Files: Not specified in the analysis.
- Dependencies: asyncpg, pymilvus.

### frontend
- Purpose: The frontend component is likely responsible for handling user interactions and displaying data.
- Key Files: Not specified in the analysis, but it is located in the `./pustak` directory.
- Dependencies: Not specified in the analysis.

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
The system uses a combination of the MVC and Repository patterns to manage data and handle requests. The core component is the central part of the system, and it interacts with the api, database, and frontend components. The api component handles API requests using FastAPI and Uvicorn. The database component stores and retrieves data using asyncpg and pymilvus. The frontend component handles user interactions and displays data.

The system also uses an intelligent caching mechanism for AI-generated file descriptions, which reuses descriptions for unchanged files from previous commits. This optimization reduces LLM calls, generation time, and operational costs for incremental updates, achieving up to 10x speed improvement for subsequent runs. The caching mechanism is based on file changes detected using `git diff` and stores descriptions in an in-memory cache.