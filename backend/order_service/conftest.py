import os
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(scope="session", autouse=True)
def mock_database_connection():
    """Mock database connection for unit tests that don't need real database."""
    with patch('app.db.engine') as mock_engine:
        with patch('app.db.SessionLocal') as mock_session:
            # Mock the database connection
            mock_connection = MagicMock()
            mock_engine.connect.return_value = mock_connection
            mock_engine.raw_connection.return_value = mock_connection
            
            # Mock the session
            mock_db_session = MagicMock()
            mock_session.return_value = mock_db_session
            
            yield mock_engine, mock_session
