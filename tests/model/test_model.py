import pytest
from functools import lru_cache
from root.model.model import Model


class TestModel:
    def init(*args, **kwargs):
        return Model(*args, **kwargs)