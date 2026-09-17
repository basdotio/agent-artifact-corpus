---
name: code-be
description: Coding Standards for Backend Development
---

Here are the coding standards that everyone developing the backend should follow (Deviations from these standards can be made but they should be minimal, and should be verified by the user):

## Backend Code Structure
backend/ (Root folder: all imports in the code should be absolute and relative to this folder)
├── logs/
    ├── <date>_<time>.log
    ├── ...
├── routers/
    ├── <router-name>.py
    ├── ...
├── models/
    ├── sql.py
    ├── pydantic.py
    ├── ...
├── utils/
    ├── logger.py
    ├── ...
├── tests/
    ├── conftest.py
    ├── api/
        ├── test_<router-name>.py
        ├── ...
    ├── unit/
        ├── test_<unit-name>.py
        ├── ...
├── .env
├── .gitignore
├── config.py
├── main.py
├── pyproject.toml
├── README.md
├── run.sh
├── test.sh


## Ignored Files
- Apart from the standard python stuff, logs/, .env and .DS_Store should be ignored in .gitignore.

## Virtual Environment
- The environment should be managed by uv. use `uv sync` to install dependencies.
- The dependencies in pyproject.toml should be fixed to a specific version.
- Before using any package in the codebase, check if it is available in the pyproject.toml file. If not, add it to the pyproject.toml file and run `uv sync`.

## Formatting
- Ruff should be used to format the code.
- Isort should be used to sort the imports.
- The following should be present in the pyproject.toml to do both formatting and sorting
    [tool.ruff]
    select = ["E", "W", "F", "I", "C", "B"]

## Logging
- utils/logger.py should have a setup_logger function that uses loguru to create and return a logger object.
- The logger should log to a rotating file handler (that rotates daily) and to the console.
- setup_logger should create the logs folder if it doesn't exist.
- The log should have datetime, level, name, func, line, message.
- Log all the important events in the codebase.

## Configs
- Ask the user to create the .env file and fill in the values.
- config.py should have a pydantic settings class. It should read the environment variables from the .env file.
- Do not hardcode strings in the code, move them to the settings class and use from there.
- After instantiating the settings class, call the setup_logger function and create a logger object.
- This settings object and the logger object should be used throughout the project to ensure consistency.
- You can define any other global variables or objects in this file after creating the settings object.

## Scripts
- `run.sh` should run the app for development.
- `test.sh` should run all or selected tests.

## Main File
- main.py should instantiate a fastapi app and link all routers to it.
- the app should also have a startup and a shutdown function to perform any setup (before startup) or cleanup (after shutdown).
- the app should also have middlewares to log all requests and to handle general exceptions.
- the app should also have a health check endpoint at / GET.

## Routers
- Everything under an endpoint prefix should be defined in the same router file (routers/<router-name>.py)
- The endpoints definition functions should use pydantic models (defined in models/pydantic.py) for request validation.
- These functions should use the logger object (defined in config.py) for logging and settings object (defined in config.py) for accessing environment variables.
- All endpoints should return a consistent response format of {"data": <data>, "message": <message>} with an appropriate status code.
- All the business logic, db queries, logging, exception handling, should be done in the same endpoint definition function.
- For DB queries, use the transaction context manager (from the models/<db-type>.py folder) to ensure atomicity. If multiple queries exist, they should be executed within the same transaction.

## Models
- Request validation models for all the endpoints should be defined in models/pydantic.py.
- For SQL DB schema models, use the models/sql.py file. Define the declarative classes for each table. Use appropriate indexes, types and constraints for the columns.
- In the same models/<db-type>.py file, define the engine, sessionmaker and transaction context manager.
- These declarative classes should be used as the ORM models for the db queries.

## Tests
- Positive, negative and edge case API test cases for each router should be defined in tests/api/test_<router-name>.py.
- If you want to test some function separately, define the test cases in tests/unit/test_<function-name>.py.
- API tests should be simple - send a request to the endpoint and check the response.
- Any fixtures should be saved in tests/conftest.py.

## General Coding Guidelines
- All the function calls, db calls and api calls should be async.
- Do not create a variable if it is used only once, do the functionality inline.
- Do not create a function if it's code is used only in one place, write the code in the same place. If the same/similar code is used in multiple places, create a function.
- Simple code is better than complex. Complex is better than complicated.
- Flat structure is better than nested.
- Error handling should not be nested until the nested handler is explicitly silencing the error or raising the error above is absolutely necessary. Be careful as nested function calls can also have error handlers - Avoid that. Try to have only one error handler at the root level. This is to avoid silent failures deep in the codebase.
- There should be one, and preferably only one obvious way to do something.
- Avoid code comments until absolutely necessary. A user reading the code should be able to understand the code in itself.

## DevOps: Deployment and DB Migrations
- Deployment using docker and github actions will be mentioned in a separate skill.
- DB migrations using alembic will also be mentioned in a separate skill.

## Deviations from the Coding Standards
- You can create a separate folder for a module (in the root folder) that is complex and has a lot of functions and/or classes.