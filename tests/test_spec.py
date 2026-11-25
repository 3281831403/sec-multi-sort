"""Specification tests for the multi-key sorting helpers."""

import copy

from sortkit import compare_records, key_for, sort_batch, sort_records


def _key(field, direction="asc", nulls="last"):
    return {"field": field, "direction": direction, "nulls": nulls}


def test_multiple_keys_are_all_applied():
    records = [
        {"g": "b", "s": 1},
        {"g": "a", "s": 2},
        {"g": "a", "s": 1},
    ]
    result = sort_records(records, [_key("g"), _key("s")])
    assert [(r["g"], r["s"]) for r in result] == [("a", 1), ("a", 2), ("b", 1)]


def test_direction_applies_only_to_its_own_key():
    records = [
        {"g": "a", "s": 1},
        {"g": "b", "s": 2},
        {"g": "a", "s": 3},
    ]
    spec = [_key("g"), _key("s", direction="desc")]
    result = sort_records(records, spec)
    assert [(r["g"], r["s"]) for r in result] == [("a", 3), ("a", 1), ("b", 2)]


def test_numbers_compare_numerically_not_as_strings():
    records = [{"v": 9}, {"v": 10}, {"v": 2}, {"v": 100}]
    assert [r["v"] for r in sort_records(records, [_key("v")])] == [2, 9, 10, 100]


def test_strings_compare_by_code_point_not_length():
    records = [{"v": "b"}, {"v": "aa"}, {"v": "ab"}, {"v": "Z"}]
    assert [r["v"] for r in sort_records(records, [_key("v")])] == [
        "Z",
        "aa",
        "ab",
        "b",
    ]


def test_nulls_first_and_last_for_both_directions():
    records = [{"v": 2}, {"v": None}, {"v": 1}]
    assert [r["v"] for r in sort_records(records, [_key("v", nulls="first")])] == [
        None,
        1,
        2,
    ]
    assert [
        r["v"] for r in sort_records(records, [_key("v", "desc", nulls="first")])
    ] == [None, 2, 1]
    assert [
        r["v"] for r in sort_records(records, [_key("v", "desc", nulls="last")])
    ] == [2, 1, None]


def test_sorting_is_stable_for_equal_keys():
    records = [{"g": "a", "id": i} for i in range(5)]
    result = sort_records(records, [_key("g")])
    assert [r["id"] for r in result] == [0, 1, 2, 3, 4]

    mixed = [{"g": "b", "id": 0}, {"g": "a", "id": 1}, {"g": "b", "id": 2}]
    result = sort_records(mixed, [_key("g")])
    assert [r["id"] for r in result] == [1, 0, 2]


def test_input_list_is_not_modified():
    records = [{"v": 3}, {"v": 1}, {"v": 2}]
    original = copy.deepcopy(records)
    sort_records(records, [_key("v")])
    assert records == original


def test_sort_is_idempotent_and_preserves_records():
    records = [{"v": 2, "n": "x"}, {"v": None, "n": "y"}, {"v": 1, "n": "z"}]
    spec = [_key("v", "desc", nulls="last")]
    once = sort_records(records, spec)
    twice = sort_records(once, spec)
    assert once == twice
    assert len(once) == len(records)
    assert sorted(map(repr, once)) == sorted(map(repr, records))


def test_batches_are_sorted_independently():
    batches = {
        "a": [{"v": 3}, {"v": 1}],
        "b": [{"v": 4}, {"v": 2}],
    }
    result = sort_batch(batches, [_key("v")])
    assert [r["v"] for r in result["a"]] == [1, 3]
    assert [r["v"] for r in result["b"]] == [2, 4]


def test_compare_records_respects_each_keys_direction():
    a = {"g": "a", "s": 1}
    b = {"g": "a", "s": 2}
    spec = [_key("g"), _key("s", direction="desc")]
    assert compare_records(a, b, spec) > 0
    assert compare_records(b, a, spec) < 0


def test_key_for_uses_per_entry_direction_and_null_policy():
    left = key_for({"v": None}, [_key("v", nulls="first")])
    right = key_for({"v": 5}, [_key("v", nulls="first")])
    assert left < right
