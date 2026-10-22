"""
Board-ready findings pack as one self-contained HTML file (print to PDF from
the browser). Structure follows OD evidence-synthesis practice: evidence
inventory first, then facts, interpretation and options kept separate,
implementation implications, and what the data still cannot tell us.
Personal names are replaced by job titles unless explicitly included.
"""

from datetime import datetime
from html import escape
from typing import Callable, Dict, List, Optional

CSS = """
:root{--paper:#FAF7F3;--ink:#1C1F24;--sec:#575C63;--faint:#8A8F96;--hair:#E7E0D8;--red:#C41E3A;--green:#257A55;--amber:#B97F24;--bad:#B02E2E}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 'DM Sans',system-ui,sans-serif}
main{max-width:960px;margin:0 auto;padding:56px 40px}
h1,h2,h3{font-family:'Playfair Display',Georgia,serif;font-weight:700;margin:0}
h1{font-size:40px;line-height:1.12}h2{font-size:26px;margin:6px 0 14px}h3{font-size:18px;margin:18px 0 8px}
.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;font-weight:600;color:var(--red)}
.faint{color:var(--faint)}.sec{color:var(--sec)}
section{margin:44px 0;page-break-inside:avoid}
.card{background:#fff;border:1px solid var(--hair);padding:18px 22px;margin:10px 0}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--hair);font-size:13.5px}
th{text-align:left;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--sec);padding:9px 12px;border-bottom:1px solid var(--hair)}
td{padding:8px 12px;border-bottom:1px solid var(--hair);vertical-align:top}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.tag{display:inline-block;border:1px solid var(--hair);border-radius:99px;padding:1px 8px;font-size:11px;color:var(--sec);margin:2px 4px 2px 0}
.reg{font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;margin-bottom:4px}
.fact{color:var(--ink)}.interp{color:var(--amber)}.rec{color:var(--red)}
.big{font-family:'Playfair Display',Georgia,serif;font-size:52px;font-weight:700;line-height:1}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}
.kpi .v{font-family:'Playfair Display',Georgia,serif;font-size:28px;font-weight:700}.kpi .l{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint)}
ol.waves{padding-left:20px}ol.waves li{margin-bottom:10px}
@media print{body{background:#fff}main{padding:0}section{margin:28px 0}a{color:inherit}}
"""


def _money(v: float) -> str:
    v = v or 0
    sign = "−" if v < 0 else ""
    v = abs(v)
    return f"{sign}${v / 1e6:.2f}M" if v >= 1e6 else f"{sign}${v / 1e3:.0f}k" if v >= 1e3 else f"{sign}${v:.0f}"


def _signed(v: float, money: bool = False) -> str:
    if not v:
        return "—"
    return ("+" if v > 0 else "") + (_money(v) if money else f"{v:g}")


def _table(headers: List[str], rows: List[List[str]], numeric: Optional[List[int]] = None) -> str:
    numeric = numeric or []
    th = "".join(f'<th class="{"n" if i in numeric else ""}">{escape(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f'<td class="{"n" if i in numeric else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>"
        for r in rows
    )
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def build_pack(
    *,
    org_name: str,
    metrics: Dict,
    ai_analysis: Dict,
    comparison: Optional[Dict],
    focus: Optional[Dict],
    plan: Optional[Dict],
    strategy_provided: bool,
    design_criteria: Optional[str],
    scrub: Callable[[str], str],
) -> str:
    """All text that may contain names passes through `scrub` before escaping."""
    e = lambda t: escape(scrub(str(t or "")))  # noqa: E731
    now = datetime.now().strftime("%d %B %Y")
    health = metrics.get("health_indicators", {})
    span = metrics.get("span_of_control", {})
    layers = metrics.get("layer_analysis", {})
    depts = metrics.get("department_analysis", []) or []
    wa = (ai_analysis or {}).get("work_activities_analysis") or {}
    diag = (ai_analysis or {}).get("category_2_health_diagnosis") or {}
    cat4 = (ai_analysis or {}).get("category_4_recommended_archetypes")
    recs = cat4.get("recommendations", []) if isinstance(cat4, dict) else []
    llm = (ai_analysis or {}).get("_llm") or wa.get("_llm") or {}
    parts: List[str] = []

    # Cover
    parts.append(f"""<header><p class="eyebrow">Organization design · findings pack</p>
<h1>{e(org_name)}</h1>
<p class="sec">{now} · {metrics.get('total_employees', 0)} people · {len(depts)} departments</p>
<p class="faint">Registers are kept separate: <b class="fact">Fact</b> = computed from the uploaded data · <b class="interp">Interpretation</b> = analysis, AI-assisted where marked · <b class="rec">Recommendation</b> = proposed action.</p></header>""")

    # 1. Evidence inventory
    wa_cov = wa.get("work_activities_summary", {}).get("positions_with_activities") if wa else None
    inv_rows = [
        ["Org structure CSV", "OBSERVABLE", f"{metrics.get('total_employees', 0)} people, {len(depts)} departments", e("; ".join((metrics.get('data_quality') or {}).get('issues', [])[:3])) or "None reported"],
        ["Work activities (role descriptions)", "OBSERVABLE (text)", f"{wa_cov} positions" if wa_cov else ("Analysed" if wa else "Not analysed"), "Self-described activities; not time-measured"],
        ["Strategy context", "PERCEPTUAL", "Provided" if strategy_provided else "Not provided", "Stated intent, not observed behaviour"],
        ["Design criteria", "PERCEPTUAL", "Provided" if design_criteria else "Not provided", ""],
        ["AI analysis", "MODEL-INFERRED", escape(llm.get("model_served") or "—"), "Industry comparisons and archetype fit are inferred, not measured"],
    ]
    parts.append(f"""<section><p class="eyebrow">01 · Evidence inventory</p><h2>What this pack is based on</h2>
{_table(['Source', 'Type', 'Coverage', 'Gaps / caveats'], inv_rows)}</section>""")

    # 2. Current state — facts
    comps = health.get("components", []) or []
    vs = span.get("distribution_vs_benchmark", {}) or {}
    kpis = [
        ("Structural health", f"{health.get('health_score', 0)}/100"),
        ("Managers", f"{metrics.get('manager_stats', {}).get('total_managers', 0)} ({metrics.get('manager_stats', {}).get('manager_ratio_pct', 0)}%)"),
        ("Layers", layers.get("total_layers", 0)),
        ("Spans within benchmark", f"{vs.get('Within benchmark', 0)} of {sum(vs.values()) if vs else 0}"),
        ("People cost", _money(metrics.get("cost_analysis", {}).get("total_cost", 0))),
    ]
    kpi_html = "".join(f'<div class="card kpi"><div class="l">{escape(l)}</div><div class="v">{escape(str(v))}</div></div>' for l, v in kpis)
    comp_rows = [[escape(c["label"]), f'{c["score"]}', escape(c["value"]), escape(c["benchmark"])] for c in comps]
    dept_rows = [[escape(d["department"]), str(d["headcount"]), str(d["managers"]), f'{d["average_span"]}',
                  f'↓{d["spans_vs_benchmark"]["below"]} ✓{d["spans_vs_benchmark"]["within"]} ↑{d["spans_vs_benchmark"]["above"]}',
                  "–".join(str(x) for x in d.get("layers_spanned", [])), f'{d["cost_pct"]}%'] for d in depts]
    parts.append(f"""<section><p class="eyebrow">02 · Current state</p><h2>Facts from the data</h2>
<p class="reg fact">Fact</p><div class="grid">{kpi_html}</div>
<h3>How the health score is made up</h3>{_table(['Check', 'Score', 'Value', 'Benchmark'], comp_rows, [1])}
<h3>Departments</h3>{_table(['Department', 'People', 'Managers', 'Avg span', 'Spans vs benchmark', 'Layers', 'Cost share'], dept_rows, [1, 2, 3, 6])}
<p class="faint">Spans are judged against 10–20 direct reports for managers tagged as frontline operational, and 5–10 for all other managers. Layers are counted from the reporting chain.</p></section>""")

    # 3. Interpretation
    interp: List[str] = []
    for p in diag.get("pathologies", []) or []:
        tags = "".join(f'<span class="tag">{escape(str(t))}</span>' for t in [p.get("dimension"), p.get("evidence_class"), p.get("confidence") and f"Confidence {p.get('confidence')}"] if t)
        interp.append(f"""<div class="card"><p class="reg interp">Interpretation · {e(p.get('severity'))} severity</p><b>{e(p.get('name'))}</b>
<p class="sec">{e(p.get('description'))}</p>
{f'<p><b>Evidence:</b> {e(p.get("supporting_evidence"))}</p>' if p.get('supporting_evidence') else ''}
{f'<p><b>Does not fully fit:</b> {e(p.get("disconfirming_evidence"))}</p>' if p.get('disconfirming_evidence') and p.get('disconfirming_evidence') != 'None identified' else ''}{tags}</div>""")
    for label, items, title_key in [
        ("Duplicated work", (wa.get("activity_duplication") or {}).get("duplications", []), "activity"),
        ("Missing activities", (wa.get("missing_activities") or {}).get("gaps", []), "activity"),
        ("Weak hand-offs", (wa.get("coordination_gaps") or {}).get("gaps", []), "handoff_point"),
    ]:
        for it in (items or [])[:5]:
            tags = "".join(f'<span class="tag">{escape(str(t))}</span>' for t in [it.get("dimension"), it.get("indicator_type") and f"{it['indicator_type']} indicator", it.get("confidence") and f"Confidence {it['confidence']}"] if t)
            action = it.get("recommended_action") or it.get("recommendation") or it.get("recommended_interface")
            interp.append(f"""<div class="card"><p class="reg interp">Interpretation · {escape(label)}{f' · {e(it.get("severity"))}' if it.get('severity') else ''}</p><b>{e(it.get(title_key))}</b>
{f'<p><b>Evidence:</b> {e(it.get("evidence"))}</p>' if it.get('evidence') else ''}
{f'<p class="reg rec" style="margin-top:8px">Recommendation</p><p>{e(action)}</p>' if action else ''}{tags}</div>""")
    if interp:
        parts.append(f"""<section><p class="eyebrow">03 · Diagnosis</p><h2>What the evidence suggests</h2>{''.join(interp)}</section>""")

    # 4. Options
    if comparison and len(comparison.get("options", [])) > 1:
        res = comparison["result"]
        crit = comparison["criteria"]
        rows = []
        for o in comparison["options"]:
            rank = res["ranking"].index(o["id"]) + 1 if o["id"] in res["ranking"] else "–"
            cells = [("–" if res["cells"][o["id"]].get(c["id"]) is None else f'{round(res["cells"][o["id"]][c["id"]])}') for c in crit]
            total = res["totals"].get(o["id"])
            rows.append([str(rank), e(o["name"]), *cells, "–" if total is None else f"<b>{round(total)}</b>"])
        heads = ["#", "Option", *[f"{c['name']} ({c['weight']})" for c in crit], "Total"]
        note = "" if res.get("complete") else '<p class="faint">Some judged scores are missing — the ranking is provisional.</p>'
        fig_rows = [[e(o["name"]), str(o["figures"]["health_score"]), str(o["figures"]["layers"]), str(o["figures"]["managers"]),
                     _money(o["figures"]["total_cost"]), f'{o["figures"]["people_affected_pct"]}%'] for o in comparison["options"]]
        arch = "".join(f'<p><b>{e(r.get("archetype"))}</b> — fit {r.get("overall_fit_score", "–")}/100. {e(r.get("why_it_fits"))}</p>' for r in recs[:2])
        parts.append(f"""<section><p class="eyebrow">04 · Options</p><h2>Structural options compared</h2>
{f'<p class="reg interp">Interpretation · recommended archetypes (AI-assisted, weighted scoring)</p>{arch}' if arch else ''}
<p class="reg fact">Scores against the design criteria</p>{_table(heads, rows, list(range(2, len(heads))))}{note}
<h3>The figures behind them</h3>{_table(['Option', 'Health', 'Layers', 'Managers', 'Cost', 'People affected'], fig_rows, [1, 2, 3, 4, 5])}</section>""")

    # 5. Implementation of the focus option
    if focus and plan:
        d = focus["delta"]
        risk_rows = [[escape(r["severity"]), escape(r["area"]), e(r["risk"]), e(r["mitigation"])] for r in plan["risks"]]
        wave_items = []
        for w in plan["waves"]:
            moves_html = ""
            if w["moves"]:
                lis = []
                for m in w["moves"]:
                    why = f' <span class="faint">(why: {e(m["note"])})</span>' if m.get("note") else ""
                    lis.append(f"<li>{e(m['message'])}{why}</li>")
                moves_html = "<ul>" + "".join(lis) + "</ul>"
            wave_items.append(f"<li><b>{escape(w['title'])}</b> — <span class='sec'>{escape(w['guidance'])}</span>{moves_html}</li>")
        waves = "".join(wave_items)
        s = plan["summary"]
        parts.append(f"""<section><p class="eyebrow">05 · Implementation</p><h2>What it takes: {e(focus['name'])}</h2>
<p class="reg rec">Recommendation under consideration</p>
<div class="grid">
<div class="card kpi"><div class="l">Health</div><div class="v">{focus['baseline']['health_score']} → {focus['scenario']['health_score']}</div></div>
<div class="card kpi"><div class="l">Layers</div><div class="v">{_signed(d['layers'])}</div></div>
<div class="card kpi"><div class="l">Annual cost</div><div class="v">{_signed(plan['cost']['net_change'], True)}</div></div>
<div class="card kpi"><div class="l">People affected</div><div class="v">{s['people_affected']} ({s['people_affected_pct']}%)</div></div>
</div>
<p class="sec">{s['roles_removed']} roles removed · {s['roles_added']} added · {s['new_manager']} people get a new manager · {s['managers_gaining']} manager{'' if s['managers_gaining'] == 1 else 's'} gain people, {s['managers_losing']} lose people. {escape(plan['cost']['note'])}</p>
<h3>Risks</h3>{_table(['Severity', 'Area', 'Risk', 'Mitigation'], risk_rows) if risk_rows else '<p class="faint">No rule-based risks flagged.</p>'}
<h3>Transition sequence</h3><ol class="waves">{waves}</ol></section>""")

    # 6. What we still don't know
    gaps = list((ai_analysis or {}).get("data_gaps") or []) + list(wa.get("data_gaps") or [])
    if gaps:
        rows = [[e(g.get("gap")), e(g.get("why_it_matters")), e(g.get("observable_indicator_to_close"))] for g in gaps]
        parts.append(f"""<section><p class="eyebrow">06 · Limits</p><h2>What we still don't know</h2>
{_table(['Gap', 'Why it matters', 'What to measure next'], rows)}</section>""")

    parts.append(f"""<footer class="faint" style="border-top:1px solid var(--hair);padding-top:14px;font-size:12px">
Generated by Org Design Analyzer on {now}. Figures are computed from the uploaded data; AI-assisted interpretation is labelled and should be validated with observable evidence before decisions.
</footer>""")

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(org_name)} — findings pack</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><main>{''.join(parts)}</main></body></html>"""
