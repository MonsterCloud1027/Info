"""Find images that appear in both datasets with perceptual hash (pHash).

pHash compares visual content, so the same picture still matches after
re-encoding, small resizes, or metadata changes. It does not match crops
or heavy edits.

Hamming distance on the 64-bit hash:
  0     visually the same at pHash resolution (treat as the same image)
  1-5   near-duplicate; worth a manual look
  ~32   unrelated images

A second hash (dHash) is reported so a pHash collision can be checked.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import imagehash
from PIL import Image

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def iter_images(root: Path) -> list[Path]:
    files = [
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]
    files.sort(key=lambda p: p.as_posix().lower())
    return files


def hash_to_int(value: imagehash.ImageHash) -> int:
    return int(str(value), 16)


def fingerprint(path: Path) -> tuple[int, int, str]:
    with Image.open(path) as im:
        rgb = im.convert("RGB")
        size = f"{rgb.width}x{rgb.height}"
        ph = hash_to_int(imagehash.phash(rgb))
        dh = hash_to_int(imagehash.dhash(rgb))
    return ph, dh, size


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def load_hashes(paths: list[Path], label: str) -> tuple[list[dict], list[tuple[str, str]]]:
    rows: list[dict] = []
    errors: list[tuple[str, str]] = []
    total = len(paths)
    for i, path in enumerate(paths, start=1):
        if i == 1 or i % 100 == 0 or i == total:
            print(f"[{label}] {i}/{total}", flush=True)
        try:
            ph, dh, size = fingerprint(path)
        except Exception as exc:  # noqa: BLE001 - keep going on bad files
            errors.append((str(path), str(exc)))
            continue
        rows.append(
            {
                "path": path,
                "phash": ph,
                "dhash": dh,
                "size": size,
            }
        )
    return rows, errors


def find_pairs(
    corpus: list[dict],
    metaphor: list[dict],
    max_distance: int,
) -> list[dict]:
    pairs: list[dict] = []
    for left in corpus:
        for right in metaphor:
            dist = hamming(left["phash"], right["phash"])
            if dist > max_distance:
                continue
            pairs.append(
                {
                    "corpus_path": str(left["path"]),
                    "metaphor_path": str(right["path"]),
                    "corpus_size": left["size"],
                    "metaphor_size": right["size"],
                    "phash_distance": dist,
                    "dhash_distance": hamming(left["dhash"], right["dhash"]),
                }
            )
    pairs.sort(key=lambda row: (row["phash_distance"], row["dhash_distance"], row["corpus_path"]))
    return pairs


def write_csv(path: Path, pairs: list[dict]) -> None:
    fieldnames = [
        "corpus_path",
        "metaphor_path",
        "corpus_size",
        "metaphor_size",
        "phash_distance",
        "dhash_distance",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(pairs)


def main() -> int:
    parser = argparse.ArgumentParser(description="用 pHash 找出两个图片数据集中的相同图片")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path(r"D:\CouldService\LLMvsHuman\corpus"),
    )
    parser.add_argument(
        "--metaphor",
        type=Path,
        default=Path(r"D:\CouldService\MetaphorDB\images"),
    )
    parser.add_argument(
        "--max-distance",
        type=int,
        default=5,
        help="保留 pHash 汉明距离不超过该值的图片对。0 表示只保留感知哈希完全相同的。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("same_images_phash.csv"),
    )
    args = parser.parse_args()

    if not args.corpus.is_dir():
        print(f"找不到目录: {args.corpus}", file=sys.stderr)
        return 1
    if not args.metaphor.is_dir():
        print(f"找不到目录: {args.metaphor}", file=sys.stderr)
        return 1
    if args.max_distance < 0:
        print("--max-distance 不能小于 0", file=sys.stderr)
        return 1

    corpus_files = iter_images(args.corpus)
    metaphor_files = iter_images(args.metaphor)
    print(f"corpus: {len(corpus_files)} 张  ({args.corpus})")
    print(f"metaphor: {len(metaphor_files)} 张  ({args.metaphor})")

    corpus_rows, corpus_errors = load_hashes(corpus_files, "corpus")
    metaphor_rows, metaphor_errors = load_hashes(metaphor_files, "metaphor")
    pairs = find_pairs(corpus_rows, metaphor_rows, args.max_distance)
    write_csv(args.output, pairs)

    exact = sum(1 for row in pairs if row["phash_distance"] == 0)
    print(f"写出 {len(pairs)} 对 -> {args.output}")
    print(f"其中 pHash 距离为 0 的有 {exact} 对")
    if corpus_errors or metaphor_errors:
        print(f"无法读取: corpus {len(corpus_errors)}，metaphor {len(metaphor_errors)}")
        for path, message in (corpus_errors + metaphor_errors)[:20]:
            print(f"  {path}: {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
