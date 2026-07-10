from adhdolib.sanitize import clean

def test_control_chars_stripped():
    assert clean("hi\x1b[31m;`rm`\x07") == "hi[31m;`rm`"

def test_newlines_collapsed():
    assert clean("a\nb\r\nc") == "a\\nb\\nc"

def test_length_capped():
    assert len(clean("x" * 9000)) == 4000

def test_del_char_stripped():
    assert clean("a\x7fb") == "ab"
