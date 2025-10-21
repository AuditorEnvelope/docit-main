# Architecture v8

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
                                  |  (asyncpg)   |
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
- Purpose: The core component is the central part of the system, but its specific purpose is not explicitly stated in the provided codebase analysis.
- Key Files: Not specified in the analysis.
- Dependencies: Not explicitly stated, but the system uses various dependencies listed in the `requirements.txt` file.

### api
- Purpose: The api component is built using FastAPI and is responsible for handling API requests.
- Key Files: Not specified in the analysis, but it's likely related to the `src` directory.
- Dependencies: FastAPI, uvicorn, and other dependencies listed in the `requirements.txt` file.

### database
- Purpose: The database component is used for data storage and is likely connected to the api component.
- Key Files: Not specified in the analysis.
- Dependencies: asyncpg, pymilvus, and other dependencies listed in the `requirements.txt` file.

### frontend
- Purpose: The frontend component is responsible for the user interface and is built using py, js, and ts.
- Key Files: Located in the `pustak` directory, specifically `pustak/public` and `pustak/src`.
- Dependencies: Not explicitly stated, but it's likely related to the dependencies listed in the `requirements.txt` file.

## Actual Technology Stack
1. Python (py)
2. JavaScript (js)
3. TypeScript (ts)
4. FastAPI
5. asyncpg
6. pymilvus
7. uvicorn

## Design Patterns Detected
1. MVC (Model-View-Controller)
2. Repository Pattern

## Current Architecture
The system consists of four main components: core, api, database, and frontend. The api component is built using FastAPI and handles API requests. The database component is used for data storage and is connected to the api component. The frontend component is responsible for the user interface and is built using py, js, and ts. The system uses various dependencies, including asyncpg, pymilvus, and uvicorn. The design patterns detected in the system are MVC and Repository Pattern. The recent changes introduced a comprehensive hierarchical caching mechanism for documentation generation, which significantly reduces the number of LLM calls required for incremental commits.