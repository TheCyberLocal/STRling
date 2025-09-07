import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from STRling.core.parser import parse

def test_hello():
    assert parse("test input") is not None