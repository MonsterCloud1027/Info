"""Expert image rating app — per-user scoring for choose/ images."""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "choose"
RATINGS_DIR = BASE_DIR / "expert_ratings"

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

YES_NO = ["Yes", "No"]

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

/* Wide: two columns (default Streamlit layout). Narrow: stack image then form. */
@media (max-width: 960px) {
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


@st.cache_data(show_spinner=False)
def list_images(image_dir: str) -> list[dict]:
    root = Path(image_dir)
    if not root.exists():
        return []
    items: list[dict] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            continue
        rel = path.relative_to(root).as_posix()
        items.append(
            {
                "image_id": rel,
                "path": str(path),
                "filename": path.name,
            }
        )
    return items


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
        f"db_{image_id}",
    ]
    keys.extend(f"emo_{g['key']}_{image_id}" for g in EMOTION_GROUPS)
    return keys


def clear_form_keys(image_id: str) -> None:
    for key in form_keys_for(image_id):
        st.session_state.pop(key, None)


def apply_theme() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session / identity
# ---------------------------------------------------------------------------
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
        if st.button("Go to results"):
            st.session_state.nav_page = "Results"
            st.rerun()
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
        for group in EMOTION_GROUPS:
            reset_score_key(f"emo_{group['key']}_{image_id}")

        # Keep filled values when required fields are missing (no clear_on_submit)
        with st.form(f"rate_form_{image_id}", clear_on_submit=False):
            st.markdown('<div class="section-label">1. Is this a metaphor?</div>', unsafe_allow_html=True)
            is_metaphor = st.radio(
                "Is this a metaphor?",
                options=YES_NO,
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
                '<div class="section-label">4. Dominant emotion</div>',
                unsafe_allow_html=True,
            )
            st.caption("1 Very weak → 5 Very strong")
            emotion_scores: dict[str, int] = {}
            for group in EMOTION_GROUPS:
                emotion_scores[group["key"]] = st.select_slider(
                    group["label"],
                    options=SCORE_OPTIONS,
                    value=1,
                    format_func=lambda x: INTENSITY_LABELS[x],
                    key=f"emo_{group['key']}_{image_id}",
                )

            st.markdown(
                '<div class="section-label">5. Explanation (optional)</div>',
                unsafe_allow_html=True,
            )
            explanation = st.text_area(
                "Explanation",
                placeholder=(
                    "Optional: which visual element most influenced "
                    "your judgment, and why"
                ),
                height=80,
                key=f"expl_{image_id}",
                label_visibility="collapsed",
            )

            st.markdown(
                '<div class="section-label">6. Suitable for the database?</div>',
                unsafe_allow_html=True,
            )
            suitable_for_db = st.radio(
                "Suitable for the database?",
                options=YES_NO,
                horizontal=True,
                index=None,
                key=f"db_{image_id}",
                label_visibility="collapsed",
            )

            submitted = st.form_submit_button(
                "Submit & next", type="primary", use_container_width=True
            )

        if submitted:
            missing = []
            if is_metaphor is None:
                missing.append("metaphor judgment")
            if suitable_for_db is None:
                missing.append("database suitability")
            if missing:
                st.warning("Please complete: " + ", ".join(missing) + ".")
            else:
                entry = {
                    "image_id": image_id,
                    "filename": img["filename"],
                    "is_metaphor": is_metaphor == "Yes",
                    "valence": int(valence),
                    "intensity": int(intensity),
                    "emotions": {k: int(v) for k, v in emotion_scores.items()},
                    "explanation": (explanation or "").strip(),
                    "suitable_for_database": suitable_for_db == "Yes",
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


def _yn(flag) -> str:
    if flag is True:
        return "Yes"
    if flag is False:
        return "No"
    return "—"


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

    st.markdown(f"**{len(all_images)}** images")

    for img in all_images:
        image_id = img["image_id"]
        filename = img["filename"]
        raters_for_img = [
            (u, all_by_user[u][image_id])
            for u in filter_user
            if image_id in all_by_user.get(u, {})
        ]
        n_rated = len([u for u in users if image_id in all_by_user.get(u, {})])

        with st.expander(f"{filename}  ·  {n_rated}/{len(users)} rated", expanded=False):
            c_img, c_meta = st.columns([1.1, 1.0], gap="large")
            with c_img:
                st.image(img["path"], use_container_width=True)
            with c_meta:
                if not raters_for_img:
                    st.info("No ratings yet for the selected raters.")
                    continue

                for user, r in raters_for_img:
                    st.markdown(f"##### {user}")
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Metaphor", _yn(r.get("is_metaphor")))
                    m2.metric("Valence", r.get("valence", "—"))
                    m3.metric("Intensity", r.get("intensity", "—"))
                    m4.metric("For DB", _yn(r.get("suitable_for_database")))
                    emos = r.get("emotions") or {}
                    for group in EMOTION_GROUPS:
                        val = emos.get(group["key"], "—")
                        st.write(f"- **{group['label']}:** {val}")
                    st.write(f"**Explanation:** {r.get('explanation', '—')}")
                    st.caption(f"Rated at: {r.get('rated_at', '—')}")
                    st.divider()


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

    if "nav_page" not in st.session_state:
        st.session_state.nav_page = "Rate"

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

        page = st.radio(
            "Page",
            options=["Rate", "Results"],
            index=0 if st.session_state.nav_page == "Rate" else 1,
        )
        st.session_state.nav_page = page

    if not IMAGE_DIR.exists():
        st.warning(f"Image directory not found: {IMAGE_DIR}")
        return

    all_images = list_images(str(IMAGE_DIR))
    if not all_images:
        st.warning("No images found.")
        return

    if st.session_state.nav_page == "Rate":
        render_rate_page(identity, all_images)
    else:
        render_results_page(all_images)


if __name__ == "__main__":
    main()
