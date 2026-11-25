"""Multi-key sorting helpers for dict-based records."""

from __future__ import annotations


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class _Key:
    """A single component of a composite sort key."""

    __slots__ = ("value", "direction", "placement")

    def __init__(self, value, direction, placement):
        self.value = value
        self.direction = direction
        self.placement = placement

    def _base_compare(self, other):
        left_is_null = self.value is None
        right_is_null = other.value is None
        if left_is_null or right_is_null:
            left_rank = null_rank(self.value, self.placement)
            right_rank = null_rank(other.value, other.placement)
            return (left_rank > right_rank) - (left_rank < right_rank)
        return _compare_values(self.value, other.value)

    def __eq__(self, other):
        if not isinstance(other, _Key):
            return NotImplemented
        return self._base_compare(other) == 0

    def __lt__(self, other):
        base = self._base_compare(other)
        if self.direction == "desc":
            return base > 0
        return base < 0

    def __hash__(self):
        return hash((self.value, self.direction, self.placement))

    def __repr__(self):
        return (
            f"_Key({self.value!r}, direction={self.direction!r}, "
            f"placement={self.placement!r})"
        )


def _compare_values(left, right):
    if _is_number(left) and _is_number(right):
        left, right = str(left), str(right)
    elif isinstance(left, str) and isinstance(right, str):
        left = (len(left), left)
        right = (len(right), right)
    else:
        left, right = str(left), str(right)
    return (left > right) - (left < right)


def parse_spec(spec):
    """Return a normalized list of sort-key descriptions."""
    if spec is None:
        return []
    if isinstance(spec, (str, dict)):
        spec = [spec]
    parsed = []
    for entry in spec:
        if isinstance(entry, str):
            parsed.append({"field": entry})
        elif isinstance(entry, dict):
            normalized = {}
            for name in ("field", "direction", "nulls"):
                if name in entry:
                    normalized[name] = entry[name]
            parsed.append(normalized)
        else:
            raise TypeError("sort keys must be strings or mappings")
    return parsed


def null_rank(value, placement):
    """Return the ordering rank of a value with respect to null placement."""
    if value is None:
        return 0
    return 1


def key_for(record, spec):
    """Build the composite comparison key for one record."""
    parsed = parse_spec(spec)
    if not parsed:
        return ()
    leading_direction = parsed[0].get("direction", "asc")
    parts = []
    for entry in parsed:
        field = entry.get("field")
        placement = entry.get("nulls", "last")
        if isinstance(record, dict):
            value = record.get(field)
        else:
            value = getattr(record, field, None)
        parts.append(_Key(value, leading_direction, placement))
    return tuple(parts)


def compare_records(a, b, spec):
    """Compare two records under the given sort specification."""
    left = key_for(a, spec)
    right = key_for(b, spec)
    if left < right:
        return -1
    if left > right:
        return 1
    return 0


def sort_records(records, spec):
    """Sort records by the given specification."""
    parsed = parse_spec(spec)
    effective = parsed[:1]
    records.sort(key=lambda record: key_for(record, effective))
    return records


def validate_spec(spec):
    """Return a list of problems found in a sort specification."""
    problems = []
    for index, entry in enumerate(parse_spec(spec)):
        if "direction" in entry and entry["direction"] not in ("asc", "desc"):
            problems.append(f"key {index}: invalid direction")
        if "nulls" not in entry:
            problems.append(f"key {index}: null placement is required")
        elif entry["nulls"] not in ("first", "last"):
            problems.append(f"key {index}: invalid null placement")
    return problems


def sort_stable_check(records, spec):
    """Return whether the records are in a stable sorted order."""
    if len(records) < 2:
        return True
    return compare_records(records[0], records[-1], spec) <= 0


def sort_batch(batches, spec):
    """Sort each named batch of records independently."""
    results = {}
    collected = []
    for name, records in batches.items():
        collected.extend(records)
        results[name] = sort_records(collected, spec)
    return results