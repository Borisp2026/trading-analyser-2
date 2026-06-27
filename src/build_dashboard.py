"""
Dashboard Builder for Trading Analyser 2.0
Generates index.html for GitHub Pages — auto-refreshes on each nightly run.
"""

import json
import os
from datetime import datetime


def signal_badge_style(rec: str) -> str:
    if "STRONG BUY" in rec:
        return "background:#00aa00;color:white;"
    elif "BUY" in rec:
        return "background:#44bb44;color:white;"
    elif "HOLD" in rec:
        return "background:#ff9900;color:white;"
    elif "WEAK" in rec:
        return "background:#ff6600;color:white;"
    return "background:#cc0000;color:white;"


def build_stock_card(r: dict) -> str:
    rec = r.get("reasoning", {})
    t = r.get("tech", {})
    cyc = r.get("cycle", {})
    ticker = r.get("ticker", "?")
    name = r.get("name", "")[:30]
    recommendation = rec.get("recommendation", "HOLD")
    score = rec.get("blended_score", 50)
    tech_score = rec.get("tech_score", 50)
    cycle_score = rec.get("cycle_score", 50)
    price = t.get("price", 0)
    change_1d = t.get("price_1d_pct", 0)
    rsi = t.get("rsi", 50)
    change_color = "green" if change_1d >= 0 else "red"

    reasons_html = "".join(f"<li>{r}</li>" for r in rec.get("reasons", [])[:6])

    cycle_html = ""
    if cyc and cyc.get("status") == "ok":
        cc = cyc.get("current_cycle", {})
        tl_break = "⚠️ YES" if cyc.get("trendline_break") else "No"
        confirm = "✅ YES" if cyc.get("confirmation_signal") else "No"
        cycle_html = f"""
        <div class="cycle-block">
            <strong>Cycle Analysis</strong><br>
            Signal: <span style="font-weight:bold">{cyc.get('cycle_signal','?')}</span> |
            Translation: {cc.get('translation','?')} |
            {cyc.get('pct_through_cycle',0):.0f}% through cycle<br>
            Trendline break: {tl_break} | Confirmation: {confirm}
            {'<br><span style="color:red">🔴 HIGH RISK ZONE</span>' if cyc.get('high_risk_zone') else ''}
        </div>
        """

    entry = rec.get("entry_price", "—")
    stop = rec.get("stop_loss", "—")
    target = rec.get("take_profit", "—")
    confidence = rec.get("confidence", "?")
    timing = rec.get("timing", "")

    return f"""
    <div class="stock-card" data-score="{score}" data-ticker="{ticker}" data-rec="{recommendation}">
        <div class="card-header" style="{signal_badge_style(recommendation)}">
            <div>
                <span class="ticker">{ticker}</span>
                <span class="company-name">{name}</span>
            </div>
            <div>
                <span class="rec-badge">{recommendation}</span>
                <span class="score-badge">{score:.0f}/100</span>
            </div>
        </div>
        <div class="card-body">
            <div class="price-row">
                <span class="price">${price:.3f}</span>
                <span style="color:{change_color}">{'+' if change_1d >= 0 else ''}{change_1d:.1f}%</span>
                <span class="rsi-badge">RSI {rsi:.0f}</span>
            </div>
            <div class="score-breakdown">
                Tech: {tech_score:.0f} | Cycle: {cycle_score:.0f} | Blended: {score:.0f}
            </div>
            <div class="trade-grid">
                <div><label>Entry</label><strong>${entry if entry else '—'}</strong></div>
                <div><label>Stop</label><strong style="color:red">${stop if stop else '—'}</strong></div>
                <div><label>Target</label><strong style="color:green">${target if target else '—'}</strong></div>
                <div><label>Confidence</label><strong>{confidence}</strong></div>
            </div>
            <div class="timing"><em>⏰ {timing}</em></div>
            {cycle_html}
            <details>
                <summary>📋 Full Analysis</summary>
                <ul class="reasons">{reasons_html}</ul>
            </details>
        </div>
    </div>
    """


def build_portfolio_section(portfolio: dict) -> str:
    real = portfolio.get("real", {})
    paper = portfolio.get("paper", {})
    holdings = real.get("holdings", [])
    pnl = real.get("total_pnl", 0)
    pnl_color = "green" if pnl >= 0 else "red"

    holdings_rows = ""
    for h in holdings:
        h_pnl = h.get("pnl", 0)
        h_color = "green" if h_pnl >= 0 else "red"
        holdings_rows += f"""
        <tr>
            <td><strong>{h['ticker']}</strong></td>
            <td>{h['shares']}</td>
            <td>${h['buy_price']:.3f}</td>
            <td>${h['current_price']:.3f}</td>
            <td>${h['value']:,.2f}</td>
            <td style="color:{h_color}">${h_pnl:+,.2f} ({h.get('pnl_pct',0):+.1f}%)</td>
            <td>{h.get('div_yield_pct',0):.1f}%</td>
        </tr>
        """

    return f"""
    <section id="portfolio" class="section">
        <h2>📁 Portfolio</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Portfolio Value</div>
                <div class="stat-value">${real.get('total_value', 0):,.2f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total P&amp;L</div>
                <div class="stat-value" style="color:{pnl_color}">${pnl:+,.2f} ({real.get('total_pnl_pct',0):+.1f}%)</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Annual Dividends</div>
                <div class="stat-value">${real.get('total_annual_dividends', 0):,.2f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Paper Win Rate</div>
                <div class="stat-value">{paper.get('win_rate_pct', 0):.1f}%</div>
            </div>
        </div>
        {'<table class="holdings-table"><thead><tr><th>Ticker</th><th>Shares</th><th>Buy</th><th>Current</th><th>Value</th><th>P&L</th><th>Div Yield</th></tr></thead><tbody>' + holdings_rows + '</tbody></table>' if holdings else '<p style="color:#888">No holdings recorded yet. Add via portfolio.json.</p>'}
    </section>
    """


def build_dashboard(results: list, portfolio: dict, output_path: str):
    today = datetime.now().strftime("%d %B %Y, %H:%M")
    cards_html = "\n".join(build_stock_card(r) for r in results)
    portfolio_html = build_portfolio_section(portfolio)

    buys = sum(1 for r in results if "BUY" in r["reasoning"].get("recommendation", ""))
    holds = sum(1 for r in results if "HOLD" in r["reasoning"].get("recommendation", ""))
    avoids = len(results) - buys - holds

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trading Analyser 2.0</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f1a; color: #e0e0e0; }}
header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; }}
header h1 {{ color: white; font-size: 24px; }}
header p {{ color: #aaa; font-size: 13px; }}
.section {{ padding: 25px 30px; }}
.section h2 {{ color: #fff; margin-bottom: 15px; font-size: 18px; }}
.filter-bar {{ display: flex; gap: 10px; padding: 15px 30px; background: #13132a; flex-wrap: wrap; align-items: center; }}
.filter-btn {{ padding: 6px 16px; border-radius: 20px; border: 1px solid #444; cursor: pointer; font-size: 13px; background: #1e1e3a; color: #ccc; transition: all 0.2s; }}
.filter-btn.active {{ background: #4a90d9; color: white; border-color: #4a90d9; }}
.filter-btn:hover {{ background: #2a2a5a; }}
#searchBox {{ padding: 6px 14px; border-radius: 20px; border: 1px solid #444; background: #1e1e3a; color: #ccc; font-size: 13px; }}
.stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px; }}
.stat-card {{ background: #1a1a2e; border-radius: 10px; padding: 15px; text-align: center; }}
.stat-label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }}
.stat-value {{ font-size: 20px; font-weight: bold; color: white; }}
.cards-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 18px; padding: 0 30px 30px; }}
.stock-card {{ background: #1a1a2e; border-radius: 12px; overflow: hidden; border: 1px solid #2a2a4a; transition: transform 0.2s, box-shadow 0.2s; }}
.stock-card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,0.4); }}
.card-header {{ padding: 12px 15px; display: flex; justify-content: space-between; align-items: center; }}
.ticker {{ font-size: 18px; font-weight: bold; margin-right: 8px; }}
.company-name {{ font-size: 12px; opacity: 0.8; }}
.rec-badge {{ font-size: 11px; font-weight: bold; padding: 3px 8px; border-radius: 4px; background: rgba(255,255,255,0.2); margin-right: 5px; }}
.score-badge {{ font-size: 11px; background: rgba(0,0,0,0.3); padding: 3px 8px; border-radius: 4px; }}
.card-body {{ padding: 15px; }}
.price-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }}
.price {{ font-size: 22px; font-weight: bold; color: white; }}
.rsi-badge {{ font-size: 11px; background: #2a2a5a; padding: 3px 8px; border-radius: 10px; }}
.score-breakdown {{ font-size: 11px; color: #888; margin-bottom: 10px; }}
.trade-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; margin: 10px 0; }}
.trade-grid div {{ background: #13132a; border-radius: 6px; padding: 6px 8px; text-align: center; }}
.trade-grid label {{ display: block; font-size: 10px; color: #888; margin-bottom: 2px; }}
.trade-grid strong {{ font-size: 12px; }}
.timing {{ font-size: 11px; color: #aaa; margin: 8px 0; }}
.cycle-block {{ background: #13132a; border-left: 3px solid #4a90d9; padding: 8px 10px; border-radius: 4px; font-size: 11px; margin: 8px 0; line-height: 1.6; }}
details summary {{ cursor: pointer; font-size: 12px; color: #4a90d9; margin-top: 8px; }}
.reasons {{ padding-left: 18px; margin-top: 8px; }}
.reasons li {{ font-size: 11px; color: #ccc; margin-bottom: 4px; line-height: 1.4; }}
.holdings-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.holdings-table th {{ background: #16213e; color: white; padding: 8px 10px; text-align: left; }}
.holdings-table td {{ padding: 8px 10px; border-bottom: 1px solid #2a2a4a; }}
.hidden {{ display: none !important; }}
a {{ color: #4a90d9; text-decoration: none; }}
</style>
</head>
<body>

<header>
    <div>
        <h1>📊 Trading Analyser 2.0</h1>
        <p>Last updated: {today} AWST | {len(results)} stocks | Data: Yahoo Finance</p>
    </div>
    <div style="text-align:right;font-size:13px;color:#aaa;">
        <div>🟢 BUY: {buys}</div>
        <div>🟡 HOLD: {holds}</div>
        <div>🔴 AVOID: {avoids}</div>
    </div>
</header>

<div class="section" style="padding-bottom:0;">
    <div class="stats-grid">
        <div class="stat-card"><div class="stat-label">Total Scanned</div><div class="stat-value">{len(results)}</div></div>
        <div class="stat-card"><div class="stat-label">Buy Signals</div><div class="stat-value" style="color:#44bb44">{buys}</div></div>
        <div class="stat-card"><div class="stat-label">Hold/Watch</div><div class="stat-value" style="color:#ff9900">{holds}</div></div>
        <div class="stat-card"><div class="stat-label">Avoid</div><div class="stat-value" style="color:#cc0000">{avoids}</div></div>
    </div>
</div>

{portfolio_html}

<div class="filter-bar">
    <strong style="color:#ccc;">Filter:</strong>
    <button class="filter-btn active" onclick="filterCards('all')">All</button>
    <button class="filter-btn" onclick="filterCards('buy')">Buy Signals</button>
    <button class="filter-btn" onclick="filterCards('hold')">Hold/Watch</button>
    <button class="filter-btn" onclick="filterCards('avoid')">Avoid</button>
    <button class="filter-btn" onclick="filterCards('asx')">ASX Only</button>
    <button class="filter-btn" onclick="filterCards('us')">US Only</button>
    &nbsp;|&nbsp;
    <strong style="color:#ccc;">Sort:</strong>
    <button class="filter-btn" onclick="sortCards('score')">By Score</button>
    <button class="filter-btn" onclick="sortCards('price')">By Price</button>
    <input id="searchBox" type="text" placeholder="🔍 Search ticker..." oninput="searchCards(this.value)">
</div>

<section class="section" style="padding:15px 30px 5px;">
    <h2>📈 Stock Analysis</h2>
</section>

<div class="cards-grid" id="cardsGrid">
{cards_html}
</div>

<footer style="text-align:center;padding:20px;color:#555;font-size:11px;border-top:1px solid #2a2a4a;">
    Trading Analyser 2.0 | ⚠️ Not financial advice. Do your own research.
</footer>

<script>
function filterCards(filter) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('.stock-card').forEach(card => {{
        const rec = card.dataset.rec || '';
        const ticker = card.dataset.ticker || '';
        let show = true;
        if (filter === 'buy') show = rec.includes('BUY');
        else if (filter === 'hold') show = rec.includes('HOLD');
        else if (filter === 'avoid') show = rec.includes('AVOID') || rec.includes('WEAK');
        else if (filter === 'asx') show = ticker.endsWith('.AX');
        else if (filter === 'us') show = !ticker.endsWith('.AX');
        card.classList.toggle('hidden', !show);
    }});
}}

function sortCards(by) {{
    const grid = document.getElementById('cardsGrid');
    const cards = Array.from(grid.querySelectorAll('.stock-card:not(.hidden)'));
    cards.sort((a, b) => {{
        if (by === 'score') return parseFloat(b.dataset.score) - parseFloat(a.dataset.score);
        return 0;
    }});
    cards.forEach(c => grid.appendChild(c));
}}

function searchCards(q) {{
    q = q.toUpperCase();
    document.querySelectorAll('.stock-card').forEach(card => {{
        card.classList.toggle('hidden', q && !card.dataset.ticker.includes(q));
    }});
}}
</script>

</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard saved: {output_path}")
