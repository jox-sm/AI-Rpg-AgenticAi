from rpg_ai_server.utils.compression import compress_text, decompress_text


def test_roundtrip():
    text = "The goblin chieftain raised its rusty axe and roared."
    assert decompress_text(compress_text(text)) == text


def test_unicode_roundtrip():
    text = "Crâne de dragon — 中文 이야기 العربية"
    assert decompress_text(compress_text(text)) == text


def test_empty_string_roundtrip():
    assert decompress_text(compress_text("")) == ""


def test_decompress_garbage_returns_none():
    assert decompress_text("not base64!!!") is None
    assert decompress_text("a=b=c!") is None


def test_compressed_is_smaller_for_long_text():
    long_text = ("The party presses deeper into the dungeon. " * 50)
    compressed = compress_text(long_text)
    assert len(compressed) < len(long_text)
