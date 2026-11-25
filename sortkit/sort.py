"""Multi-key sorting helpers for dict-based records."""

from __future__ import annotations

from functools import cmp_to_key


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
        """Compare values ignoring direction (nulls handled by policy)."""
        left_is_null = self.value is None
        right_is_null = other.value is None
        if left_is_null or right_is_null:
            left_rank = null_rank(self.value, self.placement)
            right_rank = null_rank(other.value, other.placement)
            return (left_rank > right_rank) - (left_rank < right_rank)
        return _compare_values(self.value, other.value)

    def _compare(self, other):
        """Full comparison for this key, applying direction to values only."""
        if not isinstance(other, _Key):
            return NotImplemented
        # Null placement is absolute: it is not reversed by a descending key.
        if self.value is None or other.value is None:
            return self._base_compare(other)
        base = self._base_compare(other)
        if self.direction == "desc":
            return -base
        return base

    def __eq__(self, other):
        if not isinstance(other, _Key):
            return NotImplemented
        return self._compare(other) == 0

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __lt__(self, other):
        return self._compare(other) < 0

    def __le__(self, other):
        return self._compare(other) <= 0

    def __gt__(self, other):
        return self._compare(other) > 0

    def __ge__(self, other):
        return self._compare(other) >= 0

    def __hash__(self):
        # Equality is value based, so the hash must be too.
        return hash(self.value)

    def __repr__(self):
        return (
            f"_Key({self.value!r}, direction={self.direction!r}, "
            f"placement={self.placement!r})"
        )


def _compare_values(left, right):
    """Compare two non-null values: numbers numerically, strings by code point."""
    left_is_number = _is_number(left)
    right_is_number = _is_number(right)
    if left_is_number and right_is_number:
        return (left > right) - (left < right)
    if isinstance(left, str) and isinstance(right, str):
        return (left > right) - (left < right)
    # Mixed kinds get a deterministic, total order: numbers before strings,
    # and anything else ordered by its string representation.
    left_rank = 0 if left_is_number else 1
    right_rank = 0 if right_is_number else 1
    if left_rank != right_rank:
        return (left_rank > right_rank) - (left_rank < right_rank)
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
    """Return the ordering rank of a value with respect to null placement.

    ``None`` is ranked before every non-null value for ``first`` and after
    every non-null value for ``last``.  The rank is independent of the sort
    direction, so a descending key does not move nulls to the other end.
    """
    nulls_first = placement == "first"
    if value is None:
        return 0 if nulls_first else 1
    return 1 if nulls_first else 0


def _value_for(record, field):
    if isinstance(record, dict):
        return record.get(field)
    return getattr(record, field, None)


def key_for(record, spec):
    """Build the composite comparison key for one record."""
    parsed = parse_spec(spec)
    parts = []
    for entry in parsed:
        field = entry.get("field")
        direction = entry.get("direction", "asc")
        placement = entry.get("nulls", "last")
        parts.append(_Key(_value_for(record, field), direction, placement))
    return tuple(parts)


def _compare_keys(left, right):
    for left_key, right_key in zip(left, right):
        result = left_key._compare(right_key)
        if result:
            return result
    return 0


def compare_records(a, b, spec):
    """Compare two records under the given sort specification."""
    left = key_for(a, spec)
    right = key_for(b, spec)
    if not left and not right:
        return 0
    return _compare_keys(left, right)


def sort_records(records, spec):
    """Return a new, stably sorted list without mutating ``records``."""
    parsed = parse_spec(spec)
    items = list(records)
    return sorted(
        items,
        key=cmp_to_key(lambda a, b: _compare_keys(key_for(a, parsed), key_for(b, parsed))),
    )


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
    sequence = list(records)
    for index in range(len(sequence) - 1):
        if compare_records(sequence[index], sequence[index + 1], spec) > 0:
            return False
    return True


def sort_batch(batches, spec):
    """Sort each named batch of records independently."""
    return {name: sort_records(records, spec) for name, records in batches.items()}
