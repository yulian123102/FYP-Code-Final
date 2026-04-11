# heuristics.py — Regex-based classifiers + slot extractors for all 15 categories
# Fallback when OpenAI API key is not available.

import re
from typing import Optional, Tuple, Dict, List

# ── helpers ────────────────────────────────────────────────────────
_NUM = r"([-+]?\d+(?:\.\d+)?)"

# Words that start with a capital letter but are NOT person names.
# Used to prevent "In 5 years" from being parsed as entity "In" with value 5.
STOP_WORDS = {
    "In", "Find", "The", "After", "Before", "Both", "Each", "How", "What",
    "They", "Let", "Give", "Speed", "Worker", "Original", "Rectangle",
    "Square", "Triangle", "Total", "Ratio", "Area",
    "Perimeter", "Increase", "Decrease", "Distance", "Time", "Buy",
    "Cost", "Price", "Group", "Divide", "Split", "Sum",
}

def _float(s: str) -> Optional[float]:
    try:
        return float(s)
    except Exception:
        return None

def _clean(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_ ]+", "", s).strip()

def _find_names_values(text: str, limit: int = 4) -> List[Tuple[str, float]]:
    """Extract (Name, number) pairs like 'Ali has 45'."""
    pairs = re.findall(r"([A-Z][a-zA-Z]+)[^0-9\-+]*?" + _NUM, text)
    seen: Dict[str, float] = {}
    result = []
    for name, num in pairs:
        nm = _clean(name)
        if nm and nm not in seen and nm not in STOP_WORDS:
            v = _float(num)
            if v is not None:
                seen[nm] = v
                result.append((nm, v))
        if len(result) >= limit:
            break
    return result

def _all_numbers(text: str) -> List[float]:
    """All numbers in the text."""
    return [float(m) for m in re.findall(r"[-+]?\d+(?:\.\d+)?", text)]


# ═══════════════════════════════════════════════════════════════════
# 1. FRACTIONS OF A WHOLE
# ═══════════════════════════════════════════════════════════════════
def try_fractions_whole(text: str) -> Optional[dict]:
    t = text.lower()
    # Match patterns like "3/4 of the marbles = 60" or "¾ of"
    # Unicode fractions
    UNICODE_FRACS = {"½": (1,2), "⅓": (1,3), "⅔": (2,3), "¼": (1,4), "¾": (3,4),
                     "⅕": (1,5), "⅖": (2,5), "⅗": (3,5), "⅘": (4,5),
                     "⅙": (1,6), "⅚": (5,6), "⅛": (1,8), "⅜": (3,8), "⅝": (5,8), "⅞": (7,8)}

    num, den = None, None
    for uf, (n, d) in UNICODE_FRACS.items():
        if uf in text:
            num, den = n, d
            break

    if num is None:
        m = re.search(r"(\d+)\s*/\s*(\d+)", text)
        if m:
            num, den = int(m.group(1)), int(m.group(2))

    if num is None or den is None:
        return None

    # Need a keyword like "of the"
    if not re.search(r"\bof\b", t):
        return None

    # Find value
    nums = _all_numbers(text)
    # Filter out num and den themselves
    values = [v for v in nums if v != num and v != den and v > 0]
    if not values:
        return None
    known_value = values[0]

    # Entity
    entity_m = re.search(r"of\s+(?:the\s+)?([a-zA-Z]+)", t)
    entity = entity_m.group(1) if entity_m else "items"

    # Determine find: if text says "find the whole" or "how many ... in total" → whole
    find = "whole"
    if re.search(r"\bpart\b|\bhow many .{0,20} (are|is|were)\b", t):
        find = "part"

    return {
        "category": "fractions_whole",
        "confidence": 0.80,
        "slots": {
            "category": "fractions_whole",
            "entity": entity,
            "fraction_num": num,
            "fraction_den": den,
            "known_value": known_value,
            "find": find,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 2. DIFFERENCE (MORE / LESS)
# ═══════════════════════════════════════════════════════════════════
def try_difference(text: str) -> Optional[dict]:
    t = text
    # Pattern: "X has N more/less than Y"
    m = re.search(
        r"([A-Z][a-zA-Z]+).{0,40}\b(\d+(?:\.\d+)?)\s+(?:more|greater|extra)\s+(?:than)\s+([A-Z][a-zA-Z]+)",
        t, re.I)
    if m:
        more_ent = _clean(m.group(1))
        diff = float(m.group(2))
        other = _clean(m.group(3))
    else:
        m2 = re.search(
            r"([A-Z][a-zA-Z]+).{0,40}\b(\d+(?:\.\d+)?)\s+(?:less|fewer)\s+(?:than)\s+([A-Z][a-zA-Z]+)",
            t, re.I)
        if m2:
            other = _clean(m2.group(1))  # "less" entity
            diff = float(m2.group(2))
            more_ent = _clean(m2.group(3))
        else:
            return None

    # Find known value pair
    pairs = _find_names_values(text)
    known_entity, known_value = None, None
    entities = [more_ent, other]
    for name, val in pairs:
        if name in entities:
            known_entity = name
            known_value = val
            break

    if known_entity is None:
        return None

    find = other if known_entity == more_ent else more_ent

    return {
        "category": "difference_more_less",
        "confidence": 0.80,
        "slots": {
            "category": "difference_more_less",
            "entities": entities,
            "known_entity": known_entity,
            "known_value": known_value,
            "difference": diff,
            "more_entity": more_ent,
            "find": find,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 3. MULTIPLE (TIMES AS MANY)
# ═══════════════════════════════════════════════════════════════════
def try_multiple(text: str) -> Optional[dict]:
    t = text
    who_more = None
    multiplier = None
    other = None

    # "Tom has 3 times as many as Sam" — entity must be close to the multiplier
    m = re.search(
        r"([A-Z][a-zA-Z]+)\s+(?:has|had|have|owns?)\s+(\d+(?:\.\d+)?)\s*(?:×|times|x)\s+(?:as\s+(?:many|much)\s+as\s+)?([A-Z][a-zA-Z]+)",
        t, re.I)
    if m:
        who_more = _clean(m.group(1))
        multiplier = float(m.group(2))
        other = _clean(m.group(3))
    else:
        # "twice as many as"
        m2 = re.search(r"([A-Z][a-zA-Z]+).{0,20}\b(twice|thrice)\s+as\s+(?:many|much)\s+as\s+([A-Z][a-zA-Z]+)", t, re.I)
        if m2:
            who_more = _clean(m2.group(1))
            mult_word = m2.group(2).lower()
            other = _clean(m2.group(3))
            multiplier = 2.0 if mult_word == "twice" else 3.0
        else:
            return None

    # who_more has `multiplier` times as many as `other`
    # So if we know `other`'s value, find = who_more
    # If we know `who_more`'s value, find = other
    pairs = _find_names_values(text)
    known_entity, known_value = None, None
    entities = [who_more, other]
    for name, val in pairs:
        if name in entities:
            known_entity = name
            known_value = val
            break

    if known_entity is None:
        return None

    # The entity whose value is NOT known is what we find
    find = who_more if known_entity == other else other

    return {
        "category": "multiple_times_as_many",
        "confidence": 0.80,
        "slots": {
            "category": "multiple_times_as_many",
            "entities": entities,
            "multiplier": multiplier,
            "who_is_more": who_more,
            "known_entity": known_entity,
            "known_value": known_value,
            "find": find,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 4. RATIO
# ═══════════════════════════════════════════════════════════════════
def try_ratio(text: str) -> Optional[dict]:
    t = text
    if not re.search(r"\bratio\b|(\d+)\s*:\s*(\d+)", t, re.I):
        return None

    # Extract ratio values  "A:B = 3:5" or "ratio of A to B is 3:5"
    ratio_m = re.search(r"(\d+)\s*:\s*(\d+)", t)
    if not ratio_m:
        return None
    r1, r2 = float(ratio_m.group(1)), float(ratio_m.group(2))

    # Extract entity names
    # Try "ratio of A to B"
    names_m = re.search(r"([A-Z][a-zA-Z]+)\s*(?:to|and)\s*([A-Z][a-zA-Z]+)", t)
    if names_m:
        entities = [_clean(names_m.group(1)), _clean(names_m.group(2))]
    else:
        # Try "A:B" preceded by names — or just use labels
        entities = ["A", "B"]

    ratio = {entities[0]: r1, entities[1]: r2}

    # Constraint: "total = N" or "difference = N" or "A = N"
    nums = _all_numbers(text)
    # Remove ratio numbers
    other_nums = [n for n in nums if n != r1 and n != r2]

    constraint_type = "total"
    constraint_value = other_nums[0] if other_nums else 0
    constraint_entity = None

    if re.search(r"\bdifference\b", t, re.I):
        constraint_type = "difference"
    elif re.search(r"\btotal\b|\bsum\b|\ball together\b", t, re.I):
        constraint_type = "total"
    else:
        # Check if a specific entity value is given
        pairs = _find_names_values(text)
        for name, val in pairs:
            if name in entities and val not in [r1, r2]:
                constraint_type = "one_known"
                constraint_value = val
                constraint_entity = name
                break

    if constraint_value == 0:
        return None

    return {
        "category": "ratio",
        "confidence": 0.80,
        "slots": {
            "category": "ratio",
            "entities": entities,
            "ratio": ratio,
            "constraint_type": constraint_type,
            "constraint_value": constraint_value,
            "constraint_entity": constraint_entity,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 5. BEFORE–AFTER (spend_equal / transfer)
# ═══════════════════════════════════════════════════════════════════
def try_before_after(text: str) -> Optional[dict]:
    t = text.replace("\n", " ")
    # Must have a spend/transfer/give keyword to qualify
    if not re.search(r"\b(spend|spent|buy|bought|give|gave|transfer|same amount|equal amount)\b", t, re.I):
        return None

    # Find names & initial amounts
    pairs = _find_names_values(t, 2)
    if len(pairs) != 2:
        return None

    entities = [p[0] for p in pairs]
    before = {p[0]: p[1] for p in pairs}

    # Ratio like "ratio ... 5:2" or "5 to 2"
    ratio_m = re.search(r"(\d+)\s*[:to]\s*(\d+)", t)
    if not ratio_m:
        return None
    a = float(ratio_m.group(1))
    b = float(ratio_m.group(2))
    ratio = {entities[0]: a, entities[1]: b}

    # Determine action
    if re.search(r"\b(spend|spent|buy|bought|same amount|equal amount)\b", t, re.I):
        action = {"type": "spend_equal", "actor_from": None, "actor_to": None, "amount": "unknown"}
    else:
        transf = re.search(
            r"([A-Z][a-zA-Z]+).{0,30}\b(give|gave|gives|transfer|transferred)\b.{0,30}([A-Z][a-zA-Z]+)",
            t, re.I)
        if transf:
            action = {"type": "transfer", "actor_from": _clean(transf.group(1)),
                       "actor_to": _clean(transf.group(3)), "amount": "unknown"}
        else:
            action = {"type": "spend_equal", "actor_from": None, "actor_to": None, "amount": "unknown"}

    return {
        "category": "before_after",
        "confidence": 0.85,
        "slots": {
            "category": "before_after",
            "entities": entities,
            "before": before,
            "after_relation": {"type": "ratio", "ratio": ratio},
            "actions": [action],
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 6. EQUAL SHARE WITH EXCESS / SHORTAGE
# ═══════════════════════════════════════════════════════════════════
def try_equal_share(text: str) -> Optional[dict]:
    t = text.lower()
    # "give 5 each → 3 left over. give 8 each → 6 short"
    if not (re.search(r"each|per person", t) and
            (re.search(r"left|over|excess|remain", t) or re.search(r"short|shortage|not enough", t))):
        return None

    nums = _all_numbers(text)
    if len(nums) < 4:
        return None

    # Pattern: share_a, excess, share_b, shortage
    share_a = nums[0]
    excess = nums[1]
    share_b = nums[2]
    shortage = nums[3]

    return {
        "category": "equal_share_excess_shortage",
        "confidence": 0.80,
        "slots": {
            "category": "equal_share_excess_shortage",
            "share_a": share_a,
            "share_b": share_b,
            "excess": excess,
            "shortage": shortage,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 7. GROUPING WITH REMAINDER
# ═══════════════════════════════════════════════════════════════════
def try_grouping(text: str) -> Optional[dict]:
    t = text.lower()
    if not re.search(r"group|divide|split|arrange|remainder|left over", t):
        return None

    nums = _all_numbers(text)
    if len(nums) < 2:
        return None

    # "47 items in groups of 5" → total=47, group_size=5
    # Try to detect explicit pattern
    m = re.search(r"(\d+)\s*(?:items?|things?|objects?|people)?.{0,20}(?:group|divide|split).{0,10}(\d+)", t)
    if m:
        total = float(m.group(1))
        group_size = float(m.group(2))
    else:
        total = nums[0]
        group_size = nums[1]

    remainder = total % group_size

    find = "groups"
    if re.search(r"(find|how many).{0,15}(total|altogether)", t):
        find = "total"
    elif re.search(r"minimum|smallest|least", t):
        find = "min_total"

    return {
        "category": "grouping_remainder",
        "confidence": 0.80,
        "slots": {
            "category": "grouping_remainder",
            "total": total,
            "group_size": group_size,
            "remainder": remainder,
            "find": find,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 8. PRICE × QUANTITY
# ═══════════════════════════════════════════════════════════════════
def try_price_quantity(text: str) -> Optional[dict]:
    t = text.lower()
    if not re.search(r"cost|price|\$|buy|bought|purchase|each|per\b", t):
        return None

    items = []

    # Pattern 1: "costs $10" / "price is $10" / "$10 each"
    price_matches = re.findall(
        r"([a-zA-Z]+)\s+(?:costs?|priced?)\s+\$?\s*(\d+(?:\.\d+)?)", text, re.I)
    if not price_matches:
        # "$10 each" or "$10 per item"
        price_matches = re.findall(
            r"([a-zA-Z]+).{0,15}\$\s*(\d+(?:\.\d+)?)", text, re.I)
    if not price_matches:
        # Try dollar first: "$10, buy 3"
        dm = re.search(r"\$\s*(\d+(?:\.\d+)?)", text)
        if dm:
            price_matches = [('item', dm.group(1))]

    for name, price in price_matches:
        nm = _clean(name)
        if nm.lower() in ('buy', 'bought', 'find', 'the', 'a', 'an', 'each', 'per', 'total'):
            nm = 'item'
        items.append({"name": nm, "unit_price": float(price), "quantity": None, "total": None})

    if not items:
        # Simpler: just extract numbers assuming price then quantity
        nums = _all_numbers(text)
        if len(nums) >= 2:
            items.append({"name": "item", "unit_price": nums[0], "quantity": nums[1], "total": None})

    if not items:
        return None

    # Try to fill quantity from text
    for it in items:
        if it["quantity"] is None:
            qm = re.search(r"(?:buy|bought|purchase|quantity)\s+(?:of\s+)?(\d+)", text, re.I)
            if qm:
                it["quantity"] = float(qm.group(1))
            else:
                nums = _all_numbers(text)
                # Use a number that isn't the price
                for n in nums:
                    if n != it["unit_price"]:
                        it["quantity"] = n
                        break

    return {
        "category": "price_quantity",
        "confidence": 0.75,
        "slots": {
            "category": "price_quantity",
            "items": items,
            "find": "total_cost",
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 9. COINS / NOTES
# ═══════════════════════════════════════════════════════════════════
def try_coins_notes(text: str) -> Optional[dict]:
    t = text.lower()
    if not re.search(r"coin|note|denomination|cent", t):
        return None

    nums = _all_numbers(text)
    if len(nums) < 3:
        return None

    # "$0.50 and $0.20 coins, total $5.00, 16 coins"
    # Try to extract denominations (small values) vs total value (larger)
    denoms = []
    total_value = None
    total_count = None

    # Look for total count FIRST (to avoid matching denomination digits)
    # Match patterns like "16 coins" but NOT "$0.20 coins" (preceded by $)
    count_m = re.search(r"(?<!\.)(?<!\$)\b(\d+)\s+(?:coins?|notes?|bills?)\b", t)
    if count_m:
        total_count = float(count_m.group(1))

    # Look for dollar-formatted denominations
    denom_matches = re.findall(r"\$\s*(\d+(?:\.\d+)?)", text)
    if denom_matches:
        vals = [float(v) for v in denom_matches]
        # Heuristic: the largest is the total value, smaller are denominations
        vals.sort()
        if len(vals) >= 3:
            denoms = vals[:-1]
            total_value = vals[-1]
        elif len(vals) == 2:
            denoms = [vals[0]]
            total_value = vals[1]

    if not denoms or total_value is None:
        return None

    return {
        "category": "coins_notes",
        "confidence": 0.80,
        "slots": {
            "category": "coins_notes",
            "denominations": denoms,
            "total_value": total_value,
            "total_count": total_count,
            "known_counts": None,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 10. SPEED–DISTANCE–TIME
# ═══════════════════════════════════════════════════════════════════
def try_speed_distance_time(text: str) -> Optional[dict]:
    t = text.lower()
    if not re.search(r"speed|km/?h|mph|m/s|distance|travel|drove|walk|run|cycle", t):
        return None

    speed = None
    distance = None
    time = None

    # "speed = 60 km/h" or "60 km/h"
    # First try unit-based match (most specific)
    sm2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:km/?h|mph|m/?s)", t)
    if sm2:
        speed = float(sm2.group(1))
    else:
        # "speed = 60" or "speed is 60"
        sm = re.search(r"(?:speed|rate|velocity)\s*(?:=|is|of)?\s*(\d+(?:\.\d+)?)", t)
        if sm:
            speed = float(sm.group(1))

    # "distance = 150 km" or "150 km"
    dm = re.search(r"(?:distance).{0,10}(\d+(?:\.\d+)?)", t)
    if dm:
        distance = float(dm.group(1))
    else:
        dm2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:km|miles?|m|metres?|meters?)\b", t)
        if dm2 and float(dm2.group(1)) != speed:
            distance = float(dm2.group(1))

    # "time = 2.5 hours" or "2.5h"
    # First try unit-based match
    tm2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b", t)
    if tm2:
        val = float(tm2.group(1))
        # Don't accidentally grab the speed value
        if val != speed:
            time = val
    if time is None:
        tm = re.search(r"(?:time|duration)\s*(?:=|is|of)?\s*(\d+(?:\.\d+)?)", t)
        if tm:
            time = float(tm.group(1))
    if time is None:
        tm3 = re.search(r"(\d+(?:\.\d+)?)\s*(?:minutes?|mins?)\b", t)
        if tm3:
            time = float(tm3.group(1))

    # Determine what to find
    find = None
    known_count = sum(1 for v in [speed, distance, time] if v is not None)
    if known_count < 2:
        return None

    if re.search(r"find.{0,10}distance|how far", t):
        find = "distance"
    elif re.search(r"find.{0,10}speed|how fast", t):
        find = "speed"
    elif re.search(r"find.{0,10}time|how long", t):
        find = "time"
    else:
        # Infer: the missing one is what we find
        if distance is None:
            find = "distance"
        elif speed is None:
            find = "speed"
        else:
            find = "time"

    return {
        "category": "speed_distance_time",
        "confidence": 0.80,
        "slots": {
            "category": "speed_distance_time",
            "speed": speed,
            "distance": distance,
            "time": time,
            "find": find,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 11. WORK / RATE
# ═══════════════════════════════════════════════════════════════════
def try_work_rate(text: str) -> Optional[dict]:
    t = text.lower()
    if not re.search(r"work|finish|complete|alone|together|hour|day|take", t):
        return None

    # Common words to skip when looking for worker names
    _SKIP_WORDS = {"worker", "person", "man", "woman", "pipe", "tap", "machine",
                   "find", "the", "in", "if", "it", "is", "and", "or", "for",
                   "how", "each", "both", "combined", "finishes", "takes",
                   "completes", "alone"}

    # First try named pattern: "Worker A finishes in 6 hours, Worker B in 3 hours"
    named_matches = re.findall(
        r"(?:worker|pipe|tap|machine|person)\s+([A-Z][a-zA-Z]*)\b.{0,30}(?:finish|complete|take|do|alone|in)\s*(?:in\s+)?(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h\b|days?|d\b)",
        text, re.I)

    if len(named_matches) >= 2:
        matches = named_matches
    else:
        # "A finishes alone in 6h, B in 3h"
        # Strategy: first find the worker who has a verb, then find subsequent
        # "Name ... number + time-unit" pairs that may lack a verb.
        matches = re.findall(
            r"([A-Z][a-zA-Z]*).{0,30}(?:finish|complete|take|do).{0,15}(?:alone\s+)?(?:in\s+)?(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h\b|days?|d\b)",
            text, re.I)

        # Also look for shorter patterns like "B in 3h" (no verb)
        # Use a two-step approach: find "LETTER in/takes NUMBER unit" patterns
        # but only at word boundaries (after comma, start, etc.) to avoid mid-word matches
        short_matches = re.findall(
            r"(?:^|[,;.]\s*)([A-Z])(?=\s+(?:in|takes?)\s+\d)",
            text)
        for letter in short_matches:
            # Now extract the time for this letter
            tm = re.search(
                re.escape(letter) + r"\s+(?:in|takes?)\s+(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h\b|days?|d\b)",
                text, re.I)
            if tm:
                pair = (letter, tm.group(1))
                if pair not in matches:
                    matches.append(pair)

        if len(matches) < 2:
            # Broadest: any "SingleLetter/Name ...number + time-unit" pairs
            matches = re.findall(
                r"([A-Z][a-zA-Z]*)\s.{0,20}?(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h\b|days?|d\b)",
                text, re.I)

    if len(matches) < 2:
        return None

    workers = []
    individual_times = {}
    for name, hrs in matches[:4]:
        nm = _clean(name)
        # Skip common non-name words
        if nm and nm.lower() not in _SKIP_WORDS and nm not in individual_times:
            workers.append(nm)
            individual_times[nm] = float(hrs)

    if len(workers) < 2:
        return None

    find = "combined_time"
    if re.search(r"find.{0,10}individual|how long.{0,10}alone", t):
        find = "individual_time"

    return {
        "category": "work_rate",
        "confidence": 0.80,
        "slots": {
            "category": "work_rate",
            "workers": workers,
            "individual_times": individual_times,
            "find": find,
            "combined_time": None,
            "find_worker": None,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 12. AGE
# ═══════════════════════════════════════════════════════════════════
def try_age(text: str) -> Optional[dict]:
    t = text.lower()
    if not re.search(r"age|years?\s*old|\bin\s+\d+\s+years?\b|years?\s*(?:from now|ago|later|time)|twice|thrice|half", t):
        return None

    # Find "{Name} is {N} years old" or "{Name} is {N}"
    pairs = _find_names_values(text)
    if not pairs:
        return None

    entities = []
    ages_now: Dict[str, Optional[float]] = {}

    for name, val in pairs[:2]:
        entities.append(name)
        ages_now[name] = val

    # If only one entity found, assume there's an unknown entity
    if len(entities) == 1:
        # Try to find second name
        all_names = re.findall(r"([A-Z][a-zA-Z]+)", text)
        for nm in all_names:
            nm = _clean(nm)
            if nm and nm not in entities and nm not in STOP_WORDS and nm.lower() not in ("find", "in", "the", "his", "her", "how"):
                entities.append(nm)
                ages_now[nm] = None
                break
        if len(entities) == 1:
            entities.append("child")
            ages_now["child"] = None

    # Years offset: "in 5 years" → +5, "5 years ago" → -5
    # BUT if the question asks "in how many years" the offset is UNKNOWN
    ask_offset = bool(re.search(r"(?:in\s+)?how\s+many\s+years|after\s+how\s+many\s+years", t))
    offset_m = re.search(r"\bin\s+(\d+)\s*years?", t)
    offset_m2 = re.search(r"(\d+)\s*years?\s*ago", t)
    offset_m3 = re.search(r"(\d+)\s*years?\s*(?:from now|later|time)", t)
    if ask_offset:
        years_offset = 0  # placeholder — solver will compute it
    elif offset_m:
        years_offset = float(offset_m.group(1))
    elif offset_m3:
        years_offset = float(offset_m3.group(1))
    elif offset_m2:
        years_offset = -float(offset_m2.group(1))
    else:
        years_offset = 0

    # Condition type and value
    condition_type = "sum"
    condition_value = 0
    nums = _all_numbers(text)

    # Detect multiplier words first
    twice_m = re.search(r"twice|double|two\s+times|2\s+times", t)
    thrice_m = re.search(r"thrice|triple|three\s+times|3\s+times", t)
    half_m = re.search(r"half", t)
    n_times_m = re.search(r"(\d+(?:\.\d+)?)\s*times", t)

    if twice_m:
        condition_type = "multiple"
        condition_value = 2
    elif thrice_m:
        condition_type = "multiple"
        condition_value = 3
    elif half_m:
        condition_type = "multiple"
        condition_value = 0.5
    elif n_times_m:
        condition_type = "multiple"
        condition_value = float(n_times_m.group(1))
    elif re.search(r"sum|combined|total|together", t):
        condition_type = "sum"
    elif re.search(r"ratio", t):
        condition_type = "ratio"
    elif re.search(r"difference|more than|older than", t):
        condition_type = "difference"

    # For sum/difference, try to extract the condition value if not set
    if condition_type in ("sum", "difference", "ratio") and condition_value == 0:
        known_nums = set(ages_now[k] for k in ages_now if ages_now[k] is not None)
        cond_nums = [n for n in nums if n not in known_nums and n != abs(years_offset)]
        if cond_nums:
            condition_value = cond_nums[0]
        elif nums:
            condition_value = nums[-1]

    # Determine find mode:
    find_mode = "age"  # default: find an unknown age
    if ask_offset and all(v is not None for v in ages_now.values()):
        find_mode = "years_offset"

    return {
        "category": "age",
        "confidence": 0.70,
        "slots": {
            "category": "age",
            "entities": entities,
            "ages_now": ages_now,
            "years_offset": years_offset,
            "condition_type": condition_type,
            "condition_value": condition_value,
            "find": find_mode,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 13. PERCENTAGE CHANGE
# ═══════════════════════════════════════════════════════════════════
def try_percentage_change(text: str) -> Optional[dict]:
    t = text.lower()
    if not re.search(r"percent|%", t):
        return None

    # Percentage value
    pm = re.search(r"(\d+(?:\.\d+)?)\s*%|(\d+(?:\.\d+)?)\s*percent", t)
    if not pm:
        return None
    pct = float(pm.group(1) or pm.group(2))

    # Direction
    direction = "increase"
    if re.search(r"decrease|reduce|less|discount|off|down", t):
        direction = "decrease"

    nums = _all_numbers(text)
    other_nums = [n for n in nums if n != pct]

    original = None
    final_value = None

    if re.search(r"original|was|start|initial|before", t) and other_nums:
        original = other_nums[0]
    elif other_nums:
        original = other_nums[0]

    if re.search(r"(?:find|what).{0,10}(?:final|new|after|result)", t):
        find = "final"
    elif re.search(r"(?:find|what).{0,10}(?:original|before|start|initial)", t):
        find = "original"
        final_value = other_nums[0] if other_nums else None
        original = None
    else:
        find = "final"

    return {
        "category": "percentage_change",
        "confidence": 0.80,
        "slots": {
            "category": "percentage_change",
            "original": original,
            "percentage": pct,
            "direction": direction,
            "final_value": final_value,
            "find": find,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 14. AREA / PERIMETER
# ═══════════════════════════════════════════════════════════════════
def try_area_perimeter(text: str) -> Optional[dict]:
    t = text.lower()
    if not re.search(r"area|perimeter|rectangle|square|triangle|length|width|side|base|height", t):
        return None

    # Shape
    shape = "rectangle"
    if re.search(r"\bsquare\b", t):
        shape = "square"
    elif re.search(r"\btriangle\b", t):
        shape = "triangle"

    length = None
    width = None
    side = None
    base = None
    height = None

    lm = re.search(r"length\s*(?:=|is|of)?\s*(\d+(?:\.\d+)?)", t)
    if lm:
        length = float(lm.group(1))

    wm = re.search(r"width\s*(?:=|is|of)?\s*(\d+(?:\.\d+)?)", t)
    if wm:
        width = float(wm.group(1))

    sm = re.search(r"side\s*(?:=|is|of)?\s*(\d+(?:\.\d+)?)", t)
    if sm:
        side = float(sm.group(1))

    bm = re.search(r"base\s*(?:=|is|of)?\s*(\d+(?:\.\d+)?)", t)
    if bm:
        base = float(bm.group(1))

    hm = re.search(r"height\s*(?:=|is|of)?\s*(\d+(?:\.\d+)?)", t)
    if hm:
        height = float(hm.group(1))

    # If shape is square and no 'side' but has a number
    if shape == "square" and side is None:
        nums = _all_numbers(text)
        if nums:
            side = nums[0]

    # If rectangle and missing length/width, try to pull two numbers
    if shape == "rectangle" and (length is None or width is None):
        nums = _all_numbers(text)
        used = set()
        if length is not None:
            used.add(length)
        if width is not None:
            used.add(width)
        remaining = [n for n in nums if n not in used]
        if length is None and remaining:
            length = remaining.pop(0)
        if width is None and remaining:
            width = remaining.pop(0)

    # Find
    find = "area"
    if re.search(r"perimeter", t):
        find = "perimeter"
    elif re.search(r"(?:find|what).{0,10}side", t):
        find = "side"

    return {
        "category": "area_perimeter",
        "confidence": 0.80,
        "slots": {
            "category": "area_perimeter",
            "shape": shape,
            "length": length,
            "width": width,
            "side": side,
            "base": base,
            "height": height,
            "find": find,
            "known_value": None,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# 15. TWO-SET OVERLAP (VENN)
# ═══════════════════════════════════════════════════════════════════
def try_two_set_overlap(text: str) -> Optional[dict]:
    t = text.lower()
    # Require stronger keywords for Venn diagram problems (not just "both spent")
    if not re.search(r"\b(venn|overlap|only\s+\w+\s+and\s+not|neither\b.{0,30}\bnor\b|play.{0,20}both|join.{0,20}both|total\s+(?:students|people|members|children))\b", t):
        # Also match if "both" appears with set-like context (not "both spent")
        if not (re.search(r"\bboth\b", t) and re.search(r"\b(?:soccer|tennis|football|swim|club|team|subject|class|game)\b", t)):
            return None

    # "Soccer = 25, Tennis = 18, total students = 35. Find students in both."
    # Extract set labels and values
    pairs = _find_names_values(text)

    set_a_label = "A"
    set_b_label = "B"
    set_a = None
    set_b = None
    both = None
    neither = None
    total = None

    if len(pairs) >= 2:
        set_a_label = pairs[0][0]
        set_a = pairs[0][1]
        set_b_label = pairs[1][0]
        set_b = pairs[1][1]

    # Total — handle "total students = 35" and "total = 35" and "35 students in total"
    tm = re.search(r"total\s+(?:\w+\s+)?(?:=|is|of|:)\s*(\d+(?:\.\d+)?)", t)
    if not tm:
        tm = re.search(r"total\s*(?:=|is|of|:)\s*(\d+(?:\.\d+)?)", t)
    if tm:
        total = float(tm.group(1))
    else:
        tm2 = re.search(r"(\d+)\s*(?:students?|people|members?|children)\s*(?:in\s+(?:all|total)|altogether|total)", t)
        if tm2:
            total = float(tm2.group(1))

    # Both
    bm = re.search(r"both\s*(?:=|is|:)?\s*(\d+(?:\.\d+)?)", t)
    if bm:
        both = float(bm.group(1))

    # Neither
    nm = re.search(r"neither\s*(?:=|is|:)?\s*(\d+(?:\.\d+)?)", t)
    if nm:
        neither = float(nm.group(1))

    # Determine find
    find = "both"
    if re.search(r"(?:find|how many).{0,15}neither", t):
        find = "neither"
    elif re.search(r"(?:find|how many).{0,15}total", t):
        find = "total"
    elif re.search(r"(?:find|how many).{0,15}only", t):
        find = "only_a"
    elif both is not None:
        find = "neither" if neither is None else "total"

    return {
        "category": "two_set_overlap",
        "confidence": 0.80,
        "slots": {
            "category": "two_set_overlap",
            "set_a_label": set_a_label,
            "set_b_label": set_b_label,
            "set_a": set_a,
            "set_b": set_b,
            "both": both,
            "neither": neither,
            "total": total,
            "find": find,
        }
    }


# ═══════════════════════════════════════════════════════════════════
# MASTER DISPATCHER
# ═══════════════════════════════════════════════════════════════════
# Order matters: more specific patterns first to avoid false positives
_EXTRACTORS = [
    try_before_after,       # needs ratio + spend/transfer keywords
    try_fractions_whole,    # needs fraction notation
    try_equal_share,        # needs "each" + "left over / short"
    try_coins_notes,        # needs "coin/note"
    try_speed_distance_time,# needs speed/distance/time keywords
    try_work_rate,          # needs "work/finish/together"
    try_percentage_change,  # needs "percent" or "%"
    try_area_perimeter,     # needs shape/geometric keywords
    try_two_set_overlap,    # needs "both/neither/only"
    try_age,                # needs "age/years old"
    try_grouping,           # needs "group/divide"
    try_ratio,              # needs "ratio" or ":"
    try_multiple,           # needs "times as many"
    try_difference,         # needs "more/less than"
    try_price_quantity,     # very broad — keep last
]


def classify_and_extract(text: str) -> Optional[dict]:
    """
    Try all heuristic extractors and return the best match.
    Returns dict with keys: category, confidence, slots — or None.
    """
    best = None
    for extractor in _EXTRACTORS:
        try:
            result = extractor(text)
        except Exception:
            continue
        if result is not None:
            if best is None or result["confidence"] > best["confidence"]:
                best = result
            # If confidence >= 0.80 from an early (specific) extractor, use it immediately
            if result["confidence"] >= 0.80:
                return result
    return best
