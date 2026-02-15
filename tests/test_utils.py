# tests/test_utils.py
from utils import is_valid_subdomain, slugify


def test_valid_subdomain():
    assert is_valid_subdomain("simon")
    assert is_valid_subdomain("my-site")
    assert not is_valid_subdomain("-bad")
    assert not is_valid_subdomain("no spaces")
    assert not is_valid_subdomain("AB")


def test_slugify():
    assert slugify("Hello World") == "hello-world"
    assert slugify("My First Post!") == "my-first-post"
