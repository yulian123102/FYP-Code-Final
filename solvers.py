# solvers.py — Deterministic solvers + diagram specs for all 15 categories
import math
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, field
from pydantic import BaseModel

# ─── Generic result ───────────────────────────────────────────────
@dataclass
class SolverResult:
    answer: Dict[str, object]
    steps: List[str]
    diagram: dict = field(default_factory=dict)

# ═══════════════════════════════════════════════════════════════════
#  1. FRACTIONS OF A WHOLE
# ═══════════════════════════════════════════════════════════════════
class FractionsWholeSlots(BaseModel):
    category: Literal["fractions_whole"] = "fractions_whole"
    entity: str                           # e.g. "marbles"
    fraction_num: int                     # numerator  (e.g. 3)
    fraction_den: int                     # denominator (e.g. 4)
    known_value: float                    # value of that fraction
    find: Literal["whole", "part"]        # what to solve for

def solve_fractions_whole(s: FractionsWholeSlots) -> SolverResult:
    frac = s.fraction_num / s.fraction_den
    steps = []
    if s.find == "whole":
        whole = s.known_value / frac
        steps.append(f"{s.fraction_num}/{s.fraction_den} of the {s.entity} = {s.known_value}")
        steps.append(f"1 unit = {s.known_value} ÷ {s.fraction_num} = {s.known_value/s.fraction_num:.4g}")
        steps.append(f"Whole ({s.fraction_den} units) = {s.known_value/s.fraction_num:.4g} × {s.fraction_den} = {whole:.4g}")
        ans = {"whole": round(whole, 4)}
    else:
        part = s.known_value * frac
        steps.append(f"Whole = {s.known_value}")
        steps.append(f"{s.fraction_num}/{s.fraction_den} of {s.known_value} = {part:.4g}")
        ans = {"part": round(part, 4)}
    diag = {
        "type": "fractions_whole",
        "entity": s.entity,
        "fraction_num": s.fraction_num,
        "fraction_den": s.fraction_den,
        "known_value": s.known_value,
        "find": s.find,
        "answer": ans,
    }
    return SolverResult(answer=ans, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
#  2. DIFFERENCE (MORE / LESS)
# ═══════════════════════════════════════════════════════════════════
class DifferenceSlots(BaseModel):
    category: Literal["difference_more_less"] = "difference_more_less"
    entities: List[str]                   # [A, B]
    known_entity: str                     # which entity's value is known
    known_value: float
    difference: float
    more_entity: str                      # who has more
    find: str                             # entity name to find

def solve_difference(s: DifferenceSlots) -> SolverResult:
    steps = []
    if s.find == s.more_entity:
        result = s.known_value + s.difference
        steps.append(f"{s.known_entity} = {s.known_value}")
        steps.append(f"{s.find} has {s.difference} more than {s.known_entity}")
        steps.append(f"{s.find} = {s.known_value} + {s.difference} = {result:.4g}")
    else:
        result = s.known_value - s.difference
        steps.append(f"{s.known_entity} = {s.known_value}")
        steps.append(f"{s.find} has {s.difference} less than {s.known_entity}")
        steps.append(f"{s.find} = {s.known_value} - {s.difference} = {result:.4g}")
    ans = {s.find: round(result, 4)}
    diag = {
        "type": "difference_more_less",
        "entities": s.entities,
        "values": {s.known_entity: s.known_value, s.find: round(result, 4)},
        "difference": s.difference,
        "more_entity": s.more_entity,
    }
    return SolverResult(answer=ans, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
#  3. MULTIPLE (TIMES AS MANY)
# ═══════════════════════════════════════════════════════════════════
class MultipleSlots(BaseModel):
    category: Literal["multiple_times_as_many"] = "multiple_times_as_many"
    entities: List[str]
    multiplier: float                     # e.g. 3 means A = 3 × B
    who_is_more: str                      # entity that is the multiple
    known_entity: str
    known_value: float
    find: str

def solve_multiple(s: MultipleSlots) -> SolverResult:
    steps = []
    if s.find == s.who_is_more:
        result = s.known_value * s.multiplier
        steps.append(f"{s.known_entity} = {s.known_value}")
        steps.append(f"{s.find} = {s.multiplier} × {s.known_value} = {result:.4g}")
    else:
        result = s.known_value / s.multiplier
        steps.append(f"{s.known_entity} = {s.known_value}")
        steps.append(f"{s.find} = {s.known_value} ÷ {s.multiplier} = {result:.4g}")
    ans = {s.find: round(result, 4)}
    diag = {
        "type": "multiple_times_as_many",
        "entities": s.entities,
        "multiplier": s.multiplier,
        "who_is_more": s.who_is_more,
        "values": {s.known_entity: s.known_value, s.find: round(result, 4)},
    }
    return SolverResult(answer=ans, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
#  4. RATIO
# ═══════════════════════════════════════════════════════════════════
class RatioSlots(BaseModel):
    category: Literal["ratio"] = "ratio"
    entities: List[str]
    ratio: Dict[str, float]              # e.g. {"A": 3, "B": 5}
    constraint_type: Literal["total", "difference", "one_known"]
    constraint_value: float              # total sum, difference, or known qty
    constraint_entity: Optional[str] = None  # for one_known

def solve_ratio(s: RatioSlots) -> SolverResult:
    steps = []
    names = s.entities
    parts = [s.ratio[n] for n in names]
    if s.constraint_type == "total":
        total_parts = sum(parts)
        unit = s.constraint_value / total_parts
        steps.append(f"Ratio {':'.join(str(int(p)) for p in parts)} → total parts = {total_parts:.4g}")
        steps.append(f"Total = {s.constraint_value}, so 1 unit = {s.constraint_value} ÷ {total_parts:.4g} = {unit:.4g}")
    elif s.constraint_type == "difference":
        diff_parts = abs(parts[0] - parts[1])
        unit = s.constraint_value / diff_parts if diff_parts else 0
        steps.append(f"Difference in parts = |{parts[0]:.4g} - {parts[1]:.4g}| = {diff_parts:.4g}")
        steps.append(f"Difference = {s.constraint_value}, so 1 unit = {unit:.4g}")
    else:  # one_known
        ent = s.constraint_entity or names[0]
        unit = s.constraint_value / s.ratio[ent]
        steps.append(f"{ent} = {s.constraint_value}, ratio part = {s.ratio[ent]:.4g}")
        steps.append(f"1 unit = {s.constraint_value} ÷ {s.ratio[ent]:.4g} = {unit:.4g}")

    ans = {}
    for n in names:
        val = round(s.ratio[n] * unit, 4)
        ans[n] = val
        steps.append(f"{n} = {s.ratio[n]:.4g} × {unit:.4g} = {val}")
    diag = {
        "type": "ratio",
        "entities": names,
        "ratio": s.ratio,
        "unit_value": round(unit, 4),
        "values": ans,
    }
    return SolverResult(answer=ans, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
#  6. EQUAL SHARE WITH EXCESS / SHORTAGE
# ═══════════════════════════════════════════════════════════════════
class EqualShareSlots(BaseModel):
    category: Literal["equal_share_excess_shortage"] = "equal_share_excess_shortage"
    share_a: float          # items per person in scenario A
    share_b: float          # items per person in scenario B
    excess: float           # leftover in scenario A (positive = excess)
    shortage: float         # shortfall in scenario B (positive = shortage)

def solve_equal_share(s: EqualShareSlots) -> SolverResult:
    steps = []
    diff_per_person = abs(s.share_a - s.share_b)
    total_diff = s.excess + s.shortage
    if diff_per_person == 0:
        return SolverResult(answer={"error": "share amounts are equal"}, steps=["Cannot solve: same share."])
    people = total_diff / diff_per_person
    items = s.share_a * people + s.excess
    steps.append(f"Scenario A: {s.share_a} each → {s.excess} left over")
    steps.append(f"Scenario B: {s.share_b} each → {s.shortage} short")
    steps.append(f"Extra items moved = {s.excess} + {s.shortage} = {total_diff}")
    steps.append(f"Difference per person = |{s.share_a} - {s.share_b}| = {diff_per_person}")
    steps.append(f"Number of people = {total_diff} ÷ {diff_per_person} = {people:.4g}")
    steps.append(f"Total items = {s.share_a} × {people:.4g} + {s.excess} = {items:.4g}")
    ans = {"people": round(people, 4), "items": round(items, 4)}
    diag = {"type": "equal_share_excess_shortage", "people": ans["people"], "items": ans["items"],
            "share_a": s.share_a, "share_b": s.share_b, "excess": s.excess, "shortage": s.shortage}
    return SolverResult(answer=ans, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
#  7. GROUPING WITH REMAINDER
# ═══════════════════════════════════════════════════════════════════
class GroupingSlots(BaseModel):
    category: Literal["grouping_remainder"] = "grouping_remainder"
    total: Optional[float] = None
    group_size: float
    remainder: float
    find: Literal["total", "groups", "min_total"]

def solve_grouping(s: GroupingSlots) -> SolverResult:
    steps = []
    ans = {}
    if s.find == "groups" and s.total is not None:
        groups = (s.total - s.remainder) / s.group_size
        steps.append(f"Total = {s.total}, remainder = {s.remainder}")
        steps.append(f"Items in groups = {s.total} - {s.remainder} = {s.total - s.remainder}")
        steps.append(f"Groups = {s.total - s.remainder} ÷ {s.group_size} = {groups:.4g}")
        ans = {"groups": round(groups, 4)}
    elif s.find == "total":
        # given groups implicitly via remainder
        total = s.group_size * math.floor((s.total or 0) / s.group_size) + s.remainder
        steps.append(f"Total = groups × {s.group_size} + {s.remainder} = {total:.4g}")
        ans = {"total": round(total, 4)}
    else:  # min_total — smallest total with this remainder
        # Typically: find smallest N such that N mod group_size = remainder
        result = s.group_size + s.remainder
        steps.append(f"Minimum total = {s.group_size} + {s.remainder} = {result:.4g} (1 full group + remainder)")
        ans = {"min_total": round(result, 4)}
    diag = {"type": "grouping_remainder", "group_size": s.group_size, "remainder": s.remainder, "answer": ans}
    return SolverResult(answer=ans, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
#  8. PRICE × QUANTITY
# ═══════════════════════════════════════════════════════════════════
class PriceQtyItem(BaseModel):
    name: str
    unit_price: Optional[float] = None
    quantity: Optional[float] = None
    total: Optional[float] = None

class PriceQtySlots(BaseModel):
    category: Literal["price_quantity"] = "price_quantity"
    items: List[PriceQtyItem]
    find: str  # "total_cost" | "unit_price" | "quantity" | item name

def solve_price_qty(s: PriceQtySlots) -> SolverResult:
    steps = []
    results = {}
    grand = 0.0
    for it in s.items:
        if it.unit_price is not None and it.quantity is not None:
            t = it.unit_price * it.quantity
            steps.append(f"{it.name}: ${it.unit_price} × {it.quantity} = ${t:.2f}")
            results[it.name] = round(t, 2)
            grand += t
        elif it.total is not None and it.quantity is not None and it.quantity > 0:
            up = it.total / it.quantity
            steps.append(f"{it.name}: ${it.total} ÷ {it.quantity} = ${up:.2f} each")
            results[it.name + "_unit_price"] = round(up, 2)
        elif it.total is not None and it.unit_price is not None and it.unit_price > 0:
            q = it.total / it.unit_price
            steps.append(f"{it.name}: ${it.total} ÷ ${it.unit_price} = {q:.4g} items")
            results[it.name + "_quantity"] = round(q, 4)
        elif it.total is not None:
            grand += it.total
            results[it.name] = it.total
    results["grand_total"] = round(grand, 2)
    steps.append(f"Grand total = ${grand:.2f}")
    diag = {"type": "price_quantity", "items": [i.model_dump() for i in s.items], "results": results}
    return SolverResult(answer=results, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
#  9. COINS / NOTES
# ═══════════════════════════════════════════════════════════════════
class CoinsNotesSlots(BaseModel):
    category: Literal["coins_notes"] = "coins_notes"
    denominations: List[float]            # e.g. [0.50, 0.20]
    total_value: float
    total_count: Optional[float] = None   # total number of coins/notes
    known_counts: Optional[Dict[str, float]] = None  # if one denomination count is known

def solve_coins_notes(s: CoinsNotesSlots) -> SolverResult:
    steps = []
    ans = {}
    denoms = s.denominations
    if len(denoms) == 2 and s.total_count is not None:
        d1, d2 = denoms[0], denoms[1]
        # d1*x + d2*y = total_value, x + y = total_count
        # x = (total_value - d2*total_count) / (d1 - d2)
        if d1 == d2:
            return SolverResult(answer={"error": "denominations are equal"}, steps=["Cannot solve"])
        x = (s.total_value - d2 * s.total_count) / (d1 - d2)
        y = s.total_count - x
        steps.append(f"Let x = number of ${d1} coins, y = number of ${d2} coins")
        steps.append(f"x + y = {s.total_count}")
        steps.append(f"{d1}x + {d2}y = {s.total_value}")
        steps.append(f"x = ({s.total_value} - {d2}×{s.total_count}) ÷ ({d1} - {d2}) = {x:.4g}")
        steps.append(f"y = {s.total_count} - {x:.4g} = {y:.4g}")
        ans = {f"${d1}": round(x, 4), f"${d2}": round(y, 4)}
    elif s.known_counts:
        remaining = s.total_value
        remaining_count = s.total_count or 0
        for denom_str, cnt in s.known_counts.items():
            d = float(denom_str)
            val = d * cnt
            remaining -= val
            remaining_count -= cnt
            steps.append(f"${d} × {cnt} = ${val:.2f}")
        steps.append(f"Remaining value = ${remaining:.2f}")
        ans = {"remaining_value": round(remaining, 2)}
        if remaining_count > 0 and len(denoms) > len(s.known_counts):
            unknown_d = [d for d in denoms if str(d) not in s.known_counts]
            if len(unknown_d) == 1:
                cnt = remaining / unknown_d[0]
                steps.append(f"${unknown_d[0]} coins = ${remaining:.2f} ÷ ${unknown_d[0]} = {cnt:.4g}")
                ans[f"${unknown_d[0]}"] = round(cnt, 4)
    else:
        steps.append("Insufficient constraints to solve uniquely.")
        ans = {"note": "need total_count or known_counts"}
    diag = {"type": "coins_notes", "denominations": denoms, "answer": ans}
    return SolverResult(answer=ans, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
# 10. SPEED–DISTANCE–TIME
# ═══════════════════════════════════════════════════════════════════
class SDTSlots(BaseModel):
    category: Literal["speed_distance_time"] = "speed_distance_time"
    speed: Optional[float] = None
    distance: Optional[float] = None
    time: Optional[float] = None          # in hours
    find: Literal["speed", "distance", "time"]
    speed_unit: str = "km/h"
    distance_unit: str = "km"
    time_unit: str = "h"

def solve_sdt(s: SDTSlots) -> SolverResult:
    steps = []
    if s.find == "distance":
        d = (s.speed or 0) * (s.time or 0)
        steps.append(f"Distance = Speed × Time = {s.speed} × {s.time} = {d:.4g} {s.distance_unit}")
        ans = {"distance": round(d, 4)}
    elif s.find == "speed":
        sp = (s.distance or 0) / (s.time or 1)
        steps.append(f"Speed = Distance ÷ Time = {s.distance} ÷ {s.time} = {sp:.4g} {s.speed_unit}")
        ans = {"speed": round(sp, 4)}
    else:
        t = (s.distance or 0) / (s.speed or 1)
        steps.append(f"Time = Distance ÷ Speed = {s.distance} ÷ {s.speed} = {t:.4g} {s.time_unit}")
        ans = {"time": round(t, 4)}
    diag = {"type": "speed_distance_time", "speed": s.speed, "distance": s.distance,
            "time": s.time, "find": s.find, "answer": ans}
    return SolverResult(answer=ans, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
# 11. WORK / RATE
# ═══════════════════════════════════════════════════════════════════
class WorkRateSlots(BaseModel):
    category: Literal["work_rate"] = "work_rate"
    workers: List[str]
    individual_times: Dict[str, float]    # hours each worker takes alone
    find: Literal["combined_time", "individual_time"]
    combined_time: Optional[float] = None
    find_worker: Optional[str] = None

def solve_work_rate(s: WorkRateSlots) -> SolverResult:
    steps = []
    if s.find == "combined_time":
        rate_sum = 0.0
        for w in s.workers:
            t = s.individual_times[w]
            r = 1.0 / t
            rate_sum += r
            steps.append(f"{w}'s rate = 1/{t:.4g} = {r:.6g} job/hour")
        combined = 1.0 / rate_sum
        steps.append(f"Combined rate = {rate_sum:.6g}")
        steps.append(f"Combined time = 1 ÷ {rate_sum:.6g} = {combined:.4g} hours")
        ans = {"combined_time": round(combined, 4)}
    else:
        if s.combined_time and s.find_worker:
            combined_rate = 1.0 / s.combined_time
            other_rate = 0.0
            for w in s.workers:
                if w != s.find_worker and w in s.individual_times:
                    other_rate += 1.0 / s.individual_times[w]
            target_rate = combined_rate - other_rate
            target_time = 1.0 / target_rate if target_rate > 0 else float('inf')
            steps.append(f"Combined rate = 1/{s.combined_time} = {combined_rate:.6g}")
            steps.append(f"Other workers' rate = {other_rate:.6g}")
            steps.append(f"{s.find_worker}'s rate = {target_rate:.6g}")
            steps.append(f"{s.find_worker}'s time = {target_time:.4g} hours")
            ans = {s.find_worker + "_time": round(target_time, 4)}
        else:
            ans = {"error": "need combined_time and find_worker"}
            steps.append("Insufficient data")
    diag = {"type": "work_rate", "workers": s.workers, "times": s.individual_times, "answer": ans}
    return SolverResult(answer=ans, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
# 12. AGE
# ═══════════════════════════════════════════════════════════════════
class AgeSlots(BaseModel):
    category: Literal["age"] = "age"
    entities: List[str]
    ages_now: Dict[str, Optional[float]]  # None = unknown
    years_offset: float                    # positive = future, negative = past
    condition_type: Literal["sum", "multiple", "ratio", "difference"]
    condition_value: float
    find: Optional[str] = "age"            # "age" or "years_offset"

def solve_age(s: AgeSlots) -> SolverResult:
    steps = []
    names = s.entities
    # Try to find the unknown
    known = {k: v for k, v in s.ages_now.items() if v is not None}
    unknown = [k for k, v in s.ages_now.items() if v is None]
    direction = "years ago" if s.years_offset < 0 else "years from now"
    offset = abs(s.years_offset)

    # ── Mode 1: find years_offset (both ages known) ──
    if s.find == "years_offset" and len(known) == 2:
        ks = list(known.keys())
        a_name, b_name = ks[0], ks[1]
        a_now, b_now = known[a_name], known[b_name]
        cond = s.condition_value

        if s.condition_type == "multiple":
            # a_now + y = cond * (b_now + y)  →  y = (a_now - cond*b_now) / (cond - 1)
            if cond == 1:
                ans = {"error": "Multiple of 1 means always equal (undefined offset)"}
                steps.append("Multiple of 1 → always equal.")
            else:
                y = (a_now - cond * b_now) / (cond - 1)
                steps.append(f"Let y = number of years from now.")
                steps.append(f"In y years: {a_name} = {a_now} + y, {b_name} = {b_now} + y")
                steps.append(f"Condition: {a_name} = {cond} × {b_name}")
                steps.append(f"  {a_now} + y = {cond} × ({b_now} + y)")
                steps.append(f"  {a_now} + y = {cond * b_now} + {cond}y")
                steps.append(f"  y − {cond}y = {cond * b_now} − {a_now}")
                steps.append(f"  ({1 - cond})y = {cond * b_now - a_now}")
                steps.append(f"  y = {y:.4g}")
                if y < 0:
                    steps.append(f"(Negative means {abs(y):.4g} years ago)")
                ans = {"years": round(y, 4)}
        elif s.condition_type == "sum":
            # (a + y) + (b + y) = cond  →  y = (cond - a - b) / 2
            y = (cond - a_now - b_now) / 2
            steps.append(f"(a + y) + (b + y) = {cond}")
            steps.append(f"y = ({cond} − {a_now} − {b_now}) / 2 = {y:.4g}")
            ans = {"years": round(y, 4)}
        elif s.condition_type == "difference":
            # |a + y - b - y| = cond  →  always |a - b|; can't solve for y
            ans = {"note": "Age difference is constant; cannot solve for years offset."}
            steps.append("Difference doesn't change over time.")
        else:
            ans = {"error": f"Unsupported condition_type='{s.condition_type}' for years_offset find"}
            steps.append("Unsupported condition type for this problem.")

        diag = {"type": "age", "entities": names, "ages_now": s.ages_now,
                "offset": ans.get("years", 0), "answer": ans}
        return SolverResult(answer=ans, steps=steps, diagram=diag)

    # ── Mode 2: find unknown age (1 unknown + 1 known) ──
    if len(unknown) == 1 and len(known) == 1:
        u = unknown[0]
        k_name = list(known.keys())[0]
        k_val = known[k_name]
        if s.condition_type == "sum":
            # (k_val + offset) + (x + offset) = condition  OR offset negative
            # x + k_val + 2*s.years_offset = condition
            x = s.condition_value - k_val - 2 * s.years_offset
            steps.append(f"In {offset} {direction}: {k_name} = {k_val + s.years_offset:.4g}, {u} = x + ({s.years_offset})")
            steps.append(f"Sum = {s.condition_value} → x = {s.condition_value} - {k_val} - 2×({s.years_offset}) = {x:.4g}")
        elif s.condition_type == "multiple":
            # (k_val + offset) = condition * (x + offset)  OR vice versa
            k_future = k_val + s.years_offset
            x = k_future / s.condition_value - s.years_offset
            steps.append(f"In {offset} {direction}: {k_name} = {k_future:.4g}")
            steps.append(f"{k_name} = {s.condition_value} × {u} → {u} then = {k_future/s.condition_value:.4g}")
            steps.append(f"{u} now = {x:.4g}")
        elif s.condition_type == "ratio":
            # same as multiple for 2 entities
            k_future = k_val + s.years_offset
            u_future = k_future / s.condition_value
            x = u_future - s.years_offset
            steps.append(f"{k_name} then = {k_future:.4g}")
            steps.append(f"Ratio = {s.condition_value}:1 → {u} then = {u_future:.4g}")
            steps.append(f"{u} now = {u_future:.4g} - ({s.years_offset}) = {x:.4g}")
        else:  # difference
            k_future = k_val + s.years_offset
            x = k_future - s.condition_value - s.years_offset
            steps.append(f"Difference in {offset} {direction} = {s.condition_value}")
            steps.append(f"{u} now = {x:.4g}")
        ans = {u: round(x, 4)}
    else:
        ans = {"note": "solver supports 1 unknown + 1 known entity, or find='years_offset' with 2 known"}
        steps.append("Need exactly one unknown and one known age (or two known ages and find='years_offset').")
    diag = {"type": "age", "entities": names, "ages_now": s.ages_now,
            "offset": s.years_offset, "answer": ans}
    return SolverResult(answer=ans, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
# 13. PERCENTAGE CHANGE
# ═══════════════════════════════════════════════════════════════════
class PercentageSlots(BaseModel):
    category: Literal["percentage_change"] = "percentage_change"
    original: Optional[float] = None
    percentage: float                      # e.g. 20 means 20%
    direction: Literal["increase", "decrease"]
    final_value: Optional[float] = None
    find: Literal["final", "original", "change"]

def solve_percentage(s: PercentageSlots) -> SolverResult:
    steps = []
    pct = s.percentage / 100.0
    if s.find == "final" and s.original is not None:
        if s.direction == "increase":
            result = s.original * (1 + pct)
            steps.append(f"Increase: {s.original} × (1 + {s.percentage}%) = {result:.4g}")
        else:
            result = s.original * (1 - pct)
            steps.append(f"Decrease: {s.original} × (1 - {s.percentage}%) = {result:.4g}")
        ans = {"final": round(result, 4)}
    elif s.find == "original" and s.final_value is not None:
        if s.direction == "increase":
            result = s.final_value / (1 + pct)
            steps.append(f"Original = {s.final_value} ÷ (1 + {s.percentage}%) = {result:.4g}")
        else:
            result = s.final_value / (1 - pct)
            steps.append(f"Original = {s.final_value} ÷ (1 - {s.percentage}%) = {result:.4g}")
        ans = {"original": round(result, 4)}
    else:
        change = (s.original or 0) * pct
        steps.append(f"Change = {s.original} × {s.percentage}% = {change:.4g}")
        ans = {"change": round(change, 4)}
    diag = {"type": "percentage_change", "original": s.original, "percentage": s.percentage,
            "direction": s.direction, "answer": ans}
    return SolverResult(answer=ans, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
# 14. AREA / PERIMETER
# ═══════════════════════════════════════════════════════════════════
class AreaPerimeterSlots(BaseModel):
    category: Literal["area_perimeter"] = "area_perimeter"
    shape: Literal["rectangle", "square", "triangle", "composite"]
    length: Optional[float] = None
    width: Optional[float] = None
    side: Optional[float] = None          # for square
    base: Optional[float] = None
    height: Optional[float] = None
    find: Literal["area", "perimeter", "side"]
    known_value: Optional[float] = None   # e.g. area or perimeter given

def solve_area_perimeter(s: AreaPerimeterSlots) -> SolverResult:
    steps = []
    ans = {}
    if s.shape == "rectangle":
        if s.find == "area" and s.length and s.width:
            a = s.length * s.width
            steps.append(f"Area = {s.length} × {s.width} = {a:.4g}")
            ans = {"area": round(a, 4)}
        elif s.find == "perimeter" and s.length and s.width:
            p = 2 * (s.length + s.width)
            steps.append(f"Perimeter = 2 × ({s.length} + {s.width}) = {p:.4g}")
            ans = {"perimeter": round(p, 4)}
        elif s.find == "side" and s.known_value and s.length:
            # known_value = area or perimeter; assume area
            w = s.known_value / s.length
            steps.append(f"Width = {s.known_value} ÷ {s.length} = {w:.4g}")
            ans = {"width": round(w, 4)}
        elif s.find == "side" and s.known_value and s.width:
            l = s.known_value / s.width
            steps.append(f"Length = {s.known_value} ÷ {s.width} = {l:.4g}")
            ans = {"length": round(l, 4)}
    elif s.shape == "square":
        sd = s.side or 0
        if s.find == "area":
            a = sd * sd
            steps.append(f"Area = {sd}² = {a:.4g}")
            ans = {"area": round(a, 4)}
        elif s.find == "perimeter":
            p = 4 * sd
            steps.append(f"Perimeter = 4 × {sd} = {p:.4g}")
            ans = {"perimeter": round(p, 4)}
        elif s.find == "side" and s.known_value:
            sd = math.sqrt(s.known_value)
            steps.append(f"Side = √{s.known_value} = {sd:.4g}")
            ans = {"side": round(sd, 4)}
    elif s.shape == "triangle":
        if s.find == "area" and s.base and s.height:
            a = 0.5 * s.base * s.height
            steps.append(f"Area = ½ × {s.base} × {s.height} = {a:.4g}")
            ans = {"area": round(a, 4)}
    diag = {"type": "area_perimeter", "shape": s.shape,
            "length": s.length, "width": s.width, "side": s.side,
            "base": s.base, "height": s.height, "answer": ans}
    return SolverResult(answer=ans, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
# 15. TWO-SET OVERLAP (VENN)
# ═══════════════════════════════════════════════════════════════════
class TwoSetSlots(BaseModel):
    category: Literal["two_set_overlap"] = "two_set_overlap"
    set_a_label: str
    set_b_label: str
    set_a: Optional[float] = None         # |A|
    set_b: Optional[float] = None         # |B|
    both: Optional[float] = None          # |A ∩ B|
    neither: Optional[float] = None       # outside both
    total: Optional[float] = None
    find: str                             # "both" | "neither" | "total" | "only_a" | "only_b"

def solve_two_set(s: TwoSetSlots) -> SolverResult:
    steps = []
    # Inclusion-exclusion: total = A + B - both + neither
    vals = {"set_a": s.set_a, "set_b": s.set_b, "both": s.both,
            "neither": s.neither, "total": s.total}
    nones = [k for k, v in vals.items() if v is None]

    if s.find == "both" and s.set_a is not None and s.set_b is not None and s.total is not None:
        neither = s.neither or 0
        both = s.set_a + s.set_b - s.total + neither
        steps.append(f"|A| + |B| - both + neither = total")
        steps.append(f"{s.set_a} + {s.set_b} - both + {neither} = {s.total}")
        steps.append(f"both = {s.set_a} + {s.set_b} + {neither} - {s.total} = {both:.4g}")
        ans = {"both": round(both, 4)}
    elif s.find == "neither" and s.set_a is not None and s.set_b is not None and s.both is not None and s.total is not None:
        neither = s.total - s.set_a - s.set_b + s.both
        steps.append(f"neither = total - |A| - |B| + both = {neither:.4g}")
        ans = {"neither": round(neither, 4)}
    elif s.find == "total" and s.set_a is not None and s.set_b is not None and s.both is not None:
        neither = s.neither or 0
        total = s.set_a + s.set_b - s.both + neither
        steps.append(f"total = |A| + |B| - both + neither = {total:.4g}")
        ans = {"total": round(total, 4)}
    elif s.find == "only_a" and s.set_a is not None and s.both is not None:
        only_a = s.set_a - s.both
        steps.append(f"Only A = |A| - both = {s.set_a} - {s.both} = {only_a:.4g}")
        ans = {"only_a": round(only_a, 4)}
    elif s.find == "only_b" and s.set_b is not None and s.both is not None:
        only_b = s.set_b - s.both
        steps.append(f"Only B = |B| - both = {s.set_b} - {s.both} = {only_b:.4g}")
        ans = {"only_b": round(only_b, 4)}
    else:
        ans = {"error": "insufficient data for inclusion-exclusion"}
        steps.append("Need more values to solve.")
    only_a = (s.set_a or 0) - (s.both or 0)
    only_b = (s.set_b or 0) - (s.both or 0)
    diag = {"type": "two_set_overlap",
            "set_a_label": s.set_a_label, "set_b_label": s.set_b_label,
            "only_a": round(only_a, 4), "only_b": round(only_b, 4),
            "both": s.both, "neither": s.neither, "total": s.total, "answer": ans}
    return SolverResult(answer=ans, steps=steps, diagram=diag)

# ═══════════════════════════════════════════════════════════════════
#  DISPATCH TABLE
# ═══════════════════════════════════════════════════════════════════
SOLVER_DISPATCH = {
    "fractions_whole":             (FractionsWholeSlots, solve_fractions_whole),
    "difference_more_less":        (DifferenceSlots,     solve_difference),
    "multiple_times_as_many":      (MultipleSlots,       solve_multiple),
    "ratio":                       (RatioSlots,          solve_ratio),
    # "before_after" handled in app.py (existing code)
    "equal_share_excess_shortage": (EqualShareSlots,     solve_equal_share),
    "grouping_remainder":          (GroupingSlots,        solve_grouping),
    "price_quantity":              (PriceQtySlots,       solve_price_qty),
    "coins_notes":                 (CoinsNotesSlots,     solve_coins_notes),
    "speed_distance_time":         (SDTSlots,            solve_sdt),
    "work_rate":                   (WorkRateSlots,       solve_work_rate),
    "age":                         (AgeSlots,            solve_age),
    "percentage_change":           (PercentageSlots,     solve_percentage),
    "area_perimeter":              (AreaPerimeterSlots,  solve_area_perimeter),
    "two_set_overlap":             (TwoSetSlots,         solve_two_set),
}
