import csv
import gzip
import json
import math
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple


csv.field_size_limit(10_000_000)


def pct(n: int, d: int) -> str:
    if d <= 0:
        return "NA"
    return f"{(n / d) * 100:.2f}%"


def safe_int(x: str) -> Optional[int]:
    x = (x or "").strip()
    if not x or x == "NA":
        return None
    try:
        return int(x)
    except Exception:
        return None


def unix_to_utc_str(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def quantiles_from_counts(values: List[int], qs: List[float]) -> Dict[float, int]:
    if not values:
        return {q: 0 for q in qs}
    values_sorted = sorted(values)
    out: Dict[float, int] = {}
    n = len(values_sorted)
    for q in qs:
        if q <= 0:
            out[q] = values_sorted[0]
            continue
        if q >= 1:
            out[q] = values_sorted[-1]
            continue
        idx = math.ceil(q * n) - 1
        idx = max(0, min(idx, n - 1))
        out[q] = values_sorted[idx]
    return out


def top_share(counter: Counter, total: int, k: int) -> List[Tuple[str, int, str]]:
    rows = []
    for key, count in counter.most_common(k):
        rows.append((str(key), int(count), pct(int(count), total)))
    return rows


def md_table(headers: List[str], rows: List[List[str]]) -> str:
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def iter_jsonl(path: Path) -> Iterator[dict]:
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as g:
            for line in g:
                if not line.strip():
                    continue
                yield json.loads(line)
    else:
        with path.open("rb") as f:
            for line in f:
                if not line.strip():
                    continue
                yield json.loads(line)


@dataclass
class SOYearConfig:
    year: str
    base_dir: Path

    @property
    def public_csv(self) -> Path:
        return self.base_dir / f"stack-overflow-developer-survey-{self.year}" / "survey_results_public.csv"

    @property
    def schema_csv(self) -> Path:
        return self.base_dir / f"stack-overflow-developer-survey-{self.year}" / "survey_results_schema.csv"


def load_schema_questions(schema_path: Path, qnames: List[str]) -> Dict[str, str]:
    if not schema_path.exists():
        return {}
    with schema_path.open("r", encoding="utf-8", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample)
        reader = csv.DictReader(f, dialect=dialect)
        q = {}
        for row in reader:
            qname = (row.get("qname") or row.get("QNAME") or "").strip().strip('"')
            if qname in qnames:
                question = (row.get("question") or row.get("QUESTION") or "").replace("\r", " ").replace("\n", " ").strip().strip('"')
                q[qname] = question
        return q


def so_describe_year(cfg: SOYearConfig) -> str:
    path = cfg.public_csv
    schema_qnames = [
        "AISelect",
        "AISent",
        "AIBen",
        "AIAcc",
        "AIThreat",
        "JobSat",
        "AIComplex",
        "AISearch",
        "AIDev",
        "AISearchDev",
        "AITool",
    ]
    schema_questions = load_schema_questions(cfg.schema_csv, schema_qnames)

    if not path.exists():
        return f"## {cfg.year}\n\nMissing file: `{path}`\n"

    # Counters for key variables
    key_cols = [
        "AISelect",
        "AISent",
        "AIBen",
        "AIAcc",
        "AIThreat",
        "JobSat",
        "AIComplex",
        "AIToolCurrently Using",
        "AIToolInterested in Using",
        "AISearchHaveWorkedWith",
        "AIDevHaveWorkedWith",
        "AISearchDevHaveWorkedWith",
        "AIToolCurrently mostly AI",
        "AIToolCurrently partially AI",
        "SOFriction",
        "AIAgents",
    ]

    row_count = 0
    col_count = 0
    na_counts = Counter()
    value_counts: Dict[str, Counter] = {c: Counter() for c in key_cols}
    tool_item_counts = Counter()
    tool_answered = 0
    tool_num_selected: List[int] = []

    # 2025 has split columns for AITool
    tool_cols_2025 = ["AIToolCurrently mostly AI", "AIToolCurrently partially AI"]

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        col_count = len(reader.fieldnames or [])

        # Only keep columns that exist for NA counting
        present_key_cols = [c for c in key_cols if c in (reader.fieldnames or [])]
        for row in reader:
            row_count += 1
            for c in present_key_cols:
                v = (row.get(c) or "").strip()
                if not v or v == "NA":
                    na_counts[c] += 1
                else:
                    value_counts[c][v] += 1

            # AITool summary
            if "AIToolCurrently Using" in (reader.fieldnames or []):
                raw = (row.get("AIToolCurrently Using") or "").strip()
                if raw and raw != "NA":
                    tool_answered += 1
                    items = [t.strip() for t in raw.split(";") if t.strip()]
                    tool_num_selected.append(len(items))
                    tool_item_counts.update(items)
            elif all(c in (reader.fieldnames or []) for c in tool_cols_2025):
                mostly = (row.get(tool_cols_2025[0]) or "").strip()
                partially = (row.get(tool_cols_2025[1]) or "").strip()
                items = []
                if mostly and mostly != "NA":
                    items.extend([t.strip() for t in mostly.split(";") if t.strip()])
                if partially and partially != "NA":
                    items.extend([t.strip() for t in partially.split(";") if t.strip()])
                if items:
                    tool_answered += 1
                    tool_num_selected.append(len(set(items)))
                    tool_item_counts.update(items)

    # Basic summary table
    summary_rows = [
        ["Rows (respondents)", str(row_count)],
        ["Columns", str(col_count)],
    ]
    # NA rates for a subset
    na_focus = [c for c in ["AISelect", "AISent", "AIBen", "AIAcc", "AIThreat", "JobSat", "AIToolCurrently Using"] if c in na_counts or c in value_counts]
    na_table_rows = []
    for c in na_focus:
        na = int(na_counts.get(c, 0))
        na_table_rows.append([c, str(na), pct(na, row_count)])

    md = []
    md.append(f"## {cfg.year}")
    md.append("")
    md.append("**Dataset**")
    md.append(f"- `{path}`")
    md.append("")
    md.append("**Basic Stats**")
    md.append(md_table(["Metric", "Value"], summary_rows))
    md.append("")

    if na_table_rows:
        md.append("**Missing/NA (key columns)**")
        md.append(md_table(["Column", "NA Count", "NA Rate"], na_table_rows))
        md.append("")

    def dist_section(col: str, title: str, top_n: int = 10):
        if col not in value_counts or not value_counts[col]:
            return
        total_answered = sum(value_counts[col].values())
        rows = []
        for v, k in value_counts[col].most_common(top_n):
            rows.append([v, str(k), pct(k, total_answered)])
        md.append(f"**{title}**")
        md.append(md_table(["Value", "Count", "Share (answered)"], rows))
        md.append("")

    dist_section("AISelect", "AISelect（AI 工具使用/频率）")
    dist_section("AISent", "AISent（对 AI 工具态度）")

    if cfg.year == "2023":
        dist_section("AIBen", "AIBen（信任 AI 输出准确性，2023 列名）")
    else:
        dist_section("AIAcc", "AIAcc（信任 AI 输出准确性）")

    if cfg.year in ("2024", "2025"):
        dist_section("AIThreat", "AIThreat（AI 是否威胁工作）")
        dist_section("AIComplex", "AIComplex（AI 处理复杂任务能力）")
        dist_section("JobSat", "JobSat（工作满意度 0–10）")

    if tool_answered:
        qs = quantiles_from_counts(tool_num_selected, [0.5, 0.9, 0.99, 1.0])
        md.append("**AITool（当前使用场景）概览**")
        md.append(
            md_table(
                ["Metric", "Value"],
                [
                    ["Answered (non-NA)", str(tool_answered)],
                    ["Median #scenarios", str(qs[0.5])],
                    ["P90 #scenarios", str(qs[0.9])],
                    ["P99 #scenarios", str(qs[0.99])],
                    ["Max #scenarios", str(qs[1.0])],
                ],
            )
        )
        md.append("")
        top_items = []
        for item, count in tool_item_counts.most_common(12):
            top_items.append([item, str(count), pct(count, tool_answered)])
        md.append("**AITool Top 场景（按回答者覆盖率）**")
        md.append(md_table(["Scenario", "Count", "Coverage"], top_items))
        md.append("")

    # Add question wording (from schema) for a few anchor qnames
    anchor_qnames = ["AISelect", "AISent", "AITool", "AIThreat", "JobSat"]
    q_rows = []
    for qn in anchor_qnames:
        if qn in schema_questions:
            q_rows.append([qn, schema_questions[qn]])
    if q_rows:
        md.append("**Question Wording (from schema.csv)**")
        md.append(md_table(["qname", "question"], q_rows))
        md.append("")

    return "\n".join(md).rstrip() + "\n"


def digital_music_describe(base_dir: Path) -> str:
    candidates = [
        base_dir / "final project" / "digital_music_reviews.jsonl",
        base_dir / "Digital_Music_5.json.gz",
        base_dir / "Digital_Music_5.json" / "Digital_Music_5.json",
    ]
    in_path = next((p for p in candidates if p.exists()), None)
    if in_path is None:
        return "## Digital Music (Amazon Reviews)\n\nMissing input file (expected one of digital_music_reviews.jsonl / Digital_Music_5.json.gz / Digital_Music_5.json).\n"

    n = 0
    ratings = Counter()
    verified = Counter()
    votes: List[int] = []
    vote_missing = 0
    users = Counter()
    items = Counter()
    min_ts: Optional[int] = None
    max_ts: Optional[int] = None
    by_year = Counter()

    for r in iter_jsonl(in_path):
        n += 1
        asin = str(r.get("asin") or "")
        rid = str(r.get("reviewerID") or "")
        if asin:
            items[asin] += 1
        if rid:
            users[rid] += 1

        ov = r.get("overall")
        if ov is not None and ov != "NA":
            try:
                ratings[str(float(ov))] += 1
            except Exception:
                ratings[str(ov)] += 1

        v = r.get("verified")
        if v is True:
            verified["true"] += 1
        elif v is False:
            verified["false"] += 1

        vt = safe_int(str(r.get("vote") or ""))
        if vt is None:
            vote_missing += 1
        else:
            votes.append(vt)

        ts = r.get("unixReviewTime")
        if ts is not None:
            try:
                ts_i = int(ts)
                min_ts = ts_i if min_ts is None else min(min_ts, ts_i)
                max_ts = ts_i if max_ts is None else max(max_ts, ts_i)
                y = datetime.fromtimestamp(ts_i, tz=timezone.utc).year
                by_year[str(y)] += 1
            except Exception:
                pass

    md = []
    md.append("## Digital Music (Amazon Reviews)")
    md.append("")
    md.append("**Dataset**")
    md.append(f"- `{in_path}`")
    md.append("")
    md.append("**Basic Stats**")
    md.append(
        md_table(
            ["Metric", "Value"],
            [
                ["Rows (reviews)", str(n)],
                ["Unique users (reviewerID)", str(len(users))],
                ["Unique items (asin)", str(len(items))],
            ],
        )
    )
    md.append("")

    if ratings:
        rows = []
        for k, c in sorted(ratings.items(), key=lambda x: float(x[0]) if x[0].replace(".", "", 1).isdigit() else x[0]):
            rows.append([k, str(c), pct(c, n)])
        md.append("**Rating Distribution (`overall`)**")
        md.append(md_table(["Rating", "Count", "Share"], rows))
        md.append("")

    if verified:
        t = verified.get("true", 0)
        f = verified.get("false", 0)
        denom = t + f
        md.append("**Verified Purchase (`verified`)**")
        md.append(
            md_table(
                ["Value", "Count", "Share (answered)"],
                [
                    ["true", str(t), pct(t, denom)],
                    ["false", str(f), pct(f, denom)],
                ],
            )
        )
        md.append("")

    if votes or vote_missing:
        rows = [
            ["Missing/NA", str(vote_missing), pct(vote_missing, n)],
            ["Non-missing", str(len(votes)), pct(len(votes), n)],
        ]
        md.append("**Helpful Votes (`vote`)**")
        md.append(md_table(["Metric", "Count", "Share"], rows))
        if votes:
            vs = sorted(votes)
            def q(p: float) -> int:
                idx = max(0, min(len(vs) - 1, math.ceil(p * len(vs)) - 1))
                return vs[idx]
            md.append("")
            md.append(
                md_table(
                    ["Stat", "Value"],
                    [
                        ["Min", str(vs[0])],
                        ["Median", str(q(0.5))],
                        ["P90", str(q(0.9))],
                        ["P99", str(q(0.99))],
                        ["Max", str(vs[-1])],
                    ],
                )
            )
        md.append("")

    if min_ts is not None and max_ts is not None:
        md.append("**Time Range (`unixReviewTime`, UTC)**")
        md.append(
            md_table(
                ["Metric", "Value"],
                [
                    ["Min date", unix_to_utc_str(min_ts)],
                    ["Max date", unix_to_utc_str(max_ts)],
                ],
            )
        )
        md.append("")

    if by_year:
        rows = []
        for y, c in sorted(by_year.items(), key=lambda x: x[0]):
            rows.append([y, str(c), pct(c, n)])
        md.append("**Reviews by Year (UTC)**")
        md.append(md_table(["Year", "Count", "Share"], rows))
        md.append("")

    # Long-tail overview
    item_counts = list(items.values())
    user_counts = list(users.values())
    qs = [0.5, 0.9, 0.99, 1.0]
    item_q = quantiles_from_counts(item_counts, qs)
    user_q = quantiles_from_counts(user_counts, qs)
    md.append("**Long-Tail Overview（长尾概览）**")
    md.append(
        md_table(
            ["Entity", "Unique", "Median", "P90", "P99", "Max"],
            [
                ["Items (asin)", str(len(items)), str(item_q[0.5]), str(item_q[0.9]), str(item_q[0.99]), str(item_q[1.0])],
                ["Users (reviewerID)", str(len(users)), str(user_q[0.5]), str(user_q[0.9]), str(user_q[0.99]), str(user_q[1.0])],
            ],
        )
    )
    md.append("")
    top_items = top_share(items, n, 15)
    md.append("**Top Items by Review Count**")
    md.append(md_table(["asin", "Reviews", "Share"], [[a, str(c), s] for a, c, s in top_items]))
    md.append("")
    top_users = top_share(users, n, 15)
    md.append("**Top Users by Review Count**")
    md.append(md_table(["reviewerID", "Reviews", "Share"], [[a, str(c), s] for a, c, s in top_users]))
    md.append("")

    return "\n".join(md).rstrip() + "\n"


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent
    out_path = Path(__file__).resolve().parent / "Descriptive_Stats.md"

    so_years = ["2023", "2024", "2025"]
    so_cfgs = [SOYearConfig(year=y, base_dir=base_dir) for y in so_years]

    md = []
    md.append("# Descriptive Statistics（描述性统计）")
    md.append("")
    md.append(f"- Generated at (local): `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    md.append(f"- Base dir: `{base_dir}`")
    md.append("")
    md.append("## Stack Overflow Developer Survey (2023/2024/2025)")
    md.append("")
    for cfg in so_cfgs:
        md.append(so_describe_year(cfg))
        md.append("")

    md.append(digital_music_describe(base_dir))

    out_path.write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote report to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

