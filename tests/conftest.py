import pytest
import database
import setup_db


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    """Create a fresh temporary database for every test."""
    test_db_path = tmp_path / "research.db"

    # Redirect both modules to the temporary database.
    monkeypatch.setattr(database, "DB_PATH", test_db_path)
    monkeypatch.setattr(setup_db, "DB_PATH", test_db_path)

    # Initialize the schema and sample data in the temporary database.
    setup_db.setup_database()

    yield test_db_path