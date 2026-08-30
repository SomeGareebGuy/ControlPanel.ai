"""
build_dashboard.py
--------------------
Renders audit_log.jsonl into a single static HTML dashboard
(docs/dashboard.html) -- the "metrics & monitoring" view a skeptical
stakeholder would ask for: decision breakdown, cost savings, and a
full per-interaction audit table. Run after demo.py.
"""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
LOG_PATH = os.path.join(ROOT, "audit_log.jsonl")
OUT_PATH = os.path.join(ROOT, "docs", "dashboard.html")

COLORS = {
    "allow": "#1d6d3d",
    "edit": "#b76312",
    "flag_for_review": "#b51d1d",
    "block": "#7f0f0f",
}

DISPLAY_DECISION_LABELS = {
    "allow": "Allow",
    "edit": "Edit",
    "flag_for_review": "Flag for review",
    "block": "Block",
}


def format_decision_label(decision: str) -> str:
    return DISPLAY_DECISION_LABELS.get(decision, decision.replace("_", " ").title())


def main():
    with open(LOG_PATH) as f:
        records = [json.loads(line) for line in f]

    counts = {}
    for r in records:
        counts[r["decision"]] = counts.get(r["decision"], 0) + 1
    n_escalated = sum(r["escalated"] for r in records)
    total_units = sum(r["cost_units"] for r in records)
    naive_units = len(records) * 6
    savings = 100 * (1 - total_units / naive_units)

    rows = ""
    for r in records:
        color = COLORS.get(r["decision"], "#888")
        label = format_decision_label(r["decision"])
        rows += f"""
        <tr>
          <td>{r['query_id']}</td>
          <td>{r['use_case']}</td>
          <td style="max-width:320px; color:#f2d7d7;">{r['query_text']}</td>
          <td><span class="badge badge-{r['decision']}" style="background:{color}; box-shadow: 0 0 10px {color}, inset 0 0 0 1px rgba(255,255,255,0.08);">{label}</span></td>
          <td>{'yes' if r['escalated'] else 'no'}</td>
          <td>{r['cost_units']}</td>
          <td style="max-width:360px; color:#f0d8d8;">{r['reasons'][0]}</td>
        </tr>"""

    cards = "".join(
        f'<div class="card"><div class="card-num">{v}</div><div class="card-label">{format_decision_label(k)}</div></div>'
        for k, v in counts.items()
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ControlPlane.ai — Live Oversight Dashboard</title>
<style>
  :root {{
    --bg: #0b0b0d;
    --panel: #121316;
    --panel-alt: #171a1d;
    --border: #2e2a2a;
    --text: #f4f1f1;
    --muted: #c8baba;
    --accent: #b30d0d;
    --accent-soft: #7b0d0d;
    --shadow: rgba(0, 0, 0, 0.5);
  }}

  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, Segoe UI, Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    margin: 0;
    padding: 32px;
  }}
  h1 {{
    font-size: 24px;
    margin: 0 0 6px;
    letter-spacing: 0.02em;
    color: #f9eeee;
  }}
  .sub {{
    color: var(--muted);
    margin-bottom: 24px;
    font-size: 13px;
    letter-spacing: 0.02em;
  }}
  .cards {{
    display: flex;
    gap: 16px;
    margin-bottom: 26px;
    flex-wrap: wrap;
  }}
  .card {{
    background: #121316;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    min-width: 140px;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.02), 0 10px 16px rgba(0,0,0,0.4);
  }}
  .card-num {{
    font-size: 28px;
    font-weight: 700;
    line-height: 1.1;
    color: #f3d5d5;
  }}
  .card-label {{
    color: var(--muted);
    font-size: 12px;
    text-transform: capitalize;
    margin-top: 6px;
    letter-spacing: 0.04em;
  }}
  .metrics {{
    background: #141415;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 24px;
    color: #f3ecec;
    font-size: 14px;
    box-shadow: 0 0 0 1px rgba(255,255,255,0.02);
  }}
  .metrics b {{ color: #ffb4b4; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
  }}
  th, td {{
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid #221b1b;
    vertical-align: top;
  }}
  th {{
    color: #d7b5b5;
    background: #140d0d;
    font-weight: 700;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.06em;
  }}
  td {{ color: #f5ecec; }}
  tbody tr:hover {{ background: #161314; }}
  .badge {{
    display: inline-block;
    color: #fff4f4;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.02em;
    white-space: nowrap;
    border: 1px solid rgba(255,255,255,0.12);
    text-shadow: 0 0 8px rgba(255,255,255,0.2);
  }}
</style></head>
<body>
  <h1><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#ff4d4d;box-shadow:0 0 12px #ff4d4d;margin-right:10px;vertical-align:middle;"></span>ControlPlane.ai - Live AI Oversight Dashboard</h1>
  <div class="sub"><span style="color:#ff6a6a;">|</span> Performance <span style="color:#ff6a6a;">|</span> Cost <span style="color:#ff6a6a;">|</span> Responsibility <span style="color:#ff6a6a;">|</span> {len(records)} interactions monitored</div>
  <div class="cards">{cards}</div>
  <div class="metrics">
    Escalated to multi-sample check: <b>{n_escalated}/{len(records)}</b> &nbsp;|&nbsp;
    Model-call cost units used: <b>{total_units}</b> (vs {naive_units} naive) &nbsp;|&nbsp;
    Adaptive-cost savings: <b>{savings:.1f}%</b>
  </div>
  <table>
    <thead>
      <tr><th>ID</th><th>Use case</th><th>Query</th><th>Decision</th><th>Escalated</th><th>Cost units</th><th>Reason (audit trail)</th></tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body></html>"""

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write(html)
    print(f"Dashboard written to {os.path.abspath(OUT_PATH)}")


if __name__ == "__main__":
    main()
