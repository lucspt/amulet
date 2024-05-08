import pytest
from pathlib import Path
import pymongo

# General
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "omit: mark a test for omission, (deselect with -m \"not omit\")"
    )

@pytest.fixture
def get_class():
    def _class_wrap(cls):
        def _args_wrap(*args, **kwargs):
            return cls(*args, **kwargs)
        return _args_wrap
    return _class_wrap

# Database    
@pytest.fixture(scope="session")
def database():
    client = pymongo.MongoClient()
    yield client.edge
    client.close()

# Cleanup 
@pytest.fixture(scope="session")
def cleanup_files():
    files_to_clean = []
    def _cleanup_files(files):
        files_to_clean.extend(files)
    yield _cleanup_files
    [Path(p).unlink(missing_ok=True) for p in files_to_clean]
    