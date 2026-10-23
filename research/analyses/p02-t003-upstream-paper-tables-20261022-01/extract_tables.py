#!/usr/bin/env python3
"""Extract and check the numbers in the cached Job-SDF paper.

Purpose: give future research reports one citable, reproducible summary of the
upstream paper's tables instead of re-reading the PDF each time.  The script
uses only the standard library: it decompresses the PDF content streams, pulls
literal text strings, segments the document by table captions and parses the
numeric cells.

Checks written to ``tables.json``:

* Table 1 (main benchmark): per-model values and column-ratio checks.
* Tables 6-12 (appendix): mean/std cells for benchmark and GNN runs, plus the
  std/mean ratio distribution per table.
* Cross-table comparisons used in ``report.md`` (GNN vs LSTM overall and on
  low-frequency skills).

The PDF is `references/literature/Job-SDF-NeurIPS2024.pdf`; it is ignored in
Git, so the PDF SHA256 is recorded in the output and the report states this
dependency.  Unit conversion: the extracted decimal point is a colon, so
``741 : 45`` means ``741.45``; a cell is ``mean ± std``.

    python3 -B research/analyses/p02-t003-upstream-paper-tables-20261022-01/extract_tables.py
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PDF = ROOT / "references/literature/Job-SDF-NeurIPS2024.pdf"
OUT = Path(__file__).resolve().parent / "tables.json"

COLUMNS = ["Market", "Region", "L1-O", "L2-O", "R&L1-O", "R&L2-O", "Company"]
METRICS = ["MAE", "RMSE", "SMAPE", "RRMSE"]

BENCHMARK_MODELS = [
    "LSTM",
    "Se gRNN",
    "CHGH",
    "Pre-DyGAE",
    "T ransformer",
    "Autoformer",
    "Informer",
    "Reformer",
    "FEDformer",
    "NStransformer",
    "P atchTST",
    "DLinear",
    "TSMix er",
    "FreTS",
    "FiLM",
    "K oopa",
]

GNN_MODELS = [
    "Ev olv eGCNH",
    "Ev olv eGCNO",
    "GCon vGR U",
    "TGCN",
    "GCLSTM",
    "GCon vLSTM",
    "DyGrEncoder",
]

TABLE1_MODELS = ["ARIMA", "Prophet"] + BENCHMARK_MODELS

# Cell form in the appendix tables: "mean ± std" where each number is printed
# as "integer : two-digits" (the colon stands in for the decimal point).  The
# plus-minus glyph arrives as byte 0x06 (or U+00B1) depending on the font; both
# are normalised to "±" right after extraction.
CELL = re.compile(r"(\d+)\s*:\s*(\d+)\s*±\s*(\d+)\s*:\s*(\d+)")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unescape_pdf_string(raw: bytes) -> bytes:
    """Resolve PDF literal-string escapes, including octal codes."""
    out = bytearray()
    index = 0
    while index < len(raw):
        byte = raw[index]
        if byte != 0x5C or index + 1 >= len(raw):
            out.append(byte)
            index += 1
            continue
        nxt = raw[index + 1]
        if nxt in b"()\\":
            out.append(nxt)
            index += 2
        elif 0x30 <= nxt <= 0x37:
            digits = bytearray()
            cursor = index + 1
            while cursor < len(raw) and len(digits) < 3 and 0x30 <= raw[cursor] <= 0x37:
                digits.append(raw[cursor])
                cursor += 1
            out.append(int(digits.decode("ascii"), 8) & 0xFF)
            index = cursor
        elif nxt in b"nrtbf":
            out.append({0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}[nxt])
            index += 2
        elif nxt in b"\r\n":
            index += 2
            while index < len(raw) and raw[index] in b"\r\n":
                index += 1
        else:
            out.append(nxt)
            index += 2
    return bytes(out)


def text_streams(data: bytes) -> list[str]:
    chunks: list[str] = []
    for match in re.finditer(rb"stream\r?\n", data):
        end = data.find(b"endstream", match.end())
        if end < 0:
            continue
        try:
            decoded = zlib.decompress(data[match.end() : end])
        except Exception:
            continue
        if b"BT" not in decoded:
            continue
        parts: list[str] = []
        for string in re.finditer(rb"\((?:\\.|[^\\()])*\)", decoded):
            raw = string.group(0)[1:-1]
            parts.append(unescape_pdf_string(raw).decode("latin-1"))
        if parts:
            chunks.append(" ".join(parts))
    return chunks


def decimal(whole: str, fraction: str) -> float:
    return float(f"{whole}.{fraction}")


def parse_text(text: str) -> dict:
    captions = [
        (int(match.group(1)), match.start())
        for match in re.finditer(r"T able (\d+):", text)
    ]
    order = sorted({number for number, _ in captions})
    segments: dict[int, str] = {}
    for index, (number, start) in enumerate(captions):
        end = captions[index + 1][1] if index + 1 < len(captions) else len(text)
        # Keep the last caption for duplicated table references: append, do not
        # overwrite, so the actual float (longer segment) is preserved.
        segments[number] = segments.get(number, "") + text[start:end]
    return {"order": order, "segments": segments}


def parse_table1(segment: str) -> dict:
    rows: dict[str, list[float]] = {}
    cursor = segment.find("ARIMA")
    if cursor < 0:
        cursor = 0
    for model in TABLE1_MODELS:
        index = segment.find(model, cursor)
        if index < 0:
            raise SystemExit(f"table 1: model not found: {model!r}")
        tail = segment[index + len(model) : index + len(model) + 260]
        numbers = [float(value) for value in re.findall(r"\d+\.\d+", tail)]
        if len(numbers) < 10:
            raise SystemExit(f"table 1: {model!r} has {len(numbers)} numbers")
        rows[model] = numbers[:10]
        cursor = index + len(model)
    columns = [
        "L1-O MAE",
        "L1-O RMSE",
        "L2-O MAE",
        "L2-O RMSE",
        "R&L1-O MAE",
        "R&L1-O RMSE",
        "R&L2-O MAE",
        "R&L2-O RMSE",
        "Company MAE",
        "Company RMSE",
    ]
    ratio_checks = []
    for left in range(len(columns)):
        for right in range(left + 1, len(columns)):
            ratios = [
                values[left] / values[right]
                for values in rows.values()
                if values[right]
            ]
            mean = statistics.mean(ratios)
            spread = statistics.pstdev(ratios)
            ratio_checks.append(
                {
                    "numerator": columns[left],
                    "denominator": columns[right],
                    "mean": mean,
                    "pstdev": spread,
                    "cv": spread / mean if mean else None,
                    "min": min(ratios),
                    "max": max(ratios),
                }
            )
    ratio_checks.sort(key=lambda item: item["cv"] if item["cv"] is not None else 1e9)
    return {"columns": columns, "rows": rows, "ratio_checks": ratio_checks}


def parse_mean_std(segment: str, models: list[str]) -> dict:
    cells = CELL.findall(segment)
    expected = len(METRICS) * len(models) * len(COLUMNS)
    if len(cells) != expected:
        raise SystemExit(
            f"mean/std table: parsed {len(cells)} cells, expected {expected}"
        )
    values: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
    index = 0
    for metric in METRICS:
        metric_values: dict[str, dict[str, dict[str, float]]] = {}
        for model in models:
            row: dict[str, dict[str, float]] = {}
            for column in COLUMNS:
                mean = decimal(cells[index][0], cells[index][1])
                std = decimal(cells[index][2], cells[index][3])
                row[column] = {"mean": mean, "std": std}
                index += 1
            metric_values[model] = row
        values[metric] = metric_values
    return {"models": models, "columns": COLUMNS, "metrics": METRICS, "values": values}


def ratio_summary(table: dict) -> dict:
    ratios = []
    zeros = 0
    for metric_values in table["values"].values():
        for row in metric_values.values():
            for cell in row.values():
                if cell["mean"] == 0:
                    zeros += 1
                    continue
                ratios.append(cell["std"] / cell["mean"])
    return {
        "cells": len(ratios),
        "zero_mean_cells": zeros,
        "ratio_mean": statistics.mean(ratios),
        "ratio_pstdev": statistics.pstdev(ratios),
        "ratio_min": min(ratios),
        "ratio_max": max(ratios),
        "share_within_0_02_of_constant": sum(
            1 for value in ratios if abs(value - statistics.mean(ratios)) <= 0.02
        )
        / len(ratios),
    }


def main() -> int:
    if not PDF.is_file():
        raise SystemExit(f"missing PDF: {PDF}")
    data = PDF.read_bytes()
    chunks = text_streams(data)
    joined = " ".join(chunks)
    # Normalise the plus-minus glyph before collapsing whitespace.
    joined = joined.replace("\x06", " ± ").replace("\u00b1", " ± ")
    text = re.sub(r"\s+", " ", joined)
    parsed = parse_text(text)

    tables: dict[str, dict] = {}
    tables["1"] = parse_table1(parsed["segments"][1])
    std_tables: dict[str, dict] = {}
    for number in (6, 7, 8):
        tables[str(number)] = parse_mean_std(parsed["segments"][number], BENCHMARK_MODELS)
        std_tables[str(number)] = ratio_summary(tables[str(number)])
    for number in (9, 10, 11):
        tables[str(number)] = parse_mean_std(parsed["segments"][number], GNN_MODELS)
        std_tables[str(number)] = ratio_summary(tables[str(number)])
    tables["12"] = parse_mean_std(parsed["segments"][12], BENCHMARK_MODELS)
    std_tables["12"] = ratio_summary(tables["12"])

    def comparison(low_gnn: str, low_bench: str) -> dict:
        gnn = tables[low_gnn]["values"]["MAE"]["GCon vLSTM"]
        bench = tables[low_bench]["values"]["MAE"]["LSTM"]
        return {
            "gnn_table": low_gnn,
            "benchmark_table": low_bench,
            "row": {
                column: {
                    "GConvLSTM": gnn[column]["mean"],
                    "LSTM": bench[column]["mean"],
                    "GConvLSTM_over_LSTM": gnn[column]["mean"]
                    / bench[column]["mean"],
                }
                for column in COLUMNS
            },
        }

    overall = tables["9"]["values"]["MAE"]["GCon vLSTM"]
    overall_lstm = tables["6"]["values"]["MAE"]["LSTM"]
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "script": "extract_tables.py",
        "script_sha256": sha256_file(Path(__file__)),
        "pdf": {
            "path": str(PDF.relative_to(ROOT)),
            "sha256": sha256_file(PDF),
            "bytes": len(data),
            "ignored_in_git": True,
        },
        "extracted": {
            "streams": len(chunks),
            "characters": len(text),
            "tables_found": parsed["order"],
        },
        "tables": tables,
        "std_over_mean": std_tables,
        "comparisons": {
            "overall_GConvLSTM_vs_LSTM": {
                column: {
                    "GConvLSTM": overall[column]["mean"],
                    "LSTM": overall_lstm[column]["mean"],
                    "GConvLSTM_over_LSTM": overall[column]["mean"]
                    / overall_lstm[column]["mean"],
                }
                for column in COLUMNS
            },
            "low_frequency_GConvLSTM_vs_LSTM": comparison("11", "8"),
        },
        "notes": {
            "decimal_marker": "colon in extracted text; 741 : 45 means 741.45",
            "cell_format": "appendix tables print mean <pm> std per cell",
            "limitation": (
                "numbers come from PDF text-stream extraction of the local ignored "
                "PDF; verify against the published version before external citation"
            ),
        },
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print("tables:", payload["extracted"]["tables_found"])
    for table, summary in std_tables.items():
        print(
            f"table {table}: cells={summary['cells']} "
            f"std/mean={summary['ratio_mean']:.4f} "
            f"pstdev={summary['ratio_pstdev']:.5f} "
            f"range={summary['ratio_min']:.4f}-{summary['ratio_max']:.4f}"
        )
    print(
        "GConvLSTM/LSTM MAE overall:",
        {
            column: round(values["GConvLSTM_over_LSTM"], 3)
            for column, values in payload["comparisons"]["overall_GConvLSTM_vs_LSTM"].items()
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
