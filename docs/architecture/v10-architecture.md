# Architecture v10

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
                                  |  (FastAPI)   |
                                  +---------------+
                                            |
                                            |
                                            v
                                  +---------------+
                                  |  database    |
                                  |  (asyncpg)    |
                                  +---------------+
                                            |
                                            |
                                            v
                                  +---------------+
                                  |  frontend    |
                                  |  (js, ts)     |
                                  +---------------+
```

## Actual Components Found
1. core
2. api
3. database
4. frontend

### core
- Purpose: The core component is the central part of the system, but its specific purpose is not clear from the provided analysis.
- Key Files: Not specified in the analysis.
- Dependencies: Not specified in the analysis, but the system uses python-dotenv, python-dateutil, and other dependencies listed in requirements.txt.

### api
- Purpose: The api component is built using FastAPI and handles API requests.
- Key Files: Not specified in the analysis, but it is likely related to the FastAPI framework.
- Dependencies: fastapi, uvicorn, PyJWT, PyGithub, and other dependencies listed in requirements.txt.

### database
- Purpose: The database component handles data storage and retrieval, using asyncpg for PostgreSQL database interactions.
- Key Files: Not specified in the analysis.
- Dependencies: asyncpg, pymilvus, and other dependencies listed in requirements.txt.

### frontend
- Purpose: The frontend component is responsible for the user interface, built using JavaScript and TypeScript.
- Key Files: Located in the ./pustak/public and ./pustak/src directories.
- Dependencies: Not specified in the analysis, but it is likely related to the JavaScript and TypeScript files in the frontend directories.

## Actual Technology Stack
1. Python (py)
2. JavaScript (js)
3. TypeScript (ts)
4. FastAPI
5. asyncpg
6. PostgreSQL
7. PyJWT
8. PyGithub
9. python-dotenv
10. python-dateutil
11. google-generativeai
12. groq
13. openai
14. requests
15. gitpython
16. pymilvus
17. sentence-transformers
18. pydantic
19. aiolimiter

## Design Patterns Detected
1. MVC (Model-View-Controller)
2. Repository Pattern

## Current Architecture
The system consists of four main components: core, api, database, and frontend. The api component, built using FastAPI, handles API requests and interacts with the database component, which uses asyncpg for PostgreSQL database interactions. The frontend component, built using JavaScript and TypeScript, is responsible for the user interface. The core component is the central part of the system, but its specific purpose is not clear from the provided analysis. The system follows the MVC and Repository patterns, and it uses a variety of dependencies to provide its functionality. Recently, the hierarchical documentation generation has been temporarily disabled due to performance issues, which has improved commit times and reduced LLM usage.