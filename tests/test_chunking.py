from rpg_ai_server.redis.vector_memory import estimate_tokens, split_into_chunks


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 100) == 25


def test_empty_text():
    assert split_into_chunks("") == []
    assert split_into_chunks("   ") == []


def test_short_text_single_chunk():
    text = "The goblin dies."
    assert split_into_chunks(text) == [text]


def test_short_text_single_chunk_with_big_budget():
    text = "A sentence."
    assert split_into_chunks(text, max_tokens=10000) == [text]


def test_long_text_split_within_budget():
    sentences = [f"Sentence number {i} about goblins and dungeons." for i in range(40)]
    text = ". ".join(sentences)
    chunks = split_into_chunks(text, max_tokens=30)
    assert len(chunks) > 1
    for chunk in chunks:
        assert estimate_tokens(chunk) <= 30


def test_no_content_lost():
    sentences = [f"UniquePhrase{i} walks into a tavern." for i in range(50)]
    text = ". ".join(sentences)
    chunks = split_into_chunks(text, max_tokens=50)
    joined = " ".join(chunks)
    for s in sentences:
        assert s in joined


def test_hard_split_oversized_sentence():
    text = "x" * 400
    chunks = split_into_chunks(text, max_tokens=10)
    assert len(chunks) > 1
    assert all(estimate_tokens(c) <= 10 for c in chunks)


def test_overlap_preserved_between_chunks():
    sentences = [f"Chapter{i} of the long forgotten lore." for i in range(30)]
    text = ". ".join(sentences)
    chunks = split_into_chunks(text, max_tokens=30, overlap_tokens=8)
    assert len(chunks) > 1
    overlap_found = False
    for a, b in zip(chunks, chunks[1:]):
        shared = set(a.split()) & set(b.split())
        if shared:
            overlap_found = True
            break
    assert overlap_found


def test_overlap_capped_at_half_budget():
    chunks = split_into_chunks("A. B. C.", max_tokens=10, overlap_tokens=999)
    assert all(estimate_tokens(c) <= 10 for c in chunks)


def test_newlines_split():
    text = "First line.\nSecond line.\nThird line."
    chunks = split_into_chunks(text, max_tokens=3)
    assert len(chunks) >= 2
