import argparse
import gzip
import json
from pathlib import Path

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore


def parse(path: str | Path):
    path = Path(path)
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as g:
            for line in g:
                yield json.loads(line)
    else:
        with path.open("rb") as f:
            for line in f:
                yield json.loads(line)


def getDF(path: str | Path):
    if pd is None:
        raise RuntimeError(
            "pandas is not installed. Re-run with --format jsonl, or install pandas first."
        )
    i = 0
    df = {}
    for d in parse(path):
        df[i] = d
        i += 1
    return pd.DataFrame.from_dict(df, orient="index")


def write_jsonl(in_path: str | Path, out_path: str | Path) -> int:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for d in parse(in_path):
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
            n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract Amazon Digital Music reviews (.json.gz JSONL) into CSV (pandas) or JSONL."
    )
    parser.add_argument(
        "--in",
        dest="in_path",
        default=str(Path(__file__).resolve().parent.parent / "Digital_Music_5.json.gz"),
        help="Input path to Digital Music reviews file (.json.gz or .json).",
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        default=str(Path(__file__).resolve().parent / "digital_music_reviews.csv"),
        help="Output file path (CSV or JSONL).",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "jsonl"],
        default="csv",
        help="Output format. csv requires pandas; jsonl uses stdlib only.",
    )
    args = parser.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)

    if args.format == "jsonl":
        n = write_jsonl(in_path, out_path)
        print(f"Saved {n} rows to {out_path}")
        return 0

    if pd is None:
        raise SystemExit(
            "pandas is not installed, cannot write CSV. Install pandas or use --format jsonl."
        )

    df = getDF(in_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"Saved {len(df)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
