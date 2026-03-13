from app import app


def _filter(name):
    return app.jinja_env.filters[name]


def test_first_image_extracts_url():
    f = _filter("first_image")
    assert (
        f("Hello ![alt](https://img.example.com/pic.jpg) world")
        == "https://img.example.com/pic.jpg"
    )


def test_first_image_returns_empty_when_no_image():
    f = _filter("first_image")
    assert f("Hello world, no images here") == ""


def test_first_image_returns_first_of_multiple():
    f = _filter("first_image")
    text = "![a](https://one.jpg) then ![b](https://two.jpg)"
    assert f(text) == "https://one.jpg"


def test_strip_first_image_removes_only_first():
    f = _filter("strip_first_image")
    text = "Before ![a](https://one.jpg) middle ![b](https://two.jpg) after"
    result = f(text)
    assert "https://one.jpg" not in result
    assert "![b](https://two.jpg)" in result
    assert "Before" in result


def test_strip_first_image_no_image():
    f = _filter("strip_first_image")
    assert f("No images here") == "No images here"


def test_first_image_empty_input():
    f = _filter("first_image")
    assert f("") == ""
    assert f(None) == ""


def test_strip_first_image_empty_input():
    f = _filter("strip_first_image")
    assert f("") == ""
    assert f(None) is None
