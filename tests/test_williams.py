"""Property tests for the Williams design (stdlib only, run: python -m unittest)."""

from __future__ import annotations

import unittest
from collections import Counter
from itertools import product, permutations

from app.williams import (
    assign_subjects,
    group_size,
    nearest_acceptable_subject_counts,
    williams_square,
)


def is_balanced(n: int, sequences: list[list[int]]) -> None:
    """Assert positional and directed-pair balance of a complete block."""
    # Each condition equally often at each position (n_seqs / n times each).
    expected_per_position = len(sequences) // n
    for pos in range(n):
        counts = Counter(seq[pos] for seq in sequences)
        assert set(counts.values()) == {expected_per_position}, (n, pos, counts)
        assert len(counts) == n

    # Each directed adjacent pair occurs equally often.
    pair_counts: Counter[tuple[int, int]] = Counter()
    for seq in sequences:
        for a, b in zip(seq, seq[1:]):
            pair_counts[(a, b)] += 1
    expected_pairs = {(a, b) for a, b in product(range(n), repeat=2) if a != b}
    assert set(pair_counts) == expected_pairs, (n, set(pair_counts))
    assert len(set(pair_counts.values())) == 1, (n, pair_counts)


class WilliamsSquareTests(unittest.TestCase):
    def test_structure_size(self) -> None:
        for n in range(2, 13):
            square = williams_square(n)
            expected = n if n % 2 == 0 else 2 * n
            self.assertEqual(len(square), expected)
            for seq in square:
                self.assertEqual(sorted(seq), list(range(n)))

    def test_balance_even(self) -> None:
        for n in (2, 4, 6, 8, 10, 12):
            is_balanced(n, williams_square(n))

    def test_balance_odd(self) -> None:
        for n in (3, 5, 7, 9, 11):
            is_balanced(n, williams_square(n))

    def test_group_size(self) -> None:
        self.assertEqual(group_size(4), 4)
        self.assertEqual(group_size(5), 10)

    def test_nearest_counts(self) -> None:
        # n = 4 -> block size 4
        self.assertEqual(nearest_acceptable_subject_counts(4, 4), (4, 4))
        self.assertEqual(nearest_acceptable_subject_counts(4, 5), (4, 8))
        self.assertEqual(nearest_acceptable_subject_counts(4, 1), (None, 4))
        # n = 3 -> block size 6
        self.assertEqual(nearest_acceptable_subject_counts(3, 7), (6, 12))

    def test_assignment_deterministic(self) -> None:
        conditions = ["A", "B", "C", "D"]
        subjects = [f"S{i}" for i in range(8)]
        first = assign_subjects(conditions, subjects, seed=42)
        second = assign_subjects(conditions, subjects, seed=42)
        self.assertEqual(
            [(a.subject_id, a.sequence) for a in first],
            [(a.subject_id, a.sequence) for a in second],
        )
        # Input order independence: shuffling the subject list must not change
        # the resulting subject -> sequence mapping.
        shuffled_input = assign_subjects(
            conditions, list(reversed(subjects)), seed=42
        )
        self.assertEqual(
            sorted((a.subject_id, tuple(a.sequence)) for a in first),
            sorted((a.subject_id, tuple(a.sequence)) for a in shuffled_input),
        )
        # A different seed must plausibly change the deal.
        other_seed = assign_subjects(conditions, subjects, seed=43)
        changed = any(
            a.sequence != b.sequence
            for a, b in zip(
                sorted(first, key=lambda x: x.subject_id),
                sorted(other_seed, key=lambda x: x.subject_id),
            )
        )
        self.assertTrue(changed)
        # Every subject gets exactly one sequence.
        self.assertEqual(sorted(a.subject_id for a in first), sorted(subjects))

    def test_assignment_overall_balance(self) -> None:
        for n in range(2, 9):
            conditions = [f"C{i}" for i in range(n)]
            size = group_size(n)
            subjects = [f"S{i}" for i in range(size * 3)]
            assignments = assign_subjects(conditions, subjects, seed=7)
            # Across all subjects each canonical sequence appears equally often.
            seqs = Counter(tuple(a.sequence) for a in assignments)
            self.assertEqual(len(set(seqs.values())), 1)
            self.assertEqual(len(seqs), size)

    def test_invalid_subject_count_rejected(self) -> None:
        with self.assertRaises(ValueError):
            assign_subjects(["A", "B", "C", "D"], ["s1", "s2", "s3"], 1)

    def test_n2_known_design(self) -> None:
        square = williams_square(2)
        self.assertEqual(sorted(square), sorted([[0, 1], [1, 0]]))

    def test_balance_invariant_under_relabeling(self) -> None:
        # Balance is a structural property: any relabeling of conditions
        # preserves positional and directed-pair balance.
        for n in (3, 4):
            seqs = williams_square(n)
            for perm in permutations(range(n)):
                relabeled = [[perm[x] for x in seq] for seq in seqs]
                is_balanced(n, relabeled)


if __name__ == "__main__":
    unittest.main()
