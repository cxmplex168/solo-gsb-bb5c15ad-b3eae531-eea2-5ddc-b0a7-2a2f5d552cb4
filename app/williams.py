"""Williams balanced Latin-square construction for crossover experiments.

For ``n`` distinct conditions the Williams design is a set of sequences such
that:

1. every condition appears the same number of times at each sequence position
   (first-order balance);
2. every directed adjacent pair ``A -> B`` appears the same number of times
   (first-order carry-over balance).

The complete sequence set contains ``n`` sequences when ``n`` is even and
``2n`` sequences when ``n`` is odd.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Sequence


def _base_row(n: int) -> List[int]:
    """First row of the Williams square, indices 0..n-1."""
    row: List[int] = []
    low, high = 0, n - 1
    while low <= high:
        row.append(high)
        high -= 1
        if low <= high:
            row.append(low)
            low += 1
    return row


def williams_square(n: int) -> List[List[int]]:
    """Return the Williams balanced sequence set as condition indices.

    Returns ``n`` sequences for even ``n`` and ``2n`` sequences for odd
    ``n`` (the second half is the mirror of the first, which is required for
    carry-over balance when ``n`` is odd).
    """
    if n < 2:
        raise ValueError("at least two distinct conditions are required")

    base = _base_row(n)
    sequences: List[List[int]] = []
    for shift in range(n):
        sequences.append([(value + shift) % n for value in base])

    if n % 2 == 1:
        # Mirror each row so that the reverse directed pairs are also covered.
        sequences.extend([list(reversed(row)) for row in sequences])

    return sequences


def group_size(n_conditions: int) -> int:
    """Number of subjects in one complete balanced block."""
    return n_conditions if n_conditions % 2 == 0 else 2 * n_conditions


def nearest_acceptable_subject_counts(
    n_conditions: int, requested: int
) -> tuple[int | None, int | None]:
    """Return the nearest acceptable subject counts below/above ``requested``.

    Acceptable counts are the positive multiples of :func:`group_size`.
    """
    size = group_size(n_conditions)
    if requested < size:
        return None, size
    lower = requested // size * size
    upper = lower + size
    if lower == requested:
        return requested, requested
    return lower, upper


@dataclass(frozen=True)
class Assignment:
    """One subject mapped to one concrete condition sequence."""

    subject_id: str
    sequence: List[str]


def assign_subjects(
    conditions: Sequence[str],
    subject_ids: Sequence[str],
    seed: int,
) -> List[Assignment]:
    """Map subjects to Williams sequences.

    The number of subjects must be a positive multiple of the block size
    (``n`` for even condition counts, ``2n`` for odd). Subjects are split into
    complete blocks; inside each block every canonical sequence is handed out
    exactly once. A seeded RNG shuffles both the subject order and the order in
    which sequences are dealt, so the same ``(conditions, subject_ids, seed)``
    triple always yields the same allocation while different seeds differ.
    """
    n = len(conditions)
    square_idx = williams_square(n)
    size = len(square_idx)  # n (even n) or 2n (odd n)

    if not subject_ids:
        raise ValueError("at least one subject is required")
    if len(subject_ids) % size != 0:
        raise ValueError("subject count must be a multiple of the block size")

    rng = random.Random(seed)

    # Sort subjects first so the seeded deal depends on the *set* of subjects,
    # not on the order in which the client happened to list them.
    subjects = sorted(subject_ids)
    rng.shuffle(subjects)

    assignments: List[Assignment] = []
    for block_start in range(0, len(subjects), size):
        block = subjects[block_start : block_start + size]
        order = list(range(size))
        rng.shuffle(order)
        for subject, seq_idx in zip(block, order):
            assignments.append(
                Assignment(
                    subject_id=subject,
                    sequence=[conditions[i] for i in square_idx[seq_idx]],
                )
            )
    return assignments
