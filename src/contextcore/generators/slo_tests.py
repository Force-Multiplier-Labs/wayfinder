"""
Test feature: Hello Test

A simple test module to verify Prime Contractor workflow.
"""

def hello_test() -> str:
    """Return a test greeting."""
    return "Hello from test feature!"


def test_hello_test():
    """Test the hello function."""
    assert hello_test() == "Hello from test feature!"