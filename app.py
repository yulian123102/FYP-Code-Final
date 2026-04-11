# app.py
import os, re
from solvers import SOLVER_DISPATCH
from heuristics import classify_and_extract as heuristic_classify_all
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, RootModel, ValidationError

# ----------------- OpenAI (optional for classification/extraction) -----------------
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
try:
    from openai import OpenAI
    oai = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None
except Exception: 
    oai = None

# ----------------- FastAPI + CORS -----------------
app = FastAPI(title="Word-Problem Modeler API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Categories (15, per brief) -----------------
CATEGORIES = [
    "fractions_whole",
    "difference_more_less",
    "multiple_times_as_many",
    "ratio",
    "before_after",                 # includes Transfer / Spend–Earn
    "equal_share_excess_shortage",
    "grouping_remainder",
    "price_quantity",
    "coins_notes",
    "speed_distance_time",
    "work_rate",
    "age",
    "percentage_change",
    "area_perimeter",
    "two_set_overlap"
]

# ----------------- Pydantic Schemas -----------------
class BeforeAfterAction(BaseModel):
    """two supported actions for MVP"""
    type: Literal["spend_equal", "transfer"]
    actor_from: Optional[str] = None  # for transfer only (who gives)
    actor_to: Optional[str] = None    # for transfer only (who receives)
    amount: Optional[str] = None      # "unknown" or a number as string (we solve if unknown)

class RatioRelation(BaseModel):
    type: Literal["ratio"] = "ratio"
    ratio: Dict[str, float]           # e.g. {"Esther": 5, "Fran": 2}

class BeforeAfterSlots(BaseModel):
    category: Literal["before_after"]
    entities: List[str]               # e.g. ["Esther","Fran"]
    before: Dict[str, float]          # e.g. {"Esther":157, "Fran":100}
    after_relation: RatioRelation
    actions: List[BeforeAfterAction]  # one action in MVP

class ClassifyExtractRequest(BaseModel):
    question_text: Optional[str] = None
    ocr_image_b64: Optional[str] = None  # reserved for future OCR
    # For now we only use question_text in MVP

class ClassifyExtractResponse(BaseModel):
    category: str
    confidence: float = Field(ge=0, le=1)
    slots: dict

class SolveRequest(BaseModel):
    category: str
    slots: dict

class SolveResponse(BaseModel):
    answer: dict
    steps_markdown: str
    diagram_spec: dict

# ----------------- Simple helpers -----------------
_num = r"([-+]?\d+(?:\.\d+)?)"
def to_float(s: str) -> Optional[float]:
    try:
        return float(s)
    except Exception:
        return None

def _clean_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_ ]+", "", s).strip()

# ----------------- Heuristic extractor (fallback when no OpenAI) -----------------
def heuristic_extract_before_after(text: str) -> Optional[BeforeAfterSlots]:
    """
    Minimal extractor for sentences like:
      "Esther had 157 and Fran had 100. They both bought the same blouse.
       After spending the same amount, the ratio of Esther to Fran is 5 : 2."
    Supports:
      - spend_equal
      - transfer (X gives to Y)
    """
    t = text.replace("\n", " ")
    # Find names & initial amounts like "Esther ... 157", "Fran ... 100"
    # We'll capture first two (MVP assumes 2 entities).
    pairs = re.findall(r"([A-Z][a-zA-Z]+)[^0-9\-+]*" + _num, t)
    # This overmatches; filter to first two unique names+numbers
    entities = []
    before: Dict[str, float] = {}
    for name, num in pairs:
        nm = _clean_name(name)
        if nm not in before:
            v = to_float(num)
            if v is not None:
                before[nm] = v
                entities.append(nm)
        if len(before) == 2:
            break
    if len(before) != 2:
        return None

    # Ratio like "ratio ... 5:2" or "5 to 2"
    ratio_match = re.search(r"(\d+)\s*[:to]\s*(\d+)", t)
    if not ratio_match:
        return None
    a = float(ratio_match.group(1))
    b = float(ratio_match.group(2))
    # Map ratio to entity order as found
    ratio = {entities[0]: a, entities[1]: b}

    # Determine action: spend_equal vs transfer
    if re.search(r"\b(spend|spent|buy|bought|same amount|equal amount)\b", t, re.I):
        action = BeforeAfterAction(type="spend_equal", amount="unknown")
    else:
        # transfer: detect "X gave/gives to Y" or "Y receives from X"
        transf = re.search(r"([A-Z][a-zA-Z]+).{0,30}\b(give|gave|gives|transfer|transferred)\b.{0,30}([A-Z][a-zA-Z]+)", t, re.I)
        if transf:
            fr = _clean_name(transf.group(1))
            to = _clean_name(transf.group(3))
            action = BeforeAfterAction(type="transfer", actor_from=fr, actor_to=to, amount="unknown")
        else:
            # If we can't detect, default to spend_equal (common case)
            action = BeforeAfterAction(type="spend_equal", amount="unknown")

    return BeforeAfterSlots(
        category="before_after",
        entities=entities,
        before=before,
        after_relation=RatioRelation(ratio=ratio),
        actions=[action]
    )

# ----------------- OpenAI extractor (if key provided) -----------------
OAI_INSTRUCTIONS = f"""
You are an assistant that classifies primary-school math word problems into exactly one of these categories:
{CATEGORIES}.
Then you must extract a strict JSON with keys: "category", "confidence" (0-1), and "slots".

Rules:
- Output ONLY valid JSON (no extra text).
- Do NOT compute the numeric answer.
- Pick the best category and fill in the matching slots schema below.
- If unsure, pick the best category and lower "confidence".

Slots schemas by category:

1. fractions_whole: {{"entity":str, "fraction_num":int, "fraction_den":int, "known_value":float, "find":"whole"|"part"}}
2. difference_more_less: {{"entities":[str,str], "known_entity":str, "known_value":float, "difference":float, "more_entity":str, "find":str}}
3. multiple_times_as_many: {{"entities":[str,str], "multiplier":float, "who_is_more":str, "known_entity":str, "known_value":float, "find":str}}
4. ratio: {{"entities":[str,...], "ratio":{{name:float,...}}, "constraint_type":"total"|"difference"|"one_known", "constraint_value":float, "constraint_entity":str|null}}
5. before_after: {{"entities":[str,str], "before":{{name:float,...}}, "after_relation":{{"type":"ratio","ratio":{{name:float,...}}}}, "actions":[{{"type":"spend_equal"|"transfer","actor_from":str|null,"actor_to":str|null,"amount":"unknown"}}]}}
6. equal_share_excess_shortage: {{"share_a":float, "share_b":float, "excess":float, "shortage":float}}
7. grouping_remainder: {{"total":float|null, "group_size":float, "remainder":float, "find":"total"|"groups"|"min_total"}}
8. price_quantity: {{"items":[{{"name":str,"unit_price":float|null,"quantity":float|null,"total":float|null}},...], "find":str}}
9. coins_notes: {{"denominations":[float,...], "total_value":float, "total_count":float|null, "known_counts":{{str:float}}|null}}
10. speed_distance_time: {{"speed":float|null, "distance":float|null, "time":float|null, "find":"speed"|"distance"|"time"}}
11. work_rate: {{"workers":[str,...], "individual_times":{{name:float,...}}, "find":"combined_time"|"individual_time", "combined_time":float|null, "find_worker":str|null}}
12. age: {{"entities":[str,...], "ages_now":{{name:float|null,...}}, "years_offset":float, "condition_type":"sum"|"multiple"|"ratio"|"difference", "condition_value":float}}
13. percentage_change: {{"original":float|null, "percentage":float, "direction":"increase"|"decrease", "final_value":float|null, "find":"final"|"original"|"change"}}
14. area_perimeter: {{"shape":"rectangle"|"square"|"triangle"|"composite", "length":float|null, "width":float|null, "side":float|null, "base":float|null, "height":float|null, "find":"area"|"perimeter"|"side", "known_value":float|null}}
15. two_set_overlap: {{"set_a_label":str, "set_b_label":str, "set_a":float|null, "set_b":float|null, "both":float|null, "neither":float|null, "total":float|null, "find":"both"|"neither"|"total"|"only_a"|"only_b"}}
"""

def openai_classify_extract(question_text: str) -> Optional[ClassifyExtractResponse]:
    if not oai:
        return None
    try:
        msg = [
            {"role": "system", "content": "Output only valid JSON. No prose."},
            {"role": "user", "content": OAI_INSTRUCTIONS},
            {"role": "user", "content": f"Question:\n{question_text}\nReturn JSON now."}
        ]
        res = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=msg,
            temperature=0.2,
        )
        raw = res.choices[0].message.content
        data = ClassifyExtractResponse.model_validate_json(raw)  # must match our pydantic
        return data
    except Exception:
        # as a fallback we try to parse generic JSON then coerce
        try:
            import json
            obj = json.loads(raw)  # type: ignore
            # Coerce minimal keys
            cat = obj.get("category") or "before_after"
            conf = float(obj.get("confidence", 0.6))
            slots = obj.get("slots") or obj
            return ClassifyExtractResponse(category=cat, confidence=conf, slots=slots)
        except Exception:
            return None

# ----------------- Deterministic solvers -----------------
@dataclass
class BAResult:
    answer: Dict[str, float]
    steps: List[str]
    unit_value: Optional[float] = None
    transfer_or_spend_amount: Optional[float] = None

def solve_before_after(slots: BeforeAfterSlots) -> BAResult:
    names = slots.entities
    if len(names) != 2:
        raise ValueError("MVP supports exactly two entities.")
    A, B = names[0], names[1]
    EA = float(slots.before[A]); FB = float(slots.before[B])
    ra = float(slots.after_relation.ratio[A]); rb = float(slots.after_relation.ratio[B])
    action = slots.actions[0]

    steps = []
    answer: Dict[str, float] = {}
    x = None  # unknown spend/transfer

    if action.type == "spend_equal":
        # After spending same x: (EA - x) / (FB - x) = ra / rb
        # => rb(EA - x) = ra(FB - x) => (ra - rb) x = ra*FB - rb*EA
        num = ra*FB - rb*EA
        den = (ra - rb)
        if den == 0:
            raise ValueError("Invalid ratio for spend_equal: ra == rb.")
        x = num / den
        steps.append(f"Let x be the equal amount spent. Using ratio: (E - x)/(F - x) = {ra}:{rb}.")
        steps.append(f"{rb}(E - x) = {ra}(F - x)  ⇒  ({ra} - {rb})x = {ra}×{FB} - {rb}×{EA}.")
        steps.append(f"x = ({ra}×{FB} - {rb}×{EA}) / ({ra} - {rb}) = {x:.2f}.")
        afterA = EA - x
        afterB = FB - x
        unit = afterA/ra  # equals afterB/rb
        steps.append(f"After spending, amounts are E={afterA:.2f}, F={afterB:.2f}. One unit = {unit:.2f}.")
        answer = {"equal_spend": round(x, 2)}
        return BAResult(answer=answer, steps=steps, unit_value=unit, transfer_or_spend_amount=x)

    elif action.type == "transfer":
        # Transfer t from actor_from to actor_to
        frm = action.actor_from or A
        to  = action.actor_to or B
        # Assume frm is A and to is B by default mapping:
        if frm == A and to == B:
            # (EA - t) / (FB + t) = ra / rb  =>  rb(EA - t) = ra(FB + t)
            # => rb*EA - rb*t = ra*FB + ra*t => (ra + rb)t = rb*EA - ra*FB
            num = rb*EA - ra*FB
            den = (ra + rb)
            if den == 0:
                raise ValueError("Invalid ratio for transfer: ra + rb = 0.")
            t = num / den
            x = t
            steps.append(f"Let t be amount transferred from {A} to {B}. (E - t)/(F + t) = {ra}:{rb}.")
            steps.append(f"{rb}(E - t) = {ra}(F + t)  ⇒  ({ra}+{rb})t = {rb}×{EA} - {ra}×{FB}.")
            steps.append(f"t = ({rb}×{EA} - {ra}×{FB}) / ({ra}+{rb}) = {t:.2f}.")
            afterA = EA - t
            afterB = FB + t
        else:
            # Opposite direction (B -> A): (EA + t)/(FB - t) = ra/rb
            num = ra*FB - rb*EA
            den = (ra + rb)
            if den == 0:
                raise ValueError("Invalid ratio for transfer (B->A): ra + rb = 0.")
            t = num / den
            x = t
            steps.append(f"Let t be amount transferred from {B} to {A}. (E + t)/(F - t) = {ra}:{rb}.")
            steps.append(f"{rb}(E + t) = {ra}(F - t)  ⇒  ({ra}+{rb})t = {ra}×{FB} - {rb}×{EA}.")
            steps.append(f"t = ({ra}×{FB} - {rb}×{EA}) / ({ra}+{rb}) = {t:.2f}.")
            afterA = EA + t
            afterB = FB - t

        unit = afterA/ra
        steps.append(f"After transfer, amounts are E={afterA:.2f}, F={afterB:.2f}. One unit = {unit:.2f}.")
        answer = {"transfer_amount": round(x, 2)}
        return BAResult(answer=answer, steps=steps, unit_value=unit, transfer_or_spend_amount=x)

    else:
        raise ValueError(f"Unsupported action: {action.type}")

# ----------------- Diagram spec builder (for Flutter) -----------------
def diagram_spec_before_after(slots: BeforeAfterSlots, res: BAResult) -> dict:
    A, B = slots.entities[0], slots.entities[1]
    ra = slots.after_relation.ratio[A]
    rb = slots.after_relation.ratio[B]
    # Use computed unit if available
    unit = res.unit_value if res.unit_value is not None else 1.0
    spec = {
        "type": "before_after",
        "bars": {
            "before": [
                {"label": A, "value": slots.before[A]},
                {"label": B, "value": slots.before[B]},
            ],
            "after": [
                {"label": A, "units": ra, "unitValue": unit},
                {"label": B, "units": rb, "unitValue": unit},
            ],
        },
        "action": slots.actions[0].type,
    }
    if slots.actions[0].type == "spend_equal":
        spec["equal_spend"] = True
        spec["amount"] = round(res.transfer_or_spend_amount or 0.0, 2)
    else:
        spec["transfer"] = {
            "amount": round(res.transfer_or_spend_amount or 0.0, 2),
            "from": slots.actions[0].actor_from,
            "to": slots.actions[0].actor_to,
        }
    return spec

# ----------------- Routes -----------------
@app.get("/health")
def health():
    return {"ok": True}

@app.post("/classify_extract", response_model=ClassifyExtractResponse)
def classify_extract(req: ClassifyExtractRequest):
    if not req.question_text:
        return ClassifyExtractResponse(category="before_after", confidence=0.0, slots={})

    text = req.question_text.strip()

    # 1) Try OpenAI path (if key present)
    if oai:
        resp = openai_classify_extract(text)
        if resp:
            return resp

    # 2) Heuristic fallback — tries all 15 categories
    heuristic_result = heuristic_classify_all(text)
    if heuristic_result:
        cat = heuristic_result["category"]
        conf = heuristic_result["confidence"]
        raw_slots = heuristic_result["slots"]

        # For before_after, validate into the typed model (legacy path)
        if cat == "before_after":
            try:
                ba_slots = BeforeAfterSlots.model_validate(raw_slots)
                return ClassifyExtractResponse(
                    category=cat, confidence=conf,
                    slots=ba_slots.model_dump()
                )
            except Exception:
                pass  # fall through
        else:
            return ClassifyExtractResponse(
                category=cat, confidence=conf, slots=raw_slots
            )

    # If we can't extract, return low confidence
    return ClassifyExtractResponse(category="before_after", confidence=0.3, slots={})

@app.post("/solve", response_model=SolveResponse)
def solve(req: SolveRequest):
    cat = req.category

    # ── Dispatch to new solvers module (all categories except before_after) ──
    if cat in SOLVER_DISPATCH:
        SchemaClass, solver_fn = SOLVER_DISPATCH[cat]
        try:
            slots_obj = SchemaClass.model_validate(req.slots)
        except ValidationError as e:
            return SolveResponse(
                answer={"error": "invalid slots", "details": e.errors()},
                steps_markdown="Slots validation failed.",
                diagram_spec={}
            )
        try:
            res = solver_fn(slots_obj)
        except Exception as e:
            return SolveResponse(
                answer={"error": str(e)},
                steps_markdown="Unable to solve with provided slots.",
                diagram_spec={}
            )
        steps_md = "### Solution Steps\n" + "\n".join(
            f"{i+1}. {s}" for i, s in enumerate(res.steps)
        )
        return SolveResponse(
            answer=res.answer,
            steps_markdown=steps_md,
            diagram_spec=res.diagram
        )

    if cat != "before_after":
        return SolveResponse(
            answer={"note": "unknown category"},
            steps_markdown="Unknown category.",
            diagram_spec={"type": "unknown", "category": cat}
        )

    # Validate slots to schema
    try:
        slots = BeforeAfterSlots.model_validate(req.slots)
    except ValidationError as e:
        return SolveResponse(
            answer={"error": "invalid slots", "details": e.errors()},
            steps_markdown="Slots validation failed.",
            diagram_spec={}
        )

    # Solve deterministically
    try:
        res = solve_before_after(slots)
    except Exception as e:
        return SolveResponse(
            answer={"error": str(e)},
            steps_markdown="Unable to solve with provided slots.",
            diagram_spec={}
        )

    # Build steps markdown
    steps_md = "### Solution Steps\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(res.steps))
    diag = diagram_spec_before_after(slots, res)

    return SolveResponse(
        answer=res.answer,
        steps_markdown=steps_md,
        diagram_spec=diag
    )

# ----------------- Run directly -----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
