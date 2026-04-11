#!/usr/bin/env python3
"""Test all 15 heuristic extractors against sample questions from test_questions.md."""
import sys
from heuristics import classify_and_extract

# ── Test cases: (question, expected_category, key_slots_check) ──
TESTS = [
    # 1. Fractions of a Whole
    (
        "¾ of the marbles = 60. Find the whole.",
        "fractions_whole",
        {"fraction_num": 3, "fraction_den": 4, "known_value": 60.0, "find": "whole"},
    ),
    # 2. Difference (More/Less)
    (
        "Ali has 45. Ali has 12 more than Ben. Find Ben.",
        "difference_more_less",
        {"known_entity": "Ali", "known_value": 45.0, "difference": 12.0, "more_entity": "Ali", "find": "Ben"},
    ),
    # 3. Multiple (Times as Many)
    (
        "Sam has 20. Tom has 3 times as many as Sam. Find Tom.",
        "multiple_times_as_many",
        {"multiplier": 3.0, "known_entity": "Sam", "known_value": 20.0, "find": "Tom"},
    ),
    # 4. Ratio
    (
        "The ratio of A to B is 3:5, total = 240. Find A and B.",
        "ratio",
        {"constraint_type": "total", "constraint_value": 240.0},
    ),
    # 5. Before-After
    (
        "Esther had $157, Fran had $100. Both spent the same on a blouse. After spending, ratio = 5:2. Find blouse cost.",
        "before_after",
        {"entities": ["Esther", "Fran"]},
    ),
    # 6. Equal Share (Excess/Shortage)
    (
        "Give 5 each → 3 left over. Give 8 each → 6 short. Find people & items.",
        "equal_share_excess_shortage",
        {"share_a": 5.0, "share_b": 8.0, "excess": 3.0, "shortage": 6.0},
    ),
    # 7. Grouping with Remainder
    (
        "47 items in groups of 5. Find number of groups.",
        "grouping_remainder",
        {"total": 47.0, "group_size": 5.0},
    ),
    # 8. Price × Quantity
    (
        "A pen costs $3. Buy 5 pens. Find total cost.",
        "price_quantity",
        {},  # just check category
    ),
    # 9. Coins / Notes
    (
        "$0.50 and $0.20 coins, total $5.00, 16 coins. Find count of each.",
        "coins_notes",
        {"total_value": 5.0, "total_count": 16.0},
    ),
    # 10. Speed–Distance–Time
    (
        "Speed = 60 km/h, time = 2.5h. Find distance.",
        "speed_distance_time",
        {"speed": 60.0, "time": 2.5, "find": "distance"},
    ),
    # 11. Work / Rate
    (
        "Worker A finishes alone in 6 hours, Worker B in 3 hours. Find combined time.",
        "work_rate",
        {"find": "combined_time"},
    ),
    # 12. Age
    (
        "Father is 40 years old now. In 5 years, the sum of their ages will be 55. Find the child's age.",
        "age",
        {"years_offset": 5.0, "condition_type": "sum"},
    ),
    # 13. Percentage Change
    (
        "Original = 200, increase by 25%. Find final value.",
        "percentage_change",
        {"original": 200.0, "percentage": 25.0, "direction": "increase", "find": "final"},
    ),
    # 14. Area / Perimeter
    (
        "Rectangle with length 12, width 8. Find area.",
        "area_perimeter",
        {"shape": "rectangle", "length": 12.0, "width": 8.0, "find": "area"},
    ),
    # 15. Two-Set Overlap (Venn)
    (
        "Soccer = 25, Tennis = 18, total students = 35. Find students in both.",
        "two_set_overlap",
        {"set_a": 25.0, "set_b": 18.0, "total": 35.0, "find": "both"},
    ),
]


def run_tests():
    passed = 0
    failed = 0
    for i, (question, expected_cat, key_checks) in enumerate(TESTS, 1):
        result = classify_and_extract(question)
        cat_name = expected_cat.upper().replace("_", " ")
        if result is None:
            print(f"  FAIL [{i:2d}] {cat_name}: returned None")
            failed += 1
            continue

        actual_cat = result["category"]
        slots = result["slots"]

        # Check category
        if actual_cat != expected_cat:
            print(f"  FAIL [{i:2d}] {cat_name}: expected '{expected_cat}', got '{actual_cat}'")
            failed += 1
            continue

        # Check key slots
        slot_ok = True
        for key, expected_val in key_checks.items():
            actual_val = slots.get(key)
            if actual_val != expected_val:
                print(f"  FAIL [{i:2d}] {cat_name}: slot '{key}' expected {expected_val}, got {actual_val}")
                slot_ok = False
        
        if slot_ok:
            print(f"  PASS [{i:2d}] {cat_name}")
            passed += 1
        else:
            failed += 1

    print(f"\n{'='*50}")
    print(f"  {passed}/{passed+failed} passed")
    if failed:
        print(f"  {failed} FAILED")
        return 1
    else:
        print("  All tests passed! ✅")
        return 0


if __name__ == "__main__":
    sys.exit(run_tests())
