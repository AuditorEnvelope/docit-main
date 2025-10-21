# Architecture v9

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
- Key Files: Not specified in the analysis, but it is likely to be located in the `src` directory.
- Dependencies: Not specified in the analysis, but it may depend on other components like `api` and `database`.

### api
- Purpose: The api component is likely responsible for handling API requests and interactions, possibly using the FastAPI framework.
- Key Files: Not specified in the analysis, but it is likely to be located in the `src` directory.
- Dependencies: fastapi, uvicorn, PyJWT, PyGithub, python-dotenv, python-dateutil.

### database
- Purpose: The database component is responsible for managing data storage and retrieval, possibly using a database system like PostgreSQL (not explicitly mentioned, but asyncpg is listed as a dependency).
- Key Files: Not specified in the analysis, but it is likely to be located in the `src` directory.
- Dependencies: asyncpg.

### frontend
- Purpose: The frontend component is responsible for handling user interactions and presenting data to the user, possibly using JavaScript and TypeScript.
- Key Files: Located in the `pustak/public` and `pustak/src` directories.
- Dependencies: Not specified in the analysis, but it may depend on other components like `api`.

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
10. asyncpg
11. sentence-transformers
12. pydantic
13. aiolimiter

## Design Patterns Detected
1. MVC (Model-View-Controller)
2. Repository Pattern

## Current Architecture
The system consists of four main components: core, api, database, and frontend. The core component is the central part of the system, but its exact purpose is not specified. The api component handles API requests and interactions using the FastAPI framework. The database component manages data storage and retrieval, possibly using a database system like PostgreSQL. The frontend component handles user interactions and presents data to the user using JavaScript and TypeScript. The system uses various design patterns, including MVC and Repository Pattern, to organize and structure the code. The technology stack includes Python, JavaScript, TypeScript, FastAPI, Uvicorn, and other dependencies listed in the requirements.txt file.