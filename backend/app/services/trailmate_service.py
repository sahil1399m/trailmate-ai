"""
TrailMate AI - Outdoor Adventure Planner Service

Responsibilities:
1. Validate and prepare user inputs.
2. Construct a grounded, JSON-forcing prompt for SmolLM2.
3. Call generate_text() from llm_service.
4. Extract and parse the model's JSON output robustly.
5. Sanitize hallucinated named-place claims, distances, and inappropriate gear.
6. Validate the parsed data against the PlanResponse Pydantic schema.
7. Pin known fields (duration, activity, difficulty) from the request.
8. Surface parse/validation failures as clean RuntimeError -> HTTP 503.

Grounding policy:
- The model MUST NOT invent named parks, trails, sanctuaries, roads, or landmarks.
  Location is strictly a geographic context hint.
- If the user supplies a specific named place in their request, it may be referenced.
- Post-generation sanitizers detect and replace named places, distance units,
  impractical packing items (e.g. tents for urban walks), and wildlife hazards.
- Route ideas and missions are strictly time-based, never mentioning distance units.

No external APIs, no maps, no weather, no database, no Ollama.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from backend.app.schemas.plan import PlanRequest, PlanResponse
from backend.app.services.llm_service import build_chat_prompt, generate_text

# ── Constants ─────────────────────────────────────────────────────────────────

_PLAN_MAX_TOKENS = 600

# ── Activity classification ──────────────────────────────────────────────────

def _classify_activity(activity: str) -> str:
    """Return a canonical activity class: cycling | running | hiking | walking."""
    a = activity.lower().strip()
    if any(k in a for k in ("cycl", "bike", "biking", "bicycle")):
        return "cycling"
    if any(k in a for k in ("run", "jog", "sprint")):
        return "running"
    if any(k in a for k in ("hik", "trek", "backpack", "bushwalk")):
        return "hiking"
    return "walking"


# ── Time-based stage calculation ─────────────────────────────────────────────

def _calculate_stage_minutes(duration: int) -> tuple[int, int, int, int]:
    """
    Split duration into (warmup, main, task, cooldown) such that:
    warmup + main + task + cooldown == duration.
    For short outings (<= 30 min), task is 0 (integrated into main phase).
    """
    if duration <= 30:
        warmup = max(3, min(5, duration // 5))
        cooldown = max(3, min(5, duration // 5))
        main = duration - warmup - cooldown
        task = 0
        return warmup, main, task, cooldown
    elif duration <= 60:
        warmup = max(5, duration // 10)
        cooldown = max(5, duration // 10)
        task = max(10, duration // 4)
        main = duration - warmup - task - cooldown
        return warmup, main, task, cooldown
    elif duration <= 120:
        warmup = 10
        cooldown = 10
        task = 20
        main = duration - warmup - task - cooldown
        return warmup, main, task, cooldown
    else:  # duration > 120 (e.g. 180 min hike)
        warmup = 15
        cooldown = 15
        task = 30  # scenic mid-trail checkpoint / rest / observation
        main = duration - warmup - task - cooldown
        return warmup, main, task, cooldown


# ── Actionable mission builder ────────────────────────────────────────────────

def _build_actionable_mission(req: PlanRequest) -> str:
    """Generate a structured, actionable mission with distinct stages totaling req.time_available min."""
    activity_class = _classify_activity(req.activity)
    w, m, t, c = _calculate_stage_minutes(req.time_available)
    loc = req.location
    intensity = req.intensity

    if activity_class == "walking":
        if t > 0:
            return (
                f"Begin with a {w}-minute gentle warm-up walk to establish a steady breathing rhythm. "
                f"Explore an accessible, shaded pedestrian area in {loc} for {m} minutes at a {intensity} pace. "
                f"Dedicate {t} minutes to an active nature-awareness task, observing local tree canopy variety, "
                f"bird sounds, and quiet green pockets away from traffic. "
                f"Finish with a {c}-minute relaxed cooldown stroll and light stretching."
            )
        return (
            f"Start with a {w}-minute gentle warm-up stroll. "
            f"Walk through an accessible, shaded pedestrian path in {loc} for {m} minutes at a {intensity} pace, "
            f"observing seasonal foliage and ambient natural details. "
            f"Conclude with a {c}-minute easy cooldown stroll."
        )

    elif activity_class == "running":
        if t > 0:
            return (
                f"Start with a {w}-minute easy warm-up jog and mobility drills. "
                f"Execute a {m}-minute main run at {intensity} intensity along a paved pedestrian circuit in {loc}. "
                f"Complete a {t}-minute pacing checkpoint focusing on steady cadence and relaxed shoulder posture. "
                f"Finish with a {c}-minute walking cooldown and lower-body stretching."
            )
        return (
            f"Start with a {w}-minute easy warm-up jog. "
            f"Maintain a {m}-minute main run at {intensity} intensity along a clear, flat pedestrian route in {loc}. "
            f"Conclude with a {c}-minute walking cooldown and recovery stretches."
        )

    elif activity_class == "cycling":
        if t > 0:
            return (
                f"Begin with a {w}-minute pre-ride check and easy spin warm-up on quiet streets in {loc}. "
                f"Embark on a {m}-minute main ride at a {intensity} cadence along a wide, bike-friendly loop. "
                f"Spend {t} minutes on an environmental awareness segment, noticing 5 outdoor ambient sounds while safely riding. "
                f"Wrap up with a {c}-minute gentle spin cooldown and hydration stop."
            )
        return (
            f"Begin with a {w}-minute easy gear check and spin warm-up. "
            f"Ride for {m} minutes at {intensity} effort along a safe, low-traffic route in {loc}. "
            f"Finish with a {c}-minute easy spin cooldown."
        )

    else:  # hiking
        if t > 0:
            return (
                f"Start with a {w}-minute gentle trail warm-up ascent to find your hiking rhythm. "
                f"Trek for {m} minutes at a steady {intensity} pace through natural trail paths in {loc}. "
                f"Take a {t}-minute scenic mid-trail pause for hydration, a trail snack, and observing native plants or rock formations. "
                f"Conclude with a {c}-minute controlled return leg back to your starting point and cooldown stretching."
            )
        return (
            f"Start with a {w}-minute gentle trail warm-up. "
            f"Hike for {m} minutes at {intensity} pace through accessible natural paths in {loc}. "
            f"Finish with a {c}-minute easy return stroll and cooldown stretch."
        )


# ── Time-based route idea builder ─────────────────────────────────────────────

def _build_route_idea(req: PlanRequest) -> str:
    """Generate a practical, time-based route idea without distances or named places."""
    activity_class = _classify_activity(req.activity)
    loc = req.location
    duration = req.time_available
    half = duration // 2

    if activity_class == "walking":
        return _normalize_text(
            f"Choose a shaded pedestrian loop or quiet walking path in an accessible public area around {loc}. "
            f"Head outward for roughly {half} minutes, then loop or retrace your steps early enough to finish "
            f"comfortably within your {duration}-minute window."
        )
    elif activity_class == "running":
        return _normalize_text(
            f"Select a continuous, well-lit pedestrian circuit or flat paved path in {loc}. "
            f"Run an out-and-back or circular pattern, checking your time to turn around at the {half}-minute mark "
            f"to complete your {duration}-minute session smoothly."
        )
    elif activity_class == "cycling":
        return _normalize_text(
            f"Pick a low-traffic loop or designated bike-friendly roadway in {loc} with good visibility. "
            f"Cycle outward for approximately {half} minutes before looping back along connected streets "
            f"to wrap up within your {duration}-minute time frame."
        )
    else:  # hiking
        return _normalize_text(
            f"Select an established, marked natural trail loop or accessible park pathway in {loc}. "
            f"Hike outward for the first {half} minutes of your {duration}-minute window, "
            f"leaving ample time and daylight for a safe, steady return leg."
        )


# ── Tailored packing list builder ─────────────────────────────────────────────

def _build_tailored_gear(req: PlanRequest) -> list[str]:
    """Return 3-5 practical gear items tailored to activity, intensity, duration, and budget."""
    activity_class = _classify_activity(req.activity)
    items: list[str] = []

    if activity_class == "walking":
        items.append("water bottle")
        items.append("comfortable walking shoes")
        items.append("sun protection (hat or sunscreen)")
        if req.time_available >= 60:
            items.append("light snack from home")
        if req.intensity == "high":
            items.append("electrolyte drink")
        elif req.budget > 0:
            items.append("pocket money for a local beverage or transit")

    elif activity_class == "running":
        items.append("supportive running shoes")
        items.append("breathable athletic wear")
        if req.time_available >= 20:
            items.append("handheld water bottle or hydration belt")
        if req.time_available >= 60 or req.intensity == "high":
            items.append("electrolyte drink or energy gel")

    elif activity_class == "cycling":
        items.append("cycling helmet (essential)")
        items.append("water bottle mounted on bike")
        items.append("basic puncture repair kit or mini pump")
        items.append("comfortable riding clothes")
        if req.time_available >= 60:
            items.append("energy snack or fruit")
        if req.intensity == "high":
            items.append("electrolyte replacement drink")

    else:  # hiking
        items.append("sturdy hiking footwear with good grip")
        water_amount = "2 L of drinking water" if req.time_available >= 120 else "1 L of drinking water"
        items.append(water_amount)
        items.append("trail snacks (nuts, fruit, or energy bars)")
        items.append("sun protection (hat and sunscreen)")
        items.append("compact first-aid kit")
        if req.time_available >= 120:
            items.append("lightweight windbreaker or rain layer")
        if req.intensity == "high":
            items.append("electrolyte tablets or drink")
        if req.budget > 0:
            items.append("small budget for trailhead pass or snack")

    return items[:5]


# ── Tailored challenge builder ────────────────────────────────────────────────

def _build_tailored_challenge(req: PlanRequest) -> str:
    """Return a measurable, enjoyable outdoor challenge encouraging phone-free engagement."""
    activity_class = _classify_activity(req.activity)
    dur = req.time_available

    if activity_class == "walking":
        if dur <= 45:
            return (
                "Walk for 10 consecutive minutes without looking at your phone (except for navigation), "
                "and identify 4 distinct natural sounds such as birdsong, wind through leaves, or water."
            )
        return (
            "Spot and observe 5 different plant or tree species along your route. Notice their leaf textures, "
            "bark patterns, and colors without checking your phone during the walk."
        )
    elif activity_class == "running":
        return (
            "Focus on your breathing rhythm and pick 4 distinct natural visual landmarks ahead "
            "(such as distinctive trees, hilltops, or park features) to pace your stride, keeping screens away."
        )
    elif activity_class == "cycling":
        return (
            "During easy spin segments, tune into your surroundings and distinguish 5 different ambient sounds "
            "(wind rustle, bird calls, running water) while keeping your eyes safely focused on the road."
        )
    else:  # hiking
        return (
            "Identify 5 distinct natural textures (rough bark, moss, smooth stone, soil, pine needles) "
            "and spot 3 native bird or plant varieties along the trail."
        )


# ── Tailored safety tips builder ──────────────────────────────────────────────

def _build_tailored_safety_tips(req: PlanRequest) -> list[str]:
    """Return 2-4 concise, practical safety tips relevant to the activity."""
    activity_class = _classify_activity(req.activity)

    if activity_class == "walking":
        return [
            "Wear comfortable, supportive walking shoes to avoid blisters.",
            "Stay on designated pedestrian footpaths and remain alert to vehicle traffic when crossing streets.",
            "Carry a water bottle and take regular sips, especially in warm or sunny conditions.",
            "Stick to well-lit, accessible public areas and adjust your pace if you feel fatigued.",
        ]
    elif activity_class == "running":
        return [
            "Warm up with light dynamic movement before running, and wear properly cushioned running shoes.",
            "Stay alert to uneven pavement, cyclists, and traffic; face oncoming traffic if running on shared roads.",
            "Sip water periodically to maintain hydration, especially during higher-intensity intervals.",
            "Cool down thoroughly with light walking and stretching after your run.",
        ]
    elif activity_class == "cycling":
        return [
            "Always wear a properly fitted bicycle helmet and obey all local traffic signals and road rules.",
            "Check your tyre pressure, brakes, and chain before setting out.",
            "Stay visible with bright clothing or lights, and maintain awareness of turning vehicles and pedestrians.",
            "Hydrate regularly from your bottle throughout the ride.",
        ]
    else:  # hiking
        return [
            "Wear sturdy footwear with good grip and ankle support for natural trails.",
            "Carry ample drinking water and take sips frequently to prevent dehydration.",
            "Stay on marked, accessible trails, keep track of time, and share your planned route with a contact.",
            "Check the weather forecast before heading out and wear sun protection (hat and sunscreen).",
        ]


# ── System prompt ─────────────────────────────────────────────────────────────

_TRAILMATE_SYSTEM = """\
You are TrailMate, an outdoor adventure planner. Your purpose is to help people \
spend meaningful time outdoors and reduce passive screen time.

STRICT RULES — follow all of these without exception:
1. Treat the user's location as a general geographic context only (city or region). \
Do NOT invent, guess, or name specific parks, trails, sanctuaries, reserves, roads, \
lakes, rivers, or landmarks. Use only generic descriptions such as \
"a nearby accessible green space" or "a pedestrian-friendly shaded pathway".
2. If the user themselves names a specific place in their request, you may reference \
it, because it came from the user, not from you.
3. For route_idea: describe the TYPE of route using TIME only, never distance. \
NEVER write kilometres, miles, meters, or any distance unit. \
Explain when to turn back based on elapsed minutes to finish on time.
4. For mission: write a concrete, time-structured plan with clear phases \
(warm-up -> main activity -> observation/task -> cooldown). Each phase must have \
a realistic minute allocation that adds up exactly to the available time.
5. For things_to_carry: list only practical gear for this specific day outing. \
Do NOT recommend tents, sleeping bags, camp stoves, or reusable plates for routine outings.
6. For challenge: provide one measurable sensory or nature-awareness task to complete \
during the outing. Make it achievable and enjoyable. Do not ban cameras.
7. For safety_tips: give 2-4 concise, practical tips relevant to the activity \
(hydration, footwear, traffic awareness, weather). Do NOT mention wildlife hazards.
8. If budget is 0, recommend only free public spaces and items the user already owns.\
"""


# ── Named-place and hazard regex patterns ─────────────────────────────────────

_NAMED_PLACE_RE = re.compile(
    r"\b(?:[A-Z][a-z]+\s+){1,4}"
    r"(?:Sanctuary|Wildlife|Reserve|"
    r"National\s+Park|State\s+Park|"
    r"Trail|Trails|Garden|Gardens|"
    r"Forest|Lake|River|Creek|"
    r"Beach|Hill|Hills|Valley|"
    r"Mount(?:ain)?|Drive|Highway|"
    r"Boulevard|Avenue|Promenade|"
    r"Expressway|Road|Path|Park)\b",
    re.IGNORECASE,
)

_DISTANCE_RE = re.compile(
    r"\b\d+[\d\s\-\u2013\.,]*(?:km|kilometers?|kilometres?|k\b|mi\b|miles?|meters?|metres?)\b",
    re.IGNORECASE,
)

_INAPPROPRIATE_GEAR_RE = re.compile(
    r"\b(?:tent|tents|sleeping\s+bag|sleeping\s+pad|camp\s+stove|stove|"
    r"plate|plates|reusable\s+plate|bowl|bowls|utensils?|cookware|"
    r"cooking\s+pot|pot|pots|pan|pans|tarp|pillow|cutlery|mess\s+kit|"
    r"gas\s+burner|campfire|bear\s+spray)\b",
    re.IGNORECASE,
)

_HAZARD_RE = re.compile(
    r"\b(?:wildlife|wild\s+animals?|snakes?|crocodiles?|bears?|tigers?|lions?|elephants?|"
    r"venom|scorpions?|leeches|rapids?|river\s+crossing|quicksand|avalanches?|crevasses?)\b",
    re.IGNORECASE,
)

_SAFE_ROUTE_TEMPLATE = (
    "Choose a pedestrian-friendly open area near you in {location} \u2014 "
    "a local park, promenade, or quiet shaded street. "
    "Walk outward for roughly half your {duration}-minute window, "
    "then loop or retrace to finish back where you started."
)


# ── Deterministic fallbacks ───────────────────────────────────────────────────

def _fallback_title(req: PlanRequest) -> str:
    intensity_word = {
        "low": "Scenic",
        "moderate": "Energizing",
        "high": "High-Tempo",
    }.get(req.intensity, "Outdoor")
    return f"{intensity_word} {req.time_available}-Minute {req.activity.title()} in {req.location}"


def _fallback_summary(req: PlanRequest) -> str:
    intensity_adj = {
        "low": "gentle and relaxing",
        "moderate": "steady and invigorating",
        "high": "dynamic and high-energy",
    }.get(req.intensity, "rewarding")
    budget_note = (
        "Completely free ($0 budget), utilizing accessible public spaces."
        if req.budget == 0
        else f"Planned with a flexible budget cap of {req.budget:.0f}."
    )
    return (
        f"A {intensity_adj} {req.time_available}-minute {req.activity} adventure in {req.location}. "
        f"Step away from screens, enjoy the fresh air, and move at your own pace. {budget_note}"
    )


def _fallback_mission(req: PlanRequest) -> str:
    return _build_actionable_mission(req)


def _fallback_route_idea(req: PlanRequest) -> str:
    return _build_route_idea(req)


def _fallback_things_to_carry(req: PlanRequest) -> list[str]:
    return _build_tailored_gear(req)


def _fallback_challenge(req: PlanRequest) -> str:
    return _build_tailored_challenge(req)


def _fallback_safety_tips(req: PlanRequest) -> list[str]:
    return _build_tailored_safety_tips(req)[:3]


# ── Prompt construction ───────────────────────────────────────────────────────

def _build_plan_prompt(req: PlanRequest) -> str:
    """Build the ChatML prompt for plan generation."""
    budget_str = "free ($0 budget)" if req.budget == 0 else f"budget limit up to {req.budget:.0f}"
    w, m, t, c = _calculate_stage_minutes(req.time_available)
    half_time = req.time_available // 2

    user_msg = (
        f"Create an outdoor adventure plan for a {req.time_available}-minute {req.activity} in {req.location}.\n"
        f"User parameters:\n"
        f"- Duration: exactly {req.time_available} minutes\n"
        f"- Activity: {req.activity}\n"
        f"- Intensity: {req.intensity}\n"
        f"- Budget: {budget_str} (spending limit, prefer free public spaces)\n"
        f"- Location: {req.location} (geographic context only, do not invent named parks or roads)\n\n"
        f"Output requirements:\n"
        f"1. title: Short catchy mission title without named landmarks.\n"
        f"2. summary: 2-3 sentences overview for exactly {req.time_available} minutes in {req.location}.\n"
        f"3. mission: An actionable step-by-step mission with clear stages totaling {req.time_available} minutes: "
        f"{w} min warm-up, {m} min main {req.activity} at {req.intensity} effort, "
        f"{f'{t} min nature observation task, ' if t > 0 else ''}{c} min cooldown.\n"
        f"4. route_idea: Describe the route pattern in TIME terms only (e.g. head outward for roughly {half_time} minutes, "
        f"then loop back to finish within {req.time_available} minutes). NEVER write kilometers or miles. No named places.\n"
        f"5. things_to_carry: 3-5 practical items for {req.activity} ({req.intensity} intensity, {req.time_available} min). "
        f"Do NOT suggest tents, reusable plates, stoves, or camping gear for routine day outings.\n"
        f"6. challenge: One measurable sensory or nature-awareness task (e.g. notice 3 plant details, identify 5 natural sounds). "
        f"Do not ban cameras or phones needed for safety.\n"
        f"7. safety_tips: 2-4 concise, practical tips (hydration, footwear, traffic awareness, weather). No wildlife hazards.\n\n"
        "Respond with ONLY a valid JSON object matching this schema (no markdown fences, no extra text):\n"
        "{\n"
        f'  "title": "{req.time_available}-Minute {req.activity.title()} Outing",\n'
        '  "summary": "overview text",\n'
        f'  "duration_minutes": {req.time_available},\n'
        f'  "activity": "{req.activity}",\n'
        f'  "difficulty": "{req.intensity}",\n'
        '  "mission": "actionable staged plan",\n'
        '  "route_idea": "time-based route pattern",\n'
        '  "things_to_carry": ["item 1", "item 2", "item 3"],\n'
        '  "challenge": "measurable task",\n'
        '  "safety_tips": ["tip 1", "tip 2"]\n'
        "}"
    )

    return build_chat_prompt(user_msg, system=_TRAILMATE_SYSTEM)


# ── Text extraction and parsing ───────────────────────────────────────────────

def _extract_json(raw: str) -> str:
    """Pull the outermost JSON object from raw LLM output."""
    md = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if md:
        return md.group(1)

    start = raw.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(raw[start:], start=start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return raw[start : i + 1]

    raise ValueError(
        f"No JSON object found in model output. "
        f"First 300 chars of output: {raw[:300]!r}"
    )


def _pin_known_fields(data: dict, req: PlanRequest) -> dict:
    """Force fields that must match the request exactly."""
    data["duration_minutes"] = req.time_available
    data["activity"] = req.activity
    data["difficulty"] = req.intensity
    return data


# ── Text normalization & field coercion ───────────────────────────────────────

def _normalize_text(text: str) -> str:
    """Fix UTF-8 mojibake / cp1252 misreadings."""
    if text.isascii():
        return text

    try:
        fixed = text.encode("latin-1").decode("utf-8")
        if len(fixed) < len(text):
            return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass

    _MOJIBAKE = [
        ("\u00e2\u20ac\u201c", "\u2013"),
        ("\u00e2\u20ac\u201d", "\u2014"),
        ("\u00e2\u20ac\u2018", "\u2018"),
        ("\u00e2\u20ac\u2122", "\u2019"),
        ("\u00e2\u20ac\u0153", "\u201c"),
        ("\u00e2\u20ac\x9d",   "\u201d"),
        ("\u00e2\u20ac\u00a6", "\u2026"),
        ("\u00e2 ",           "\u2014 "),
        ("\u00c3\u00a9",       "\u00e9"),
        ("\u00c3\u00a8",       "\u00e8"),
        ("\u00c3\u00a0",       "\u00e0"),
        ("\u00c3\u00bc",       "\u00fc"),
        ("\u00c3\u00b6",       "\u00f6"),
    ]
    result = text
    for bad, good in _MOJIBAKE:
        result = result.replace(bad, good)
    return result


def _normalize_plan_strings(data: dict) -> dict:
    """Apply _normalize_text to all strings and lists of strings."""
    for key, value in data.items():
        if isinstance(value, str):
            data[key] = _normalize_text(value)
        elif isinstance(value, list):
            data[key] = [
                _normalize_text(item) if isinstance(item, str) else item
                for item in value
            ]
    return data


def _normalize_list_field(data: dict, field_name: str) -> dict:
    """Coerce string representations into list[str]."""
    value = data.get(field_name)
    if value is None or isinstance(value, list):
        return data

    if not isinstance(value, str):
        return data

    for sep in ("\n", ";", ","):
        if sep in value:
            items = [item.strip() for item in value.split(sep)]
            data[field_name] = [item for item in items if item]
            return data

    data[field_name] = [value.strip()]
    return data


# ── Sanitizers ────────────────────────────────────────────────────────────────

def _sanitize_title(title: Any, req: PlanRequest) -> str:
    if not isinstance(title, str) or not title.strip():
        return _fallback_title(req)
    t = title.strip()
    if any(p in t.lower() for p in ("short catchy", "mission title", "string", "...", "overview text")):
        return _fallback_title(req)
    match = _NAMED_PLACE_RE.search(t)
    if match and match.group(0).lower() not in req.location.lower():
        return _fallback_title(req)
    return t


def _sanitize_summary(summary: Any, req: PlanRequest) -> str:
    if not isinstance(summary, str) or not summary.strip():
        return _fallback_summary(req)
    s = summary.strip()
    if len(s) < 40 or any(p in s.lower() for p in ("2-3 sentences", "overview text", "what this outing is", "outing overview", "string", "...")):
        return _fallback_summary(req)

    # Check for duration mismatch in summary
    dur_matches = re.findall(r"\b(\d+)(?:\s*-\s*\d+)?\s*(?:min|minute|minutes|hour|hours)\b", s, re.IGNORECASE)
    for dm in dur_matches:
        try:
            val = int(dm)
            if abs(val - req.time_available) > max(10, req.time_available * 0.2):
                return _fallback_summary(req)
        except ValueError:
            pass

    if s:
        s = s[0].upper() + s[1:]
    return s


def _sanitize_mission(mission: Any, req: PlanRequest) -> str:
    if not isinstance(mission, str) or not mission.strip():
        return _build_actionable_mission(req)

    m_text = mission.strip()

    # 1. Reject placeholder tokens
    placeholder_pattern = re.compile(
        r"(?:time-structured\s+plan|use\s+this\s+structure|suggested\s+structure|"
        r"short\s+catchy|<step|actionable\s+staged\s+plan|phases\s+totalling|\bstring\b|\.\.\.)",
        re.IGNORECASE,
    )
    if placeholder_pattern.search(m_text):
        return _build_actionable_mission(req)

    # 2. Reject distance units
    if _DISTANCE_RE.search(m_text):
        return _build_actionable_mission(req)

    # 3. Reject invented named places
    match = _NAMED_PLACE_RE.search(m_text)
    if match and match.group(0).lower() not in req.location.lower():
        return _build_actionable_mission(req)

    # 4. Require minimum detail and phase structure
    has_stages = any(s in m_text.lower() for s in ("warm-up", "warmup", "cooldown", "cool-down", "stretch", "phase", "stage", "finish", "return"))
    if len(m_text) < 50 or not has_stages:
        return _build_actionable_mission(req)

    return _normalize_text(m_text)


def _sanitize_route_idea(route_idea: Any, req: PlanRequest) -> tuple[str, bool]:
    """Detect and replace named places, distance language, or non-time-based route ideas."""
    if not isinstance(route_idea, str) or not route_idea.strip():
        return _build_route_idea(req), True

    r_text = route_idea.strip()

    # 1. Check for named places
    match = _NAMED_PLACE_RE.search(r_text)
    if match:
        matched_name = match.group(0)
        if matched_name.lower() not in req.location.lower():
            return _build_route_idea(req), True

    # 2. Check for distance units (km, miles, etc.)
    if _DISTANCE_RE.search(r_text):
        return _build_route_idea(req), True

    # 3. Check for placeholder text
    if any(p in r_text.lower() for p in ("time-based route pattern", "route type and pattern", "example:", "string", "<route", "...", "never write")):
        return _build_route_idea(req), True

    # 4. Length check
    if len(r_text) < 30:
        return _build_route_idea(req), True

    # 5. Check if it recommends a time-based route pattern
    time_terms = ("min", "minute", "minutes", "time", "window", "halfway", "turn back", "loop", "retrace")
    if not any(term in r_text.lower() for term in time_terms):
        return _build_route_idea(req), True

    if r_text:
        r_text = r_text[0].upper() + r_text[1:]

    return _normalize_text(r_text), False


def _sanitize_things_to_carry(raw_items: Any, req: PlanRequest) -> list[str]:
    """Filter out inappropriate items and placeholders; ensure 3-5 practical items."""
    cleaned: list[str] = []
    seen = set()

    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, str):
                continue
            item_text = item.strip()
            if not item_text:
                continue
            # Drop placeholders
            if any(p in item_text.lower() for p in ("practical item", "item 1", "item 2", "item 3", "string", "...")):
                continue
            # Drop camping / inappropriate gear for non-overnight outings
            if _INAPPROPRIATE_GEAR_RE.search(item_text):
                continue
            # Deduplicate
            key = item_text.lower()
            if key not in seen:
                seen.add(key)
                cleaned.append(item_text)

    # Supplement if fewer than 3 items
    tailored = _build_tailored_gear(req)
    for t_item in tailored:
        if len(cleaned) >= 4:
            break
        # Avoid duplicating concepts already present in cleaned items
        is_shoe = any(w in t_item.lower() for w in ("shoe", "footwear", "boot"))
        has_shoe = any(any(w in s for w in ("shoe", "footwear", "boot")) for s in seen)
        is_water = any(w in t_item.lower() for w in ("water", "hydrat", "bottle"))
        has_water = any(any(w in s for w in ("water", "hydrat", "bottle")) for s in seen)
        if (is_shoe and has_shoe) or (is_water and has_water):
            continue

        first_word = t_item.lower().split()[0]
        if not any(first_word in s for s in seen):
            cleaned.append(t_item)
            seen.add(t_item.lower())

    if len(cleaned) < 2:
        cleaned = tailored

    return cleaned[:5]


def _sanitize_challenge(challenge: Any, req: PlanRequest) -> str:
    """Ensure challenge is measurable, outdoor-focused, and non-empty without rigid camera bans."""
    if not isinstance(challenge, str) or not challenge.strip():
        return _build_tailored_challenge(req)

    c_text = challenge.strip()

    # Reject placeholders
    if any(p in c_text.lower() for p in ("measurable task", "one measurable", "<measurable", "string", "...")):
        return _build_tailored_challenge(req)

    # Reject rigid bans on taking cameras or carrying phones
    rigid_ban_re = re.compile(
        r"\b(?:leave\s+your\s+phone\s+at\s+home|no\s+cameras?\s+allowed|ban\s+all\s+phones?)\b",
        re.IGNORECASE,
    )
    if rigid_ban_re.search(c_text):
        return _build_tailored_challenge(req)

    # Require measurability (has numbers or count words)
    has_number = bool(re.search(r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b", c_text, re.IGNORECASE))
    if not has_number:
        return _build_tailored_challenge(req)

    return _normalize_text(c_text)


def _sanitize_safety_tips(raw_tips: Any, req: PlanRequest) -> list[str]:
    """Ensure 2-4 concise, practical tips without wildlife hazards."""
    cleaned: list[str] = []
    seen = set()

    if isinstance(raw_tips, list):
        for tip in raw_tips:
            if not isinstance(tip, str):
                continue
            t = tip.strip()
            if not t:
                continue
            # Strip leading conjunctions (e.g. "and wear comfortable shoes")
            for prefix in ("and ", "also ", "or "):
                if t.lower().startswith(prefix):
                    t = t[len(prefix):].strip()
            if t:
                t = t[0].upper() + t[1:]
            if not t:
                continue
            # Drop placeholders
            if any(p in t.lower() for p in ("tip 1", "tip 2", "concise practical tip", "practical tip", "string", "...")):
                continue
            # Drop wildlife / extreme terrain hazards
            if _HAZARD_RE.search(t):
                continue
            # Deduplicate
            key = t.lower()
            if key not in seen:
                seen.add(key)
                cleaned.append(t)

    # Guarantee between 2 and 4 tips
    if len(cleaned) < 2:
        tailored = _build_tailored_safety_tips(req)
        for tt in tailored:
            if len(cleaned) >= 3:
                break
            if tt.lower() not in seen:
                cleaned.append(tt)
                seen.add(tt.lower())

    if len(cleaned) < 2:
        cleaned = _build_tailored_safety_tips(req)[:3]

    return cleaned[:4]


# ── Public API ────────────────────────────────────────────────────────────────

def create_plan(request: PlanRequest) -> PlanResponse:
    """
    Generate a structured, grounded outdoor adventure plan.

    Pipeline:
      1. Build the ChatML prompt with activity-aware grounding rules.
      2. Call generate_text() with token budget.
      3. Extract the JSON object from raw stdout.
      4. Parse JSON -> dict.
      5. Pin known fields (duration, activity, difficulty) from request.
      6. Normalise text (mojibake) and coerce list fields.
      7. Sanitize: remove hallucinated named places, distance language,
         camping gear, camera-only challenges, inappropriate safety tips.
      8. Apply deterministic fallbacks for any missing or invalid fields.
      9. Validate the final dict against PlanResponse.

    Args:
        request: A validated PlanRequest instance.

    Returns:
        A grounded PlanResponse with all required fields.

    Raises:
        RuntimeError: On LLM errors, invalid JSON, or schema mismatch.
                      The caller (FastAPI route) converts this to HTTP 503.
    """
    prompt = _build_plan_prompt(request)

    # ── Step 1: Generate ──────────────────────────────────────────────────────
    try:
        raw = generate_text(prompt, max_tokens=_PLAN_MAX_TOKENS)
    except RuntimeError:
        raise

    # ── Step 2: Extract JSON ──────────────────────────────────────────────────
    try:
        json_str = _extract_json(raw)
    except ValueError as exc:
        raise RuntimeError(f"Model did not return a JSON object. {exc}") from exc

    # ── Step 3: Parse ─────────────────────────────────────────────────────────
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Model returned malformed JSON: {exc}. Snippet: {json_str[:300]!r}"
        ) from exc

    if not isinstance(data, dict):
        data = {}

    # ── Step 4: Pin known fields ──────────────────────────────────────────────
    data = _pin_known_fields(data, request)

    # ── Step 5: Normalise text (fix encoding mojibake) ────────────────────────
    data = _normalize_plan_strings(data)

    # ── Step 6: Coerce list fields ────────────────────────────────────────────
    for _list_field in ("things_to_carry", "safety_tips"):
        data = _normalize_list_field(data, _list_field)

    # ── Step 7: Sanitize content ──────────────────────────────────────────────
    data["title"] = _sanitize_title(data.get("title"), request)
    data["summary"] = _sanitize_summary(data.get("summary"), request)
    data["mission"] = _sanitize_mission(data.get("mission"), request)
    data["route_idea"], _ = _sanitize_route_idea(data.get("route_idea"), request)
    data["things_to_carry"] = _sanitize_things_to_carry(data.get("things_to_carry"), request)
    data["challenge"] = _sanitize_challenge(data.get("challenge"), request)
    data["safety_tips"] = _sanitize_safety_tips(data.get("safety_tips"), request)

    # ── Step 8: Apply deterministic fallbacks for any missing fields ──────────
    if not data.get("title"):
        data["title"] = _fallback_title(request)
    if not data.get("summary"):
        data["summary"] = _fallback_summary(request)
    if not data.get("mission"):
        data["mission"] = _fallback_mission(request)
    if not data.get("route_idea"):
        data["route_idea"] = _fallback_route_idea(request)
    if not data.get("challenge"):
        data["challenge"] = _fallback_challenge(request)
    if not data.get("things_to_carry"):
        data["things_to_carry"] = _fallback_things_to_carry(request)
    if not data.get("safety_tips"):
        data["safety_tips"] = _fallback_safety_tips(request)

    # ── Step 9: Validate schema ───────────────────────────────────────────────
    try:
        return PlanResponse(**data)
    except (ValidationError, TypeError) as exc:
        raise RuntimeError(
            f"Model response does not satisfy the PlanResponse schema: {exc}"
        ) from exc
