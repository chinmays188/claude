from app.knowledge.cleaner import clean_text


def test_collapses_excessive_blank_lines():
    result = clean_text("Line one.\n\n\n\n\nLine two.")

    assert result == "Line one.\n\nLine two."


def test_strips_control_characters():
    result = clean_text("Hello\x00World\x0b.")

    assert result == "HelloWorld."


def test_trims_trailing_whitespace_per_line():
    result = clean_text("Line one.   \nLine two.")

    assert result == "Line one.\nLine two."


def test_strips_leading_and_trailing_whitespace_overall():
    result = clean_text("\n\n  Hello.  \n\n")

    assert result == "Hello."
