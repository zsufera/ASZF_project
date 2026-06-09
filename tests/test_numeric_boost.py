from backend.retrieval import apply_numeric_boost


def test_numeric_boost_promotes_number_match():
    results = [
        {"chunk_id": "x", "quote": "általános szabályok", "paragrafus": "2.1", "score": 0.5},
        {"chunk_id": "y", "quote": "a felmondási idő 60 nap", "paragrafus": "7.3", "score": 0.45},
    ]
    out = apply_numeric_boost("60 napos felmondás", results)
    assert out[0]["chunk_id"] == "y"  # 0.45 + 0.1 = 0.55 > 0.5


def test_numeric_boost_matches_section_number():
    results = [
        {"chunk_id": "x", "quote": "általános", "paragrafus": "2.1", "score": 0.5},
        {"chunk_id": "y", "quote": "lásd az 5.5.1 pontot", "paragrafus": "5.5", "score": 0.45},
    ]
    out = apply_numeric_boost("mit mond az 5.5.1 pont", results)
    assert out[0]["chunk_id"] == "y"


def test_numeric_boost_noop_without_query_numbers():
    results = [{"chunk_id": "x", "quote": "szöveg", "paragrafus": "2", "score": 0.5}]
    assert apply_numeric_boost("felmondás szabályai", results) == results


def test_numeric_boost_ignores_single_digits():
    # az egyjegyű "5" túl gyakori → nem szignifikáns, nincs boost
    results = [{"chunk_id": "x", "quote": "a 5 pont", "paragrafus": "1", "score": 0.5}]
    out = apply_numeric_boost("5", results)
    assert out[0]["score"] == 0.5
