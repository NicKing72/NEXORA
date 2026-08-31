"""Safe deterministic export renderers for frozen reports."""

from __future__ import annotations

import csv
import io
import json
from html import escape

from nexora_api.models.report import ReportRun


def render_json(run: ReportRun) -> str:
    payload = {
        "report_run_id": run.id,
        "report_type": run.report_type,
        "title": run.title,
        "status": run.status,
        "report_cutoff": run.report_cutoff.isoformat(),
        "created_at": run.created_at.isoformat(),
        "calculation_version": run.calculation_version,
        "is_demo": run.is_demo,
        "source_snapshot": run.source_snapshot,
        "report_payload": run.report_payload,
        "warnings": run.warnings,
        "limitations": run.limitations,
        "sections": [
            {
                "position": item.position,
                "section_type": item.section_type,
                "completeness": item.completeness,
                "payload": item.payload,
                "source_references": item.source_references,
            }
            for item in sorted(run.sections, key=lambda section: section.position)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _text(value: object) -> str:
    if value is None:
        return "No disponible"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def render_html(run: ReportRun) -> str:
    sections = []
    for item in sorted(run.sections, key=lambda section: section.position):
        title = escape(str(item.payload.get("title", item.section_type)))
        content = escape(json.dumps(item.payload, ensure_ascii=False, indent=2))
        sections.append(
            f"<section><small>{item.position:02d}</small><h2>{title}</h2>"
            f"<pre>{content}</pre></section>"
        )
    return "".join(
        [
            "<!doctype html><html lang='es'><head><meta charset='utf-8'>",
            f"<title>{escape(run.title)}</title>",
            "<style>body{font:15px system-ui;color:#17201d;max-width:1080px;margin:40px auto;"
            "padding:0 24px}header{border-bottom:2px solid #153b35;padding-bottom:20px}"
            "section{break-inside:avoid;border-bottom:1px solid #ccd6d2;padding:24px 0}"
            "small{color:#4e716a}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7f6;"
            "padding:16px;border-radius:8px}@media print{body{margin:0}}</style></head><body>",
            f"<header><p>NEXORA · Reporte auditable</p><h1>{escape(run.title)}</h1>",
            f"<p>Report Run: {escape(run.id)} · Corte: {run.report_cutoff.isoformat()} · "
            f"Versión: {escape(run.calculation_version)}</p></header>",
            *sections,
            "<footer><p>Este informe reconstruye evidencia persistida. No ejecuta decisiones "
            "ni garantiza resultados futuros.</p></footer></body></html>",
        ]
    )


def _tabular_rows(run: ReportRun) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = [
        {
            "section": "metadata",
            "record": "report_run_id",
            "key": run.id,
            "value": run.calculation_version,
            "status": run.status,
            "source_id": run.id,
        }
    ]
    sources = run.source_snapshot
    forecast = sources.get("forecast")
    if isinstance(forecast, dict):
        for point in forecast.get("forecast_points", []):
            if isinstance(point, dict):
                rows.append(
                    {
                        "section": "forecast",
                        "record": "point",
                        "key": point.get("timestamp"),
                        "value": point.get("forecast"),
                        "status": "persisted",
                        "source_id": forecast.get("id"),
                    }
                )
    scor = sources.get("scor")
    if isinstance(scor, dict):
        for metric in scor.get("metrics", []):
            if isinstance(metric, dict):
                rows.append(
                    {
                        "section": "scor",
                        "record": metric.get("metric_id"),
                        "key": metric.get("display_name"),
                        "value": metric.get("result_value"),
                        "status": metric.get("evidence_status"),
                        "source_id": scor.get("id"),
                    }
                )
    portfolio = sources.get("portfolio")
    if isinstance(portfolio, dict):
        for item in portfolio.get("items", []):
            if isinstance(item, dict):
                rows.append(
                    {
                        "section": "portfolio",
                        "record": item.get("rank"),
                        "key": item.get("series_key"),
                        "value": item.get("priority_score"),
                        "status": item.get("risk_level"),
                        "source_id": portfolio.get("id"),
                    }
                )
    decision = sources.get("decision")
    if isinstance(decision, dict):
        for item in decision.get("recommendations", []):
            if isinstance(item, dict):
                rows.append(
                    {
                        "section": "decision",
                        "record": item.get("rank"),
                        "key": item.get("title"),
                        "value": item.get("support_score"),
                        "status": item.get("status"),
                        "source_id": decision.get("id"),
                    }
                )
    return rows


def render_csv(run: ReportRun) -> str:
    output = io.StringIO(newline="")
    fields = ["section", "record", "key", "value", "status", "source_id"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in _tabular_rows(run):
        writer.writerow({key: _text(row.get(key)) for key in fields})
    return output.getvalue()
