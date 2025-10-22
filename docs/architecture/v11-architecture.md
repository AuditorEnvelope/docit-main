# Architecture v11

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
- Purpose: The core component is the central part of the system, but its specific purpose is not explicitly stated in the provided analysis.
- Key Files: Not specified in the analysis, but it's likely to be in the `src` directory.
- Dependencies: Not explicitly stated, but it may depend on other components like `api` and `database`.

### api
- Purpose: The api component is built using FastAPI and is responsible for handling API requests.
- Key Files: Not specified in the analysis, but it's likely to be in the `src` directory.
- Dependencies: FastAPI, uvicorn, and other dependencies listed in the `requirements.txt` file.

### database
- Purpose: The database component is used for storing and retrieving data, and it uses asyncpg as the database driver.
- Key Files: Not specified in the analysis, but it's likely to be in the `src` directory.
- Dependencies: asyncpg and other dependencies listed in the `requirements.txt` file.

### frontend
- Purpose: The frontend component is responsible for user interaction and is built using Python, JavaScript, and TypeScript.
- Key Files: Not specified in the analysis, but it's likely to be in the `pustak` directory.
- Dependencies: Not explicitly stated, but it may depend on other components like `api` and `core`.

## Actual Technology Stack
1. Python (py)
2. JavaScript (js)
3. TypeScript (ts)
4. FastAPI
5. asyncpg
6. uvicorn

## Design Patterns Detected
1. MVC (Model-View-Controller)
2. Repository Pattern

## Current Architecture
The system consists of four main components: core, api, database, and frontend. The core component is the central part of the system, and it may depend on other components. The api component is built using FastAPI and handles API requests. The database component uses asyncpg as the database driver and is responsible for storing and retrieving data. The frontend component is responsible for user interaction and is built using Python, JavaScript, and TypeScript. The system uses the MVC and Repository patterns in its design. The recent bug fix resolved a critical `NameError` in the `smart_processor.py` file, which ensures that the event consumer can successfully call the documentation generation function.