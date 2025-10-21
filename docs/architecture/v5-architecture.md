# Architecture v5

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
                                  |  (FastAPI)    |
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
                                  |  (py, js, ts) |
                                  +---------------+
```

## Actual Components Found
1. core
2. api
3. database
4. frontend

### core
- Purpose: The core component is the foundation of the system, but its specific purpose is not explicitly stated in the analysis.
- Key Files: Not specified in the analysis.
- Dependencies: Not explicitly stated, but the system uses various dependencies listed in `requirements.txt`.

### api
- Purpose: The api component, built with FastAPI, handles API-related functionality.
- Key Files: Not specified in the analysis, but likely includes files within the `src` directory.
- Dependencies: FastAPI, uvicorn, and other dependencies listed in `requirements.txt`.

### database
- Purpose: The database component, utilizing asyncpg, manages data storage and retrieval.
- Key Files: Not specified in the analysis.
- Dependencies: asyncpg, and other dependencies related to database operations.

### frontend
- Purpose: The frontend component, using py, js, and ts, is responsible for the user interface and client-side logic.
- Key Files: Files within the `pustak/public` and `pustak/src` directories.
- Dependencies: Various dependencies listed in `requirements.txt`, including those for frontend development.

## Actual Technology Stack
1. FastAPI
2. asyncpg
3. Python (py)
4. JavaScript (js)
5. TypeScript (ts)
6. uvicorn
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
The system consists of four main components: core, api, database, and frontend. The core component serves as the foundation, while the api component, built with FastAPI, handles API-related functionality. The database component, utilizing asyncpg, manages data storage and retrieval. The frontend component, using py, js, and ts, is responsible for the user interface and client-side logic. The system employs the MVC and Repository patterns in its design. The technology stack includes a range of dependencies, from FastAPI and asyncpg to various libraries for frontend development and data processing.