# Architecture v6

## System Overview
```
                                  +---------------+
                                  |  pustak/src  |
                                  |  (frontend)  |
                                  +---------------+
                                            |
                                            |
                                            v
                                  +---------------+
                                  |  api (FastAPI) |
                                  |  (backend)     |
                                  +---------------+
                                            |
                                            |
                                            v
                                  +---------------+
                                  |  database      |
                                  |  (dependencies: |
                                  |   asyncpg, pymilvus)|
                                  +---------------+
                                            |
                                            |
                                            v
                                  +---------------+
                                  |  core (hierarchical|
                                  |   doc generator)    |
                                  +---------------+
```

## Actual Components Found
1. core
2. api
3. database
4. frontend (pustak)

### core
- Purpose: The core component contains the hierarchical document generator logic, which is responsible for parsing and generating documentation.
- Key Files: `src/hierarchical_doc_generator.py`, `src/main.py`
- Dependencies: `fastapi`, `uvicorn`, `PyJWT`, `PyGithub`, `python-dotenv`, `python-dateutil`, `google-generativeai`, `groq`, `openai`, `requests`, `gitpython`

### api
- Purpose: The api component is built using FastAPI and provides a backend interface for the system.
- Key Files: Not specified in the analysis
- Dependencies: `fastapi`, `uvicorn`

### database
- Purpose: The database component is responsible for storing and managing data, with dependencies on asyncpg and pymilvus.
- Key Files: Not specified in the analysis
- Dependencies: `asyncpg`, `pymilvus`

### frontend (pustak)
- Purpose: The frontend component is responsible for displaying the generated documentation, with a key file in `pustak/src/app/repo/[repoName]/[docType]/page.tsx`.
- Key Files: `pustak/src/app/repo/[repoName]/[docType]/page.tsx`
- Dependencies: Not specified in the analysis

## Actual Technology Stack
1. FastAPI
2. Uvicorn
3. PyJWT
4. PyGithub
5. python-dotenv
6. python-dateutil
7. google-generativeai
8. groq
9. openai
10. requests
11. gitpython
12. asyncpg
13. pymilvus
14. sentence-transformers
15. pydantic
16. aiolimiter
17. TypeScript (for frontend)

## Design Patterns Detected
1. MVC (Model-View-Controller)
2. Repository Pattern

## Current Architecture
The system consists of a core component that generates documentation using a hierarchical document generator. The api component provides a backend interface using FastAPI. The database component manages data storage using asyncpg and pymilvus. The frontend component displays the generated documentation. The system uses various dependencies, including FastAPI, Uvicorn, and PyJWT, and follows the MVC and Repository patterns. The recent introduction of recursive file detection depth control for doc parsing has improved the structure and performance of documentation generation.