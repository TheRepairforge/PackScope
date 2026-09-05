"""Per-pack Battery Health Report — a self-contained, print-friendly HTML card.

Light theme (prints cleanly on paper, reads as a professional customer document).
Opened in the browser; the user prints to PDF via Ctrl+P. No dependencies.
"""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import db as dbmod
from .models import CELL_V_MAX, CELL_V_MIN, DIFF_BAD, DIFF_WARN, Verdict
from .units import fmt_temp, human_dt
from .verdict import verdict_label

_VCOL = {"HEALTHY": "#1a8f5a", "REPAIRABLE": "#b8860b", "SUSPECT": "#d1561a",
         "REAL_FAULT": "#c23b3b", "UNKNOWN": "#666"}


def _cell_color(v, mn, spread):
    if v < CELL_V_MIN:
        return "#c23b3b"
    if abs(v - mn) < 1e-6 and spread > DIFF_WARN:
        return "#c23b3b" if spread > DIFF_BAD else "#b8860b"
    return "#1a8f5a"


def build_html(conn, serial_no: str, generated_at: Optional[str] = None,
               unit: str = "C") -> str:
    """Build the health-report HTML for one pack. Raises ValueError if unknown."""
    hist = dbmod.get_history(conn, serial_no)
    if not hist:
        raise ValueError(f"no readings for {serial_no}")
    bat = dbmod.get_battery(conn, serial_no)
    reps = dbmod.get_repair_sessions(conn, serial_no)
    latest = hist[-1]
    gen = generated_at or datetime.now().isoformat(timespec="minutes")

    verdict = latest["verdict"] or "UNKNOWN"
    vlabel = verdict_label(Verdict(verdict)) if verdict in Verdict.__members__ else verdict
    vcol = _VCOL.get(verdict, "#666")
    alias = (bat["alias"] if bat and bat["alias"] else "") or latest["model"] or "?"
    owner = (bat["owner"] if bat else "") or "—"
    status = (bat["status"] if bat else "") or "—"

    try:
        cells = [c / 1000.0 for c in json.loads(latest["cell_voltages_mv"] or "[]") if c]
    except (json.JSONDecodeError, TypeError):
        cells = []
    mn = min(cells) if cells else 0
    spread = (max(cells) - mn) if cells else 0

    def esc(x):
        return html.escape(str(x if x is not None else "—"))

    cell_bars = ""
    for i, v in enumerate(cells, 1):
        pct = max(4, min(100, (v - CELL_V_MIN) / (CELL_V_MAX - CELL_V_MIN) * 100))
        col = _cell_color(v, mn, spread)
        cell_bars += (
            f'<div class="cell"><span>C{i}</span>'
            f'<div class="bar"><i style="width:{pct:.0f}%;background:{col}"></i></div>'
            f'<b>{v:.2f} V</b></div>')

    rep_rows = ""
    for s in reps:
        held = s["held"]
        tag = ("held" if held == 1 else "re-locked" if held == 0 else "unknown")
        tcol = "#1a8f5a" if held == 1 else "#c23b3b" if held == 0 else "#666"
        rep_rows += (
            f'<tr><td>{esc(human_dt(s["started_at"]))}</td>'
            f'<td>{esc(s["verdict_before"])} → unlock</td>'
            f'<td style="color:{tcol};font-weight:600">{tag}</td>'
            f'<td>{esc(s["notes"])}</td></tr>')
    if not rep_rows:
        rep_rows = '<tr><td colspan="4" style="color:#888">No repair sessions.</td></tr>'

    vhist = "".join(
        f'<span class="vdot" title="{esc(d)}" '
        f'style="background:{_VCOL.get(vv, "#666")}"></span>'
        for d, vv in dbmod.verdict_series(conn, serial_no))

    t1, t2 = latest["temp1_c"], latest["temp2_c"]
    temp = (f"{fmt_temp(t1, unit)} / {fmt_temp(t2, unit)}"
            if t1 is not None and t2 is not None else "—")

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Battery Health Report — {esc(alias)}</title>
<style>
  * {{ box-sizing:border-box; }}
  body {{ font-family:'Segoe UI',system-ui,sans-serif; color:#1c2733; margin:0;
         background:#eef1f4; padding:24px; }}
  .sheet {{ max-width:760px; margin:0 auto; background:#fff; border-radius:12px;
            padding:28px 32px; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
  .top {{ display:flex; justify-content:space-between; align-items:flex-start;
          border-bottom:2px solid #eef1f4; padding-bottom:14px; }}
  .top h1 {{ font-size:20px; margin:0; }} .top .sn {{ color:#6b7885; font:13px monospace; }}
  .brand {{ text-align:right; color:#6b7885; font-size:12px; }}
  .brand b {{ color:#0e7f92; font-size:15px; }}
  .verdict {{ margin:18px 0; padding:14px 18px; border-radius:10px; color:#fff;
              background:{vcol}; }}
  .verdict h2 {{ margin:0 0 4px; font-size:18px; }} .verdict p {{ margin:0; opacity:.95; font-size:13px; }}
  .grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:16px 0; }}
  .kv {{ background:#f5f7f9; border-radius:8px; padding:10px 12px; }}
  .kv span {{ display:block; color:#6b7885; font-size:11px; text-transform:uppercase;
              letter-spacing:.4px; }}
  .kv b {{ font-size:16px; }}
  h3 {{ font-size:13px; text-transform:uppercase; letter-spacing:.5px; color:#6b7885;
        margin:20px 0 8px; }}
  .cells {{ display:flex; gap:10px; }}
  .cell {{ flex:1; text-align:center; font-size:12px; }}
  .cell .bar {{ height:70px; background:#eef1f4; border-radius:6px; display:flex;
                align-items:flex-end; overflow:hidden; margin:4px 0; }}
  .cell .bar i {{ display:block; height:100%; border-radius:6px; }}
  .cell span {{ color:#6b7885; }} .cell b {{ font:12px monospace; }}
  .vstrip {{ display:flex; gap:3px; }}
  .vdot {{ width:14px; height:20px; border-radius:3px; display:inline-block; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  td, th {{ text-align:left; padding:7px 8px; border-bottom:1px solid #eef1f4; }}
  .foot {{ margin-top:22px; color:#96a1ad; font-size:11px; border-top:1px solid #eef1f4;
           padding-top:12px; }}
  @media print {{ body {{ background:#fff; padding:0; }} .sheet {{ box-shadow:none; }} }}
</style></head><body><div class="sheet">
  <div class="top">
    <div><h1>{esc(alias)}</h1><div class="sn">{esc(latest['model'])} · S/N {esc(serial_no)}</div></div>
    <div class="brand"><b>PocketOBI</b><br>Battery Health Report<br>The Repair Forge<br>{esc(human_dt(gen))}</div>
  </div>
  <div class="verdict"><h2>{esc(vlabel)}</h2><p>{esc(latest['verdict_detail'])}</p></div>
  <div class="grid">
    <div class="kv"><span>Capacity</span><b>{esc(latest['capacity_ah'])} Ah</b></div>
    <div class="kv"><span>Pack voltage</span><b>{(latest['pack_voltage_mv'] or 0)/1000:.2f} V</b></div>
    <div class="kv"><span>Cycles</span><b>{esc(latest['cycle_count'])}</b></div>
    <div class="kv"><span>Temp cell/board</span><b>{esc(temp)}</b></div>
    <div class="kv"><span>Owner</span><b>{esc(owner)}</b></div>
    <div class="kv"><span>Status</span><b>{esc(status)}</b></div>
    <div class="kv"><span>First seen</span><b>{esc(hist[0]['read_at'][:10])}</b></div>
    <div class="kv"><span>Last seen</span><b>{esc(latest['read_at'][:10])}</b></div>
  </div>
  <h3>Cell voltages</h3><div class="cells">{cell_bars or '—'}</div>
  <h3>Verdict over time</h3><div class="vstrip">{vhist or '—'}</div>
  <h3>Repair history</h3>
  <table><tr><th>Date</th><th>Action</th><th>Result</th><th>Notes</th></tr>{rep_rows}</table>
  <div class="foot">Generated by PackScope · firmware {esc(latest['fw_version'])} ·
    diagnostic aid, not a warranty. Cell scale 2.5–4.2 V.</div>
</div></body></html>"""


def export_health_card(conn, serial_no: str, path,
                       generated_at: Optional[str] = None, unit: str = "C") -> Path:
    p = Path(path)
    p.write_text(build_html(conn, serial_no, generated_at, unit), encoding="utf-8")
    return p
