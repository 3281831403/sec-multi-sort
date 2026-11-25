"""Public tests for the multi-key sorting helpers."""

from sortkit import sort_batch, sort_records


def _key(field, direction="asc", nulls="last"):
    return {"field": field, "direction": direction, "nulls": nulls}


def _spec(field, direction="asc", nulls="last"):
    return [_key(field, direction, nulls)]


def test_single_key_ascending():
    records = [{"score": 10}, {"score": 2}, {"score": 1}]
    result = sort_records(records, _spec("score"))
    assert [item["score"] for item in result] == [1, 2, 10]


def test_two_key_combined_sort():
    records = [
        {"group": "a", "score": 2},
        {"group": "b", "score": 0},
        {"group": "a", "score": 1},
    ]
    spec = [_key("group"), _key("score")]
    result = sort_records(records, spec)
    assert [(item["group"], item["score"]) for item in result] == [
        ("a", 1),
        ("a", 2),
        ("b", 0),
    ]


def test_nulls_are_placed_last():
    records = [{"value": None}, {"value": 2}, {"value": 1}]
    result = sort_records(records, _spec("value", nulls="last"))
    assert [item["value"] for item in result] == [1, 2, None]


def test_descending_order():
    records = [{"value": 10}, {"value": 2}, {"value": 33}]
    result = sort_records(records, _spec("value", direction="desc"))
    assert [item["value"] for item in result] == [33, 10, 2]


def test_batch_sorting_is_independent_per_batch():
    batches = {
        "first": [{"value": 5}, {"value": 6}],
        "second": [{"value": 1}, {"value": 2}],
    }
    result = sort_batch(batches, _spec("value"))
    assert [item["value"] for item in result["first"]] == [5, 6]
    assert [item["value"] for item in result["second"]] == [1, 2]