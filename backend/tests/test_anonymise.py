from __future__ import annotations

import random

from faker import Faker

from scripts.anonymise import _hash_asin, _make_alias


def test_hash_asin_stable() -> None:
    assert _hash_asin("B00X", "42") == _hash_asin("B00X", "42")
    assert _hash_asin("B00X", "42") != _hash_asin("B00X", "43")
    assert len(_hash_asin("B00X", "42")) == 16  # blake2s(digest_size=8) hex


def test_make_alias_unique() -> None:
    rng = random.Random(42)
    faker = Faker(); Faker.seed(42)
    used: set[str] = set()
    for cat in ("Home_and_Kitchen", "Pet_Supplies", "Health_and_Household"):
        for _ in range(20):
            alias = _make_alias(rng, cat, used, faker)
            assert alias not in used
            used.add(alias)
    assert len(used) == 60
