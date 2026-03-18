# LitePolis Database Template

This repository provides a template for creating custom database modules for the LitePolis system using `pyproject.toml` for modern Python packaging.

The example code within this template uses SQLModel and SQLite for demonstration purposes. **You will replace this specific implementation** with your chosen database technology (e.g., PostgreSQL, MySQL, MongoDB, Redis, etc.) and corresponding drivers or ORMs/ODMs (e.g., SQLAlchemy, Psycopg2, PyMongo, Django ORM, etc.).

## Key Files/Variables to Modify

* **Folder:** `litepolis_database_particiapi/` (Rename this to your package name using underscores, e.g., `litepolis_database_mymongodb`)
* **File:** `pyproject.toml` (Update `[project]` table: `name`, `version`, `dependencies`, `authors`, `description`, `urls`, etc.)
* **File:** `requirements.txt` (Optional: Pin development dependencies if needed)
* **File:** `litepolis_database_particiapi/utils.py` (Update `DEFAULT_CONFIG`, connection/session logic relevant to your DB)
* **File:** `litepolis_database_particiapi/Actor.py` (Update `DatabaseActor` implementation/inheritance)
* **File:** `litepolis_database_particiapi/__init__.py` (Update imports to expose your `DatabaseActor` and `DEFAULT_CONFIG`)
* **Files:** `litepolis_database_particiapi/Users.py`, `Conversations.py` (Delete or replace these example model/manager files)
* **Folder:** `tests/` (Rewrite tests for your implementation)
* **File:** `README.md` (This file! Update prerequisites, add specific notes for your implementation)

## Steps

Follow these steps to adapt the template:

1.  **Clone Repository:** Get a local copy of this template. You can use the CLI if you installed `litepolis` from PyPI
    ```bash
    litepolis-cli create database LitePolis-database-mymongodb
    ```
2.  **Update `pyproject.toml`:** Modify the `[project]` table:
    * Update `version`, `authors`, and `description`.
    * **Crucially, update `dependencies`**: List all libraries your module *requires* to run, including your chosen database driver/ORM (e.g., `"pymongo"`, `"psycopg2-binary"`, `"redis"`). **Remove `"sqlmodel"`** if you are not using the example implementation.
    * Update `[project.urls].Homepage`.
3.  **Install Dependencies:** Create a virtual environment and install the dependencies:
    ```bash
    python -m venv venv
    source venv/bin/activate # or venv\Scripts\activate on Windows
    # Install your package in editable mode (uses pyproject.toml)
    pip install -e .
    ```
4.  **Configure Database (`litepolis_database_particiapi/utils.py` or your renamed equivalent):**
    * Update `DEFAULT_CONFIG` with configuration keys and default values relevant to *your* database (e.g., connection string/URI, host, port, db name, credentials).
    * Implement the database connection logic (e.g., creating a client, engine, connection pool).
    * Implement session/connection handling functions or context managers suitable for your database and chosen access pattern.
    * Adapt the configuration loading logic (checking `PYTEST_CURRENT_TEST` vs. defaults) ensuring it reads from `DEFAULT_CONFIG` during tests.
5.  **Define Data Models:**
    * Replace the example model files (`Users.py`, `Conversations.py`) for your data models/schemas using your chosen tools (e.g., Pydantic models for MongoDB, SQLAlchemy models, Django models).
6.  **Implement Database Logic:**
    * Create "Manager" classes (or use another pattern) for your data models, containing methods for database operations (CRUD, queries, aggregations, etc.).
    * Update `litepolis_database_particiapi/Actor.py` (`DatabaseActor`) to utilize your Manager classes (e.g., through inheritance or composition). Remove the example inheritance (`UserManager`, `ConversationManager`). Remember, the class name **must remain `DatabaseActor`**.
7. **Write/Update Tests (`tests/`):**
    * Delete or heavily modify the existing example test files (`test_Users.py`, etc.).
    * Ensure proper test database setup/teardown procedures (e.g., using a separate test database, mocking, fixtures).
    * Run tests using `pytest`.
8. **Document Prerequisites:** Add any necessary setup instructions for *your specific database* to this README (e.g., "Requires a running PostgreSQL server accessible via connection string defined in config", "Ensure MongoDB is running on localhost:27017", "Redis server must be running").
9. **Release:** Once developed and tested, you can build and publish your package to PyPI using tools like `build` and `twine`.
    * `python -m build`
    * `twine upload dist/*`
    * Once your package is published on PyPI, the LitePolis CLI will be able to download and install it during the setup of other LitePolis services that depend on it.

## Global Concepts to Retain

While changing the implementation, retain these structural concepts:

* A central `DatabaseActor` class in `Actor.py` as the main entry point for LitePolis. **Do not rename this class.**
* Using a configuration dictionary (`DEFAULT_CONFIG` in `utils.py`) for database settings, exposed by your package's `__init__.py`.
* Having dedicated logic for database connection and session/client management (e.g., in `utils.py`).
* Organizing database logic for different models/collections into separate "Manager" classes (recommended pattern, but adaptable).
* Comprehensive testing using `pytest` (or equivalent) in the `tests/` directory.
* Standard Python packaging via `pyproject.toml` (PEP 621).

## Core Concepts

```mermaid
graph LR
    subgraph LitePolis
        A[LitePolis Core]
        Aa[LitePolis Modules]
    end
    subgraph Your Database Module (e.g., litepolis-database-mymongodb)
        A --> B(DatabaseActor)
        Aa --> B(DatabaseActor)
        B --> C[YourModelManager1]
        B --> D[YourModelManager2]
        B --> E[Connection/Utils]
        E --> F[DEFAULT_CONFIG]
    end
    C --> G[Your Database]
    D --> G
```