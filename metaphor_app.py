"""Metaphor image browser — filter by target, source, and strategy."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------------
# Paths
# Repo-relative first so Streamlit Cloud can read the JSON. Local Windows
# folders are fallbacks for this machine.
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent


def _first_existing(candidates: list[Path]) -> Path:
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


DATA_PATH = _first_existing(
    [
        BASE_DIR / "Metaphor_data.json",
        Path(r"d:\CouldService\Info Data\Metaphor_data.json"),
    ]
)
IMAGE_DIR = _first_existing(
    [
        BASE_DIR / "images",
        Path(r"D:\CouldService\MetaphorDB\images"),
    ]
)

PAGE_SIZE_OPTIONS = [12, 24, 36, 48]
THUMB_SIZE = 280


def _fit_cover_square(im: Image.Image, size: int) -> Image.Image:
    """Scale to cover a square, then center-crop to exact size×size."""
    w, h = im.size
    scale = max(size / w, size / h)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - size) // 2
    top = (nh - size) // 2
    return im.crop((left, top, left + size, top + size))


def _fit_contain(im: Image.Image, max_side: int) -> Image.Image:
    im = im.copy()
    im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return im


def _file_num(name: str) -> int:
    stem = Path(name).stem
    return int(stem) if stem.isdigit() else 0


def _annotation_rows(annotations: list) -> list[dict]:
    rows = []
    for ann in annotations or []:
        if not isinstance(ann, dict):
            continue
        rows.append(
            {
                "targets": [str(x) for x in (ann.get("targets") or [])],
                "sources": [str(x) for x in (ann.get("sources") or [])],
                "strategy": str(ann.get("strategy") or ""),
            }
        )
    return rows


def _annotation_matches(
    ann: dict,
    targets: set[str],
    sources: set[str],
    strategies: set[str],
) -> bool:
    if targets and not targets.intersection(ann["targets"]):
        return False
    if sources and not sources.intersection(ann["sources"]):
        return False
    if strategies and ann["strategy"] not in strategies:
        return False
    return True


# ---------------------------------------------------------------------------
# Data loading / thumbnails (cached)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading metaphor data…")
def load_metaphor_data(path_str: str) -> tuple[pd.DataFrame, dict]:
    with open(path_str, encoding="utf-8") as f:
        raw = json.load(f)

    rows = []
    for filename, item in raw.items():
        info = item.get("info") or {}
        anns = _annotation_rows(item.get("annotations") or [])
        rows.append(
            {
                "filename": filename,
                "title": info.get("title") or "",
                "source_type": info.get("source_type") or "",
                "source": info.get("source") or "",
                "description": info.get("description") or "",
                "n_annotations": len(anns),
                "targets": sorted({t for a in anns for t in a["targets"]}),
                "sources": sorted({s for a in anns for s in a["sources"]}),
                "strategies": sorted({a["strategy"] for a in anns if a["strategy"]}),
                "annotations": anns,
            }
        )

    df = pd.DataFrame(rows)
    df["_num"] = df["filename"].map(_file_num)
    df = df.sort_values("_num").drop(columns="_num").reset_index(drop=True)
    return df, raw


@st.cache_data(show_spinner=False)
def get_thumbnail_bytes(
    image_dir: str, filename: str, size: int = THUMB_SIZE, mode: str = "cover"
) -> bytes | None:
    path = Path(image_dir) / filename
    if not path.exists():
        return None

    with Image.open(path) as im:
        im = im.convert("RGB")
        if mode == "cover":
            im = _fit_cover_square(im, size)
        else:
            im = _fit_contain(im, size)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=78, optimize=True)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------
def apply_filters(
    df: pd.DataFrame,
    name_query: str,
    targets: list[str],
    sources: list[str],
    strategies: list[str],
    same_annotation: bool,
) -> pd.DataFrame:
    out = df
    q = name_query.strip().lower()
    if q:
        out = out[
            out["filename"].str.lower().str.contains(q, regex=False)
            | out["title"].str.lower().str.contains(q, regex=False)
        ]

    target_set = set(targets)
    source_set = set(sources)
    strategy_set = set(strategies)
    if not (target_set or source_set or strategy_set):
        return out.reset_index(drop=True)

    def row_ok(row) -> bool:
        anns = row.annotations
        if same_annotation:
            return any(
                _annotation_matches(a, target_set, source_set, strategy_set)
                for a in anns
            )
        if target_set and not target_set.intersection(row.targets):
            return False
        if source_set and not source_set.intersection(row.sources):
            return False
        if strategy_set and not strategy_set.intersection(row.strategies):
            return False
        return True

    mask = out.apply(row_ok, axis=1)
    return out[mask].reset_index(drop=True)


def apply_sort(df: pd.DataFrame, sort_by: str, ascending: bool) -> pd.DataFrame:
    if df.empty:
        return df
    if sort_by == "filename":
        out = df.copy()
        out["_num"] = out["filename"].map(_file_num)
        out = out.sort_values("_num", ascending=ascending).drop(columns="_num")
        return out.reset_index(drop=True)
    if sort_by not in df.columns:
        return df
    return df.sort_values(sort_by, ascending=ascending, na_position="last").reset_index(
        drop=True
    )


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------
def init_state():
    if "selected_file" not in st.session_state:
        st.session_state.selected_file = None
    if "page" not in st.session_state:
        st.session_state.page = 0


def select_file(filename: str):
    st.session_state.selected_file = filename


def _join(values: list[str]) -> str:
    return ", ".join(values) if values else "—"


def render_detail(filename: str, raw: dict, image_dir: str):
    item = raw[filename]
    info = item.get("info") or {}
    st.subheader(filename)
    if info.get("title"):
        st.markdown(f"**{info['title']}**")

    img_path = Path(image_dir) / filename
    if img_path.exists():
        st.image(str(img_path), use_container_width=True)
    else:
        st.warning(f"Image file not found: {filename}")

    c1, c2 = st.columns(2)
    c1.metric("Source type", info.get("source_type") or "—")
    c2.metric("Annotations", len(item.get("annotations") or []))

    if info.get("source"):
        st.caption(info["source"])
    if info.get("description"):
        st.markdown(info["description"])

    anns = _annotation_rows(item.get("annotations") or [])
    st.markdown("##### Annotations")
    if not anns:
        st.info("No annotations")
        return

    table = pd.DataFrame(
        [
            {
                "targets": _join(a["targets"]),
                "sources": _join(a["sources"]),
                "strategy": a["strategy"] or "—",
            }
            for a in anns
        ]
    )
    st.dataframe(table, use_container_width=True, hide_index=True)


def render_gallery(page_df: pd.DataFrame, image_dir: str, cols_n: int = 4):
    if page_df.empty:
        st.info("No images match the current filters.")
        return

    rows = list(page_df.itertuples(index=False))
    for i in range(0, len(rows), cols_n):
        cols = st.columns(cols_n)
        for j, col in enumerate(cols):
            if i + j >= len(rows):
                break
            row = rows[i + j]
            filename = row.filename
            with col:
                thumb = get_thumbnail_bytes(image_dir, filename, size=THUMB_SIZE)
                if thumb:
                    st.image(thumb, use_container_width=True)
                else:
                    st.caption("(missing)")

                st.caption(
                    f"**{filename}** · {row.n_annotations} ann.\n\n"
                    f"T: {_join(list(row.targets))}\n\n"
                    f"S: {_join(list(row.sources))} · {_join(list(row.strategies))}"
                )
                st.button(
                    "View details",
                    key=f"btn_{filename}",
                    on_click=select_file,
                    args=(filename,),
                    use_container_width=True,
                )


def _unique_sorted(series: pd.Series) -> list[str]:
    values: set[str] = set()
    for items in series:
        values.update(items or [])
    return sorted(values)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Metaphor Image Browser",
        page_icon="🖼️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()

    st.title("Metaphor Image Browser")
    st.caption("Filter MetaphorDB images by target, source, and strategy")

    if not DATA_PATH.exists():
        st.error(f"Data file not found: {DATA_PATH}")
        return
    if not IMAGE_DIR.exists():
        st.warning(
            f"Image directory not found: {IMAGE_DIR}. "
            "Annotations from the JSON file are still shown."
        )

    df, raw = load_metaphor_data(str(DATA_PATH))
    image_dir = str(IMAGE_DIR)
    all_targets = _unique_sorted(df["targets"])
    all_sources = _unique_sorted(df["sources"])
    all_strategies = _unique_sorted(df["strategies"])

    with st.sidebar:
        st.header("Filters")
        name_query = st.text_input(
            "Name or title",
            placeholder="e.g. 12 or Iraq",
        )
        targets = st.multiselect(
            "Target",
            options=all_targets,
            default=[],
            help="Leave empty to include all",
        )
        sources = st.multiselect(
            "Source",
            options=all_sources,
            default=[],
            help="Leave empty to include all",
        )
        strategies = st.multiselect(
            "Strategy",
            options=all_strategies,
            default=[],
            help="Leave empty to include all",
        )
        same_annotation = st.checkbox(
            "Match within the same annotation",
            value=True,
            help="When on, one annotation must contain the chosen target, source, and strategy together.",
        )

        st.markdown("---")
        st.subheader("Sort")
        sort_options = {
            "filename": "filename",
            "annotation count": "n_annotations",
            "title": "title",
        }
        sort_label = st.selectbox("Sort by", options=list(sort_options.keys()), index=0)
        sort_by = sort_options[sort_label]
        sort_ascending = st.radio(
            "Order",
            options=["Ascending", "Descending"],
            index=0,
            horizontal=True,
        )
        ascending = sort_ascending == "Ascending"

        st.markdown("---")
        page_size = st.selectbox("Images per page", PAGE_SIZE_OPTIONS, index=1)
        cols_n = st.selectbox("Images per row", [3, 4, 5, 6], index=1)

        if st.button("Clear selection", use_container_width=True):
            st.session_state.selected_file = None

    filtered = apply_filters(
        df, name_query, targets, sources, strategies, same_annotation
    )
    filtered = apply_sort(filtered, sort_by, ascending)

    filter_sig = (
        name_query,
        tuple(targets),
        tuple(sources),
        tuple(strategies),
        same_annotation,
        sort_by,
        ascending,
        len(filtered),
    )
    if st.session_state.get("_filter_sig") != filter_sig:
        st.session_state._filter_sig = filter_sig
        st.session_state.page = 0

    n = len(filtered)
    n_pages = max(1, (n + page_size - 1) // page_size)
    page = min(st.session_state.page, n_pages - 1)
    st.session_state.page = page

    left, right = st.columns([1.55, 1.0], gap="large")

    with left:
        st.markdown(f"**{n} / {len(df)} matches** · Page {page + 1}/{n_pages}")

        nav1, nav2, nav3 = st.columns([1, 2, 1])
        with nav1:
            if st.button("← Prev", disabled=page <= 0, use_container_width=True):
                st.session_state.page = max(0, page - 1)
                st.rerun()
        with nav2:
            new_page = st.number_input(
                "Page",
                min_value=1,
                max_value=n_pages,
                value=page + 1,
                step=1,
                label_visibility="collapsed",
            )
            if new_page - 1 != page:
                st.session_state.page = int(new_page) - 1
                st.rerun()
        with nav3:
            if st.button(
                "Next →", disabled=page >= n_pages - 1, use_container_width=True
            ):
                st.session_state.page = min(n_pages - 1, page + 1)
                st.rerun()

        start = page * page_size
        page_df = filtered.iloc[start : start + page_size]
        render_gallery(page_df, image_dir, cols_n=cols_n)

        page_ids = page_df["filename"].tolist()
        if page_ids:
            jump = st.selectbox(
                "Quick select (this page)",
                options=["(none)"] + page_ids,
                index=0,
            )
            if jump != "(none)":
                st.session_state.selected_file = jump

    with right:
        st.markdown("### Details")
        selected = st.session_state.selected_file
        if selected and selected in set(df["filename"]):
            render_detail(selected, raw, image_dir)
        else:
            st.info(
                'Click "View details" under an image, or use Quick select on this page.'
            )


if __name__ == "__main__":
    main()
