"""Expert image rating app — per-user scoring for choose/ images."""

from __future__ import annotations

import json
import random
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "choose"
RATINGS_DIR = BASE_DIR / "expert_ratings"
STUDY_DATA_PATH = BASE_DIR / "study_data864.json"
METAPHOR_DATA_PATH = BASE_DIR / "Metaphor_data.json"

DEFAULT_USERS = ["Christophe", "Thomas", "Yunfan"]

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

EMOTION_GROUPS = [
    {
        "key": "hopeful_content_happy_excited",
        "label": "hopeful, content, happy, excited",
    },
    {
        "key": "surprised_awestruck",
        "label": "surprised, awestruck",
    },
    {
        "key": "shocked_sad_concerned",
        "label": "shocked, sad, concerned",
    },
    {
        "key": "bored_overwhelmed",
        "label": "bored, overwhelmed",
    },
]
EMOTION_OPTIONS = [
    part.strip()
    for group in EMOTION_GROUPS
    for part in group["label"].split(",")
]

METAPHOR_OPTIONS = ["Yes", "No", "Unsure"]

VALENCE_LABELS = {
    1: "1 · Very negative",
    2: "2 · Negative",
    3: "3 · Neutral",
    4: "4 · Positive",
    5: "5 · Very positive",
}
INTENSITY_LABELS = {
    1: "1 · Very weak",
    2: "2 · Weak",
    3: "3 · Moderate",
    4: "4 · Strong",
    5: "5 · Very strong",
}
SCORE_OPTIONS = [1, 2, 3, 4, 5]
GALLERY_FRAME = 480
NAV_PAGES = ["Infographic Dataset Overview", "Rate", "Results"]


def reset_score_key(key: str) -> None:
    """Drop leftover values from older radio (string) formats."""
    if key in st.session_state and st.session_state[key] not in SCORE_OPTIONS:
        del st.session_state[key]

# Soft teal / slate theme (avoid bright red)
APP_CSS = """
<style>
:root {
  --bg: #f4f7f6;
  --card: #ffffff;
  --ink: #2c3e3a;
  --muted: #5f726c;
  --accent: #3d7a6e;
  --accent-soft: #d8ebe5;
  --border: #d5e2dd;
  --warn-bg: #f3efe6;
  --warn-ink: #7a6a45;
  --ok-bg: #e6f2ed;
  --ok-ink: #2f6b5a;
}

html, body, [class*="css"] {
  color: var(--ink);
}

.stApp {
  background: linear-gradient(165deg, #eef5f2 0%, #f7f5f1 48%, #eef2f6 100%);
}

[data-testid="stSidebar"] {
  background: #e8f1ee !important;
  border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] * {
  color: var(--ink) !important;
}

h1, h2, h3, h4, h5, h6 {
  color: var(--ink) !important;
  letter-spacing: -0.02em;
}

.stCaption, [data-testid="stCaptionContainer"] {
  color: var(--muted) !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 0.4rem 0.6rem;
}

.stButton > button {
  border-radius: 10px !important;
  border: 1px solid var(--border) !important;
  color: var(--ink) !important;
  background: #fff !important;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.stButton > button:hover {
  background: var(--accent-soft) !important;
  border-color: #b7d2c9 !important;
}

.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"],
button[kind="primary"] {
  background: var(--accent) !important;
  color: #f7fbf9 !important;
  border: 1px solid #34685e !important;
}
.stButton > button[kind="primary"]:hover,
button[kind="primary"]:hover {
  background: #32675d !important;
  border-color: #2a574f !important;
  color: #fff !important;
}

.stSlider [data-baseweb="slider"] div[role="slider"] {
  background-color: var(--accent) !important;
}
.stSlider [data-baseweb="slider"] div[data-testid="stThumbValue"] {
  color: var(--accent) !important;
}

div[data-baseweb="select"] > div,
.stTextInput input,
.stTextArea textarea {
  border-radius: 10px !important;
  border-color: var(--border) !important;
  background: #fff !important;
}

/* Soften alerts — no bright red */
div[data-testid="stAlert"] {
  border-radius: 12px !important;
  border: 1px solid var(--border) !important;
}
div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
  color: var(--ink) !important;
}
/* error → warm sand */
div[data-baseweb="notification"]:has(svg[data-testid="stIconError"]),
div[data-testid="stAlert"]:has([data-testid="stIconError"]) {
  background: var(--warn-bg) !important;
  color: var(--warn-ink) !important;
}
/* success / info → soft green / slate */
div[data-testid="stAlert"]:has([data-testid="stIconSuccess"]),
div[data-testid="stAlert"]:has([data-testid="stIconInfo"]) {
  background: var(--ok-bg) !important;
  color: var(--ok-ink) !important;
}

.stProgress > div > div > div > div {
  background-color: var(--accent) !important;
}

.stExpander {
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  background: var(--card) !important;
}

.rate-chip {
  display: inline-block;
  padding: 0.25rem 0.7rem;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 0.6rem;
}
.section-label {
  font-size: 0.95rem;
  font-weight: 650;
  color: var(--ink);
  margin: 0.55rem 0 0.25rem 0;
}
.soft-note {
  color: var(--muted);
  font-size: 0.88rem;
  margin-bottom: 0.8rem;
}
/* Keep the rated image large and sharp */
.main-image img {
  width: 100% !important;
  max-height: 78vh !important;
  height: auto !important;
  object-fit: contain !important;
}
div[data-testid="stImage"] img {
  max-height: 78vh;
  object-fit: contain;
}

/* Wide: two columns. Below 1400px: stack image then form. */
@media (max-width: 1400px) {
  div[data-testid="stHorizontalBlock"]:has(.main-image) {
    flex-direction: column !important;
    flex-wrap: nowrap !important;
    gap: 1rem !important;
  }
  div[data-testid="stHorizontalBlock"]:has(.main-image) > div[data-testid="column"],
  div[data-testid="stHorizontalBlock"]:has(.main-image) > div[data-testid="stColumn"] {
    width: 100% !important;
    flex: 1 1 100% !important;
    min-width: 100% !important;
  }
  .main-image img,
  div[data-testid="stHorizontalBlock"]:has(.main-image) div[data-testid="stImage"] img {
    max-height: 52vh !important;
  }
}
</style>
"""


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def ensure_ratings_dir() -> None:
    RATINGS_DIR.mkdir(parents=True, exist_ok=True)


def user_json_path(user: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in user.strip())
    return RATINGS_DIR / f"{safe}.json"


def load_user_ratings(user: str) -> dict:
    path = user_json_path(user)
    if not path.exists():
        return {"user": user, "ratings": {}}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "ratings" not in data:
        data["ratings"] = {}
    data["user"] = user
    return data


def save_user_ratings(user: str, data: dict) -> None:
    ensure_ratings_dir()
    data["user"] = user
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = user_json_path(user)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_known_users() -> list[str]:
    ensure_ratings_dir()
    users = list(DEFAULT_USERS)
    for path in sorted(RATINGS_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                name = json.load(f).get("user") or path.stem
        except (json.JSONDecodeError, OSError):
            name = path.stem
        if name not in users:
            users.append(name)
    return users


def list_images(image_dir: str) -> list[dict]:
    root = Path(image_dir)
    if not root.exists():
        return []
    items: list[dict] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            continue
        rel = path.relative_to(root).as_posix()
        # Edited copies live under choose/**/modify and should not be rated or shown.
        if "modify" in {part.lower() for part in Path(rel).parts}:
            continue
        items.append(
            {
                "image_id": rel,
                "path": str(path),
                "filename": path.name,
            }
        )
    return items


@st.cache_data(show_spinner=False)
def gallery_frame(path: str, size: int, mtime_ns: int) -> Image.Image:
    """Fit the full image inside a fixed square so gallery cells share one height."""
    im = Image.open(path).convert("RGB")
    im.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (size, size), (244, 247, 246))
    canvas.paste(im, ((size - im.width) // 2, (size - im.height) // 2))
    return canvas


def pending_images(all_images: list[dict], rated_ids: set[str]) -> list[dict]:
    return [img for img in all_images if img["image_id"] not in rated_ids]


def shuffled_for_user(images: list[dict], user: str) -> list[dict]:
    """Deterministic shuffle per identity so refresh keeps the same order."""
    items = list(images)
    rng = random.Random(user.strip().casefold())
    rng.shuffle(items)
    return items


def form_keys_for(image_id: str) -> list[str]:
    keys = [
        f"meta_{image_id}",
        f"valence_{image_id}",
        f"intensity_{image_id}",
        f"expl_{image_id}",
        f"rq1_{image_id}",
        f"rq2_{image_id}",
    ]
    keys.extend(f"top3_{image_id}_{emo}" for emo in EMOTION_OPTIONS)
    return keys


def clear_form_keys(image_id: str) -> None:
    for key in form_keys_for(image_id):
        st.session_state.pop(key, None)


def apply_theme() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session / identity
# ---------------------------------------------------------------------------
def _set_nav_page(page: str) -> None:
    st.session_state.nav_page = page


def init_state() -> None:
    if "identity" not in st.session_state:
        st.session_state.identity = None
    if "rate_index" not in st.session_state:
        st.session_state.rate_index = 0


def render_identity_gate() -> None:
    st.title("Expert Image Rating")
    st.markdown(
        '<p class="soft-note">Select your identity to start rating or view results.</p>',
        unsafe_allow_html=True,
    )

    users = list_known_users()
    col1, col2 = st.columns([2, 1])
    with col1:
        choice = st.selectbox("Identity", options=users, index=0)
    with col2:
        st.write("")
        st.write("")
        custom = st.checkbox("Add new identity")

    new_name = ""
    if custom:
        new_name = st.text_input("New identity name", placeholder="e.g. Alice").strip()

    if st.button("Continue", type="primary", use_container_width=True):
        identity = new_name if custom and new_name else choice
        if not identity:
            st.warning("Please enter a name.")
            return
        st.session_state.identity = identity
        st.session_state.rate_index = 0
        data = load_user_ratings(identity)
        if not user_json_path(identity).exists():
            save_user_ratings(identity, data)
        st.rerun()


# ---------------------------------------------------------------------------
# Rate page
# ---------------------------------------------------------------------------
def render_rate_page(identity: str, all_images: list[dict]) -> None:
    data = load_user_ratings(identity)
    rated_ids = set(data["ratings"].keys())
    ordered = shuffled_for_user(all_images, identity)
    todo = pending_images(ordered, rated_ids)

    st.title("Rate images")
    st.markdown(
        f'<p class="soft-note">Signed in as <b>{identity}</b></p>',
        unsafe_allow_html=True,
    )

    done = len(rated_ids)
    total = len(all_images)
    st.progress(done / total if total else 0.0, text=f"Progress: {done} / {total}")

    if not todo:
        st.success("All current images are rated. New files added later will show up here.")
        st.button(
            "Go to results",
            on_click=_set_nav_page,
            args=("Results",),
        )
        return

    if st.session_state.rate_index >= len(todo):
        st.session_state.rate_index = 0
    idx = st.session_state.rate_index
    img = todo[idx]

    st.markdown(
        f'<div class="rate-chip">Image {idx + 1} of {len(todo)} remaining'
        f" · {img['filename']}</div>",
        unsafe_allow_html=True,
    )

    # Image-first layout: 2 columns on wide screens; CSS stacks on narrow
    left, right = st.columns([2.4, 1.0], gap="large")

    with left:
        st.markdown('<div class="main-image">', unsafe_allow_html=True)
        st.image(img["path"], use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="rate-form-panel">', unsafe_allow_html=True)
        image_id = img["image_id"]
        reset_score_key(f"valence_{image_id}")
        reset_score_key(f"intensity_{image_id}")

        # Keep filled values when required fields are missing.
        st.markdown(
            '<div class="section-label">1. Does this infographic contain a visual metaphor?</div>',
            unsafe_allow_html=True,
        )
        is_metaphor = st.radio(
            "Does this infographic contain a visual metaphor?",
            options=METAPHOR_OPTIONS,
            horizontal=True,
            index=None,
            key=f"meta_{image_id}",
            label_visibility="collapsed",
        )

        st.markdown('<div class="section-label">2. Valence</div>', unsafe_allow_html=True)
        st.caption("Very negative → Very positive")
        valence = st.select_slider(
            "Valence",
            options=SCORE_OPTIONS,
            value=3,
            format_func=lambda x: VALENCE_LABELS[x],
            key=f"valence_{image_id}",
            label_visibility="collapsed",
        )

        st.markdown('<div class="section-label">3. Emotional intensity</div>', unsafe_allow_html=True)
        st.caption("Very weak → Very strong")
        intensity = st.select_slider(
            "Emotional intensity",
            options=SCORE_OPTIONS,
            value=3,
            format_func=lambda x: INTENSITY_LABELS[x],
            key=f"intensity_{image_id}",
            label_visibility="collapsed",
        )

        st.markdown(
            '<div class="section-label">4. Top emotions</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Which emotions are most prominently conveyed by this infographic? "
            "Select up to three emotions. You may select fewer than three if appropriate. "
            "The selected emotions do not need to be ranked."
        )
        selected_now = [
            emo
            for emo in EMOTION_OPTIONS
            if st.session_state.get(f"top3_{image_id}_{emo}")
        ]
        at_max = len(selected_now) >= 3
        top_emotions: list[str] = []
        emo_left, emo_right = st.columns(2)
        for i, emo in enumerate(EMOTION_OPTIONS):
            with emo_left if i % 2 == 0 else emo_right:
                checked = st.checkbox(
                    emo,
                    key=f"top3_{image_id}_{emo}",
                    disabled=at_max and emo not in selected_now,
                )
            if checked:
                top_emotions.append(emo)
        if at_max:
            st.caption("3 selected. Uncheck one to choose a different emotion.")

        st.markdown(
            '<div class="section-label">5. Suitability for RQ1</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Is this infographic suitable for comparing affective interpretations "
            "between humans and VLMs? Consider whether the infographic is legible, "
            "understandable, and can be meaningfully evaluated for its emotional expression."
        )
        st.caption(
            "A clear or strong emotion is not required. Images with ambiguous, weak, "
            "or even neutral emotions may still be valuable for RQ1."
        )
        suitable_rq1 = st.radio(
            "Suitability for RQ1",
            options=METAPHOR_OPTIONS,
            horizontal=True,
            index=None,
            key=f"rq1_{image_id}",
            label_visibility="collapsed",
        )

        st.markdown(
            '<div class="section-label">6. Suitability for RQ2</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Is this infographic suitable for controlled modifications of its visual design? "
            "Consider whether elements such as color, text, imagery, or metaphorical meaning "
            "can be modified while preserving the underlying information."
        )
        suitable_rq2 = st.radio(
            "Suitability for RQ2",
            options=METAPHOR_OPTIONS,
            horizontal=True,
            index=None,
            key=f"rq2_{image_id}",
            label_visibility="collapsed",
        )

        st.markdown(
            '<div class="section-label">7. Comments (optional)</div>',
            unsafe_allow_html=True,
        )
        explanation = st.text_area(
            "Comments",
            placeholder="Ambiguous judgments or concerns about this infographic...",
            height=80,
            key=f"expl_{image_id}",
            label_visibility="collapsed",
        )

        submitted = st.button(
            "Submit & next", type="primary", use_container_width=True
        )

        if submitted:
            missing = []
            if is_metaphor is None:
                missing.append("visual metaphor")
            if suitable_rq1 is None:
                missing.append("RQ1 suitability")
            if suitable_rq2 is None:
                missing.append("RQ2 suitability")
            if missing:
                st.warning("Please complete: " + ", ".join(missing) + ".")
            else:
                entry = {
                    "image_id": image_id,
                    "filename": img["filename"],
                    "is_metaphor": is_metaphor,
                    "valence": int(valence),
                    "intensity": int(intensity),
                    "top_emotions": list(top_emotions),
                    "explanation": (explanation or "").strip(),
                    "suitable_for_rq1": suitable_rq1,
                    "suitable_for_rq2": suitable_rq2,
                    "rated_at": datetime.now(timezone.utc).isoformat(),
                }
                data["ratings"][image_id] = entry
                save_user_ratings(identity, data)
                clear_form_keys(image_id)
                st.toast(f"Saved · {img['filename']}")
                st.rerun()

        nav_l, nav_r = st.columns(2)
        with nav_l:
            if st.button("← Previous", disabled=idx <= 0, use_container_width=True):
                st.session_state.rate_index = max(0, idx - 1)
                st.rerun()
        with nav_r:
            if st.button(
                "Skip →", disabled=idx >= len(todo) - 1, use_container_width=True
            ):
                st.session_state.rate_index = min(len(todo) - 1, idx + 1)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Results page
# ---------------------------------------------------------------------------
def load_all_ratings() -> dict[str, dict]:
    ensure_ratings_dir()
    out: dict[str, dict] = {}
    for path in sorted(RATINGS_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        user = data.get("user") or path.stem
        out[user] = data.get("ratings") or {}
    return out


def _metaphor_label(value) -> str:
    if value is True or value == "Yes":
        return "Yes"
    if value is False or value == "No":
        return "No"
    if value == "Unsure":
        return "Unsure"
    return "—"


@st.cache_data(show_spinner=False)
def load_study_data(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


@st.cache_data(show_spinner=False)
def load_metaphor_data(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _is_normal_image(img: dict) -> bool:
    name = img["filename"].lower()
    folder = img["image_id"].split("/", 1)[0].lower()
    return name.startswith("pic") or folder == "normal"


def _is_metaphor_image(img: dict) -> bool:
    folder = img["image_id"].split("/", 1)[0].lower()
    return folder == "metaphor"


def _study_record(study: dict, filename: str) -> dict | None:
    stem = Path(filename).stem
    if stem in study:
        rec = study[stem]
        return rec if isinstance(rec, dict) else None
    match = re.match(r"(pic\d+)", stem, flags=re.IGNORECASE)
    if match:
        key = match.group(1)
        # JSON keys are like "pic417"
        for candidate in (key, key.lower()):
            rec = study.get(candidate)
            if isinstance(rec, dict):
                return rec
    return None


def _metaphor_record(meta: dict, filename: str) -> dict | None:
    stem = Path(filename).stem
    base = stem.split("_", 1)[0]
    for key in (filename, f"{stem}.png", f"{base}.png"):
        rec = meta.get(key)
        if isinstance(rec, dict):
            return rec
    return None


def _top3_affects(rec: dict) -> list[tuple[str, float]]:
    pairs: list[tuple[str, float]] = []
    for key, value in rec.items():
        if not isinstance(key, str) or not key.endswith("_mean"):
            continue
        if key == "primary_affect_mean":
            continue
        if isinstance(value, (int, float)):
            pairs.append((key[: -len("_mean")], float(value)))
    pairs.sort(key=lambda item: item[1], reverse=True)
    return pairs[:3]


def _render_image_attributes(img: dict, study: dict, metaphor: dict) -> None:
    st.markdown("##### Image attributes")
    if _is_normal_image(img):
        rec = _study_record(study, img["filename"])
        if not rec:
            st.caption("No matching record in study_data864.json.")
            return
        affect = rec.get("primary_affect", "—")
        mean = rec.get("primary_affect_mean", "—")
        st.write(f"**Primary affect:** {affect} ({mean})")
        top3 = _top3_affects(rec)
        if top3:
            lines = ", ".join(f"{name} ({value:g})" for name, value in top3)
            st.write(f"**Top 3 affect:** {lines}")
        else:
            st.write("**Top 3 affect:** —")
        return

    if _is_metaphor_image(img):
        rec = _metaphor_record(metaphor, img["filename"])
        if not rec:
            st.caption("No matching record in Metaphor_data.json.")
            return
        strategies = [
            ann.get("strategy")
            for ann in (rec.get("annotations") or [])
            if isinstance(ann, dict) and ann.get("strategy")
        ]
        shown = ", ".join(strategies) if strategies else "—"
        st.write(f"**Strategy:** {shown}")
        return

    st.caption("No attribute source for this image.")


def _distribution_chart(counts: Counter, value_title: str) -> None:
    if not counts:
        st.caption("No matching records.")
        return
    rows = [{"category": name, "count": count} for name, count in counts.items()]
    chart = (
        alt.Chart(alt.Data(values=rows))
        .mark_bar(color="#3d7a6e", cornerRadiusEnd=4)
        .encode(
            x=alt.X("count:Q", title=value_title, axis=alt.Axis(tickMinStep=1)),
            y=alt.Y("category:N", sort="-x", title=None),
            tooltip=[
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("count:Q", title=value_title),
            ],
        )
        .properties(height=max(160, 36 * len(rows)))
    )
    st.altair_chart(chart, use_container_width=True)


def _collect_distributions(
    all_images: list[dict], study: dict, metaphor: dict
) -> dict:
    primary: Counter = Counter()
    top3: Counter = Counter()
    strategy: Counter = Counter()
    normal_n = metaphor_n = 0
    normal_missing = metaphor_missing = 0

    for img in all_images:
        if _is_normal_image(img):
            normal_n += 1
            rec = _study_record(study, img["filename"])
            if not rec or not rec.get("primary_affect"):
                normal_missing += 1
                continue
            primary[str(rec["primary_affect"])] += 1
            for name, _value in _top3_affects(rec):
                top3[name] += 1
        elif _is_metaphor_image(img):
            metaphor_n += 1
            rec = _metaphor_record(metaphor, img["filename"])
            strategies = [
                str(ann["strategy"])
                for ann in (rec.get("annotations") or [])
                if isinstance(ann, dict) and ann.get("strategy")
            ] if rec else []
            if not strategies:
                metaphor_missing += 1
                continue
            strategy.update(strategies)

    return {
        "normal_n": normal_n,
        "metaphor_n": metaphor_n,
        "normal_missing": normal_missing,
        "metaphor_missing": metaphor_missing,
        "primary": primary,
        "top3": top3,
        "strategy": strategy,
    }


def render_welcome_page(all_images: list[dict]) -> None:
    st.title("Infographic Dataset Overview")
    st.markdown(
        '<p class="soft-note">Distribution of the images currently in this set.</p>',
        unsafe_allow_html=True,
    )

    study = load_study_data(str(STUDY_DATA_PATH))
    metaphor = load_metaphor_data(str(METAPHOR_DATA_PATH))
    stats = _collect_distributions(all_images, study, metaphor)

    c1, c2, c3 = st.columns(3)
    c1.metric("Images", len(all_images))
    c2.metric("Normal", stats["normal_n"])
    c3.metric("Metaphor", stats["metaphor_n"])

    go_rate, go_results = st.columns(2)
    with go_rate:
        st.button(
            "Start rating",
            type="primary",
            use_container_width=True,
            on_click=_set_nav_page,
            args=("Rate",),
        )
    with go_results:
        st.button(
            "View results",
            use_container_width=True,
            on_click=_set_nav_page,
            args=("Results",),
        )

    st.subheader("Normal images")
    st.caption(
        "Primary affect is one label per image. "
        "Top 3 affect counts each image’s three strongest emotion means."
    )
    if stats["normal_missing"]:
        st.caption(f"{stats['normal_missing']} normal image(s) have no study record.")
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Primary affect**")
        _distribution_chart(stats["primary"], "Images")
    with right:
        st.markdown("**Top 3 affect**")
        _distribution_chart(stats["top3"], "Appearances")

    st.subheader("Metaphor images")
    st.caption("Strategy counts each annotation on an image.")
    if stats["metaphor_missing"]:
        st.caption(f"{stats['metaphor_missing']} metaphor image(s) have no strategy.")
    st.markdown("**Strategy**")
    _distribution_chart(stats["strategy"], "Annotations")


def render_results_page(all_images: list[dict]) -> None:
    st.title("Results")
    st.markdown(
        '<p class="soft-note">Per-image ratings from all experts.</p>',
        unsafe_allow_html=True,
    )

    all_by_user = load_all_ratings()
    users = sorted(all_by_user.keys())

    # Full dump for backup (important on Streamlit Cloud: disk can reset)
    ensure_ratings_dir()
    export_payload = {}
    for path in sorted(RATINGS_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                export_payload[path.stem] = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
    st.download_button(
        "Download all ratings (JSON)",
        data=json.dumps(export_payload, ensure_ascii=False, indent=2),
        file_name=f"expert_ratings_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True,
    )

    if not all_images:
        st.warning("No images found.")
        return

    filter_user = st.multiselect(
        "Filter raters shown",
        options=users,
        default=users,
    )

    filt_status, filt_kind = st.columns(2)
    with filt_status:
        status_pick = st.pills(
            "Completion",
            options=["Completed", "Not completed"],
            selection_mode="multi",
            default=["Completed", "Not completed"],
            key="results_completion",
        )
    with filt_kind:
        kind_pick = st.pills(
            "Image type",
            options=["Metaphor", "Non-metaphor"],
            selection_mode="multi",
            default=["Metaphor", "Non-metaphor"],
            key="results_image_type",
        )
    status_pick = status_pick or []
    kind_pick = kind_pick or []
    st.caption(
        "Completed means every rater has submitted. "
        "Metaphor images are in the Metaphor folder; "
        "filenames starting with pic count as non-metaphor."
    )

    def _is_complete(img: dict) -> bool:
        if not users:
            return False
        image_id = img["image_id"]
        return all(image_id in all_by_user.get(user, {}) for user in users)

    def _is_metaphor_item(img: dict) -> bool:
        return _is_metaphor_image(img) and not img["filename"].lower().startswith("pic")

    shown = []
    for img in all_images:
        complete = _is_complete(img)
        if complete and "Completed" not in status_pick:
            continue
        if not complete and "Not completed" not in status_pick:
            continue
        metaphor_item = _is_metaphor_item(img)
        if metaphor_item and "Metaphor" not in kind_pick:
            continue
        if not metaphor_item and "Non-metaphor" not in kind_pick:
            continue
        shown.append(img)

    study = load_study_data(str(STUDY_DATA_PATH))
    metaphor = load_metaphor_data(str(METAPHOR_DATA_PATH))

    focus_id = st.session_state.get("results_focus")
    focused = next((img for img in all_images if img["image_id"] == focus_id), None)

    if focused is not None:
        if st.button("← Back to gallery"):
            st.session_state.results_focus = None
            st.rerun()

        image_id = focused["image_id"]
        filename = focused["filename"]
        n_rated = len([u for u in users if image_id in all_by_user.get(u, {})])
        raters_for_img = [
            (u, all_by_user[u][image_id])
            for u in filter_user
            if image_id in all_by_user.get(u, {})
        ]

        st.subheader(filename)
        st.caption(f"{n_rated}/{len(users)} rated")
        c_img, c_meta = st.columns([1.1, 1.0], gap="large")
        with c_img:
            st.image(focused["path"], use_container_width=True)
        with c_meta:
            _render_image_attributes(focused, study, metaphor)
            st.divider()
            if not raters_for_img:
                st.info("No ratings yet for the selected raters.")
            else:
                for user, r in raters_for_img:
                    st.markdown(f"##### {user}")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Metaphor", _metaphor_label(r.get("is_metaphor")))
                    m2.metric("Valence", r.get("valence", "—"))
                    m3.metric("Intensity", r.get("intensity", "—"))
                    q1, q2 = st.columns(2)
                    rq1 = r.get("suitable_for_rq1", r.get("suitable_for_database"))
                    q1.metric("RQ1", _metaphor_label(rq1))
                    q2.metric("RQ2", _metaphor_label(r.get("suitable_for_rq2")))
                    top_emotions = r.get("top_emotions")
                    if isinstance(top_emotions, list):
                        shown = ", ".join(top_emotions) if top_emotions else "—"
                        st.write(f"**Top emotions:** {shown}")
                    else:
                        emos = r.get("emotions") or {}
                        for group in EMOTION_GROUPS:
                            val = emos.get(group["key"], "—")
                            st.write(f"- **{group['label']}:** {val}")
                    st.write(f"**Comments:** {r.get('explanation', '—') or '—'}")
                    st.caption(f"Rated at: {r.get('rated_at', '—')}")
                    st.divider()
        return

    st.markdown(f"**{len(shown)}** / {len(all_images)} images")
    if not shown:
        st.info("No images match these filters.")
        return
    cols_n = 4
    for start in range(0, len(shown), cols_n):
        cols = st.columns(cols_n, gap="medium")
        for col, img in zip(cols, shown[start : start + cols_n]):
            image_id = img["image_id"]
            n_rated = len([u for u in users if image_id in all_by_user.get(u, {})])
            with col:
                st.image(
                    gallery_frame(
                        img["path"],
                        GALLERY_FRAME,
                        Path(img["path"]).stat().st_mtime_ns,
                    ),
                    use_container_width=True,
                )
                st.caption(f"{img['filename']}  ·  {n_rated}/{len(users)} rated")
                if st.button(
                    "View details",
                    key=f"results_open_{image_id}",
                    use_container_width=True,
                ):
                    st.session_state.results_focus = image_id
                    st.rerun()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="Expert Image Rating",
        page_icon="📝",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme()
    init_state()
    ensure_ratings_dir()

    if st.session_state.get("nav_page") not in NAV_PAGES:
        st.session_state.nav_page = "Infographic Dataset Overview"

    identity = st.session_state.identity
    if not identity:
        render_identity_gate()
        return

    with st.sidebar:
        st.markdown(f"**Identity:** {identity}")
        if st.button("Switch identity", use_container_width=True):
            st.session_state.identity = None
            st.session_state.rate_index = 0
            st.rerun()

        st.radio("Page", options=NAV_PAGES, key="nav_page")

    if not IMAGE_DIR.exists():
        st.warning(f"Image directory not found: {IMAGE_DIR}")
        return

    all_images = list_images(str(IMAGE_DIR))
    if not all_images:
        st.warning("No images found.")
        return

    if st.session_state.nav_page == "Infographic Dataset Overview":
        render_welcome_page(all_images)
    elif st.session_state.nav_page == "Rate":
        render_rate_page(identity, all_images)
    else:
        render_results_page(all_images)


if __name__ == "__main__":
    main()
