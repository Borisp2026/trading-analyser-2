"""Dashboard Builder for Trading Analyser 2.0 — 8 tabs"""
import json, os
from datetime import datetime

def signal_style(rec):
    if "STRONG BUY" in rec: return "background:#00aa00;color:white;"
    elif "BUY" in rec: return "background:#44bb44;color:white;"
    elif "HOLD" in rec: return "background:#ff9900;color:white;"
    elif "WEAK" in rec: return "background:#ff6600;color:white;"
    return "background:#cc0000;color:white;"

def build_stock_card(r):
    rec=r.get("reasoning",{}); t=r.get("tech",{}); cyc=r.get("cycle",{})
    corr=r.get("correlation",{})
    ticker=r.get("ticker","?"); name=r.get("name","")[:30]
    recommendation=rec.get("recommendation","HOLD"); score=rec.get("blended_score",50)
    tech_score=rec.get("tech_score",50); cycle_score=rec.get("cycle_score",50)
    price=t.get("price",0); change_1d=t.get("price_1d_pct",0); rsi=t.get("rsi",50)
    change_color="green" if change_1d>=0 else "red"
    change_prefix="+" if change_1d>=0 else ""
    change_arrow="▲ " if change_1d>=0 else "▼ "
    reasons_html="".join(f"<li>{x}</li>" for x in rec.get("reasons",[])[:6])
    entry=rec.get("entry_price",""); stop=rec.get("stop_loss",""); target=rec.get("take_profit","")
    confidence=rec.get("confidence","?"); timing=rec.get("timing","")
    entry_str=f"${entry:.3f}" if entry else "—"
    stop_str=f"${stop:.3f}" if stop else "—"
    target_str=f"${target:.3f}" if target else "—"
    cycle_html=""
    if cyc and cyc.get("status")=="ok":
        cc=cyc.get("current_cycle",{})
        cycle_html=(f'<div class="cycle-block"><b>Cycle:</b> {cyc.get("cycle_signal","?")} | '
            f'{cc.get("translation","?")} | {cyc.get("pct_through_cycle",0):.0f}% through | '
            f'TL Break: {"YES" if cyc.get("trendline_break") else "No"} | '
            f'Confirm: {"YES" if cyc.get("confirmation_signal") else "No"}'
            +(' | <span style="color:red">HIGH RISK</span>' if cyc.get("high_risk_zone") else "")
            +"</div>")
    corr_html=""
    if corr and corr.get("status")=="ok":
        trend_color="#44bb44" if corr.get("us_trend")=="BULLISH" else "#cc0000" if corr.get("us_trend")=="BEARISH" else "#ff9900"
        corr_html=(f'<div class="corr-block">US Correlation: avg {corr.get("avg_correlation",0):.2f} | '
            f'US Trend: <span style="color:{trend_color}">{corr.get("us_trend","?")}</span> | '
            f'{corr.get("outlook","")}')
        for bname,bd in (corr.get("benchmarks",{}) or {}).items():
            corr_html+=f' | {bname} r={bd.get("correlation","?")}'
        corr_html+='</div>'
    has_chart = bool(r.get("chart_data",{}).get("candles"))
    chart_btn = f'<button class="btn-chart" onclick="showChart(\'{ticker}\')" style="margin-top:6px;padding:4px 12px;font-size:12px;background:#1a3a5c;color:#4a90d9;border:1px solid #4a90d9;border-radius:6px;cursor:pointer">Show Chart</button>' if has_chart else ""
    return (f'<div class="stock-card" data-score="{score}" data-ticker="{ticker}" data-rec="{recommendation}">'
        f'<div class="card-header" style="{signal_style(recommendation)}">'
        f'<div><span class="ticker">{ticker}</span><span class="company-name">{name}</span></div>'
        f'<div><span class="rec-badge">{recommendation}</span><span class="score-badge">{score:.0f}/100</span></div></div>'
        f'<div class="card-body">'
        f'<div class="price-row"><span class="price">${price:.3f}</span>'
        f'<span style="color:{change_color}">{change_arrow}{change_prefix}{change_1d:.1f}%</span>'
        f'<span class="rsi-badge">RSI {rsi:.0f}</span></div>'
        f'<div class="score-breakdown">Tech:{tech_score:.0f} | Cycle:{cycle_score:.0f} | Blended:{score:.0f}</div>'
        f'<div class="trade-grid">'
        f"<div><label>Entry</label><strong>{entry_str}</strong></div>"
        f'<div><label>Stop</label><strong style="color:red">{stop_str}</strong></div>'
        f'<div><label>Target</label><strong style="color:green">{target_str}</strong></div>'
        f"<div><label>Confidence</label><strong>{confidence}</strong></div></div>"
        f'<div class="timing">{timing}</div>'
        f'{chart_btn}'
        # Cycle-phase and correlation detail moved behind "Full Analysis" -- decision-relevant
        # fields (price, rating, entry/stop/target) stay on the card face; the rest is one
        # click deeper instead of printed on every card regardless of whether it's needed.
        f'<details><summary>Full Analysis</summary>{cycle_html}{corr_html}<ul class="reasons">{reasons_html}</ul></details>'
        f"</div></div>")

def build_portfolio_html(portfolio, stock_advice=None):
    real=portfolio.get("real",{}); paper=portfolio.get("paper",{})
    holdings=real.get("holdings",[]); pnl=real.get("total_pnl",0)
    pnl_color="green" if pnl>=0 else "red"; pnl_prefix="+" if pnl>=0 else ""
    pnl_arrow="▲ " if pnl>=0 else "▼ "
    rows=""
    for h in holdings:
        hp=h.get("pnl",0); hc="green" if hp>=0 else "red"; hpfx="+" if hp>=0 else ""
        harrow="▲ " if hp>=0 else "▼ "
        rows+=(f'<tr><td><b>{h["ticker"]}</b></td><td>{h["shares"]}</td>'
            f'<td>${h["buy_price"]:.3f}</td><td>${h["current_price"]:.3f}</td>'
            f'<td>${h["value"]:,.2f}</td><td style="color:{hc}">{harrow}{hpfx}${hp:,.2f} ({h.get("pnl_pct",0):+.1f}%)</td>'
            f'<td>{h.get("div_yield_pct",0):.1f}%</td>'
            f'<td><button onclick="removeHolding(\'{h["ticker"]}\')" class="btn-remove">Remove</button></td></tr>')
    table=(f'<table class="holdings-table"><thead><tr><th>Ticker</th><th>Shares</th><th>Buy</th>'
        f'<th>Current</th><th>Value</th><th>P&L</th><th>Div Yield</th><th></th></tr></thead>'
        f'<tbody>{rows}</tbody></table>' if holdings else
        '<p style="color:#888;margin-bottom:20px;">No holdings yet. Use the Add Holding tab.</p>')
    tv=real.get("total_value",0); tc=real.get("total_cost",0)
    divs=real.get("total_annual_dividends",0); wr=paper.get("win_rate_pct",0)
    return (f'<section id="portfolio" class="section"><h2>Portfolio Summary</h2>'
        f'<div class="stats-grid">'
        f'<div class="stat-card"><div class="stat-label">Portfolio Value</div><div class="stat-value">${tv:,.2f}</div></div>'
        f'<div class="stat-card"><div class="stat-label">Total Cost</div><div class="stat-value">${tc:,.2f}</div></div>'
        f'<div class="stat-card"><div class="stat-label">P&L</div><div class="stat-value" style="color:{pnl_color}">{pnl_arrow}{pnl_prefix}${pnl:,.2f} ({real.get("total_pnl_pct",0):+.1f}%)</div></div>'
        f'<div class="stat-card"><div class="stat-label">Annual Dividends</div><div class="stat-value">${divs:,.2f}</div></div>'
        f'<div class="stat-card"><div class="stat-label">Paper Win Rate</div><div class="stat-value">{wr:.1f}%</div></div>'
        f'</div>{table}</section>')

def _build_signal_history_html(signal_history, accuracy):
    if not signal_history:
        return '<p style="color:#888">No signal history yet. Runs automatically each nightly report.</p>'
    overall=accuracy.get("overall_accuracy",0) if accuracy else 0
    total=accuracy.get("total_signals",0) if accuracy else 0
    correct=accuracy.get("correct_signals",0) if accuracy else 0
    acc_color="#44bb44" if overall>=60 else "#ff9900" if overall>=50 else "#cc0000"
    html=(f'<div class="stats-grid" style="margin-bottom:20px">'
        f'<div class="stat-card"><div class="stat-label">Overall Accuracy</div>'
        f'<div class="stat-value" style="color:{acc_color}">{overall:.1f}%</div></div>'
        f'<div class="stat-card"><div class="stat-label">Total Resolved</div>'
        f'<div class="stat-value">{total}</div></div>'
        f'<div class="stat-card"><div class="stat-label">Correct Signals</div>'
        f'<div class="stat-value" style="color:#44bb44">{correct}</div></div>'
        f'<div class="stat-card"><div class="stat-label">Wrong Signals</div>'
        f'<div class="stat-value" style="color:#cc0000">{total-correct}</div></div>'
        f'</div>')
    html+='<div style="margin-bottom:12px"><label style="color:#aaa">Filter by stock: </label>'
    html+='<select id="histStockFilter" onchange="filterHistory()" style="background:#1e1e3a;color:#ccc;border:1px solid #444;padding:5px;border-radius:6px;margin-left:8px">'
    html+='<option value="ALL">All Stocks</option>'
    for ticker in sorted(signal_history.keys()):
        html+=f'<option value="{ticker}">{ticker}</option>'
    html+='</select></div>'
    html+='<table class="holdings-table" id="historyTable"><thead><tr>'
    html+='<th>Date</th><th>Ticker</th><th>Signal</th><th>Score</th><th>Price</th>'
    html+='<th>Entry</th><th>Stop</th><th>Target</th><th>Next Day Move</th><th>Outcome</th>'
    html+='</tr></thead><tbody id="historyBody">'
    rows_data=[]
    for ticker, entries in signal_history.items():
        by_stock=accuracy.get("by_stock",{}).get(ticker,{}) if accuracy else {}
        for e in reversed(entries[-30:]):
            outcome=e.get("outcome","PENDING")
            out_color="#44bb44" if outcome=="CORRECT" else "#cc0000" if outcome=="WRONG" else "#888"
            actual=e.get("actual_next_day_pct")
            actual_str=f"{actual:+.2f}%" if actual is not None else "PENDING"
            actual_color="#44bb44" if (actual or 0)>0 else "#cc0000" if (actual or 0)<0 else "#888"
            entry_v=e.get("entry_price"); stop_v=e.get("stop_loss"); tgt_v=e.get("take_profit")
            rows_data.append((e.get("date",""),ticker,
                f'<span style="font-size:11px;padding:2px 8px;border-radius:4px;{signal_style(e.get("recommendation","?"))}">{e.get("recommendation","?")}</span>',
                f'{e.get("blended_score",0):.0f}',
                f'${e.get("price",0):.3f}',
                f'${entry_v:.3f}' if entry_v else '—',
                f'${stop_v:.3f}' if stop_v else '—',
                f'${tgt_v:.3f}' if tgt_v else '—',
                f'<span style="color:{actual_color}">{actual_str}</span>',
                f'<span style="color:{out_color}">{outcome}</span>',
            ))
    rows_data.sort(key=lambda x: (x[0], int(x[3] or 0)), reverse=True)
    current_date=None
    for rd in rows_data:
        if rd[0]!=current_date:
            current_date=rd[0]
            html+=f'<tr><td colspan="10" style="background:#0a0a15;color:#4a90d9;font-weight:bold;padding:6px 12px;font-size:12px;letter-spacing:1px">{current_date}</td></tr>'
        html+=f'<tr data-ticker="{rd[1]}">'+''.join(f'<td>{v}</td>' for v in rd)+'</tr>'
    html+='</tbody></table>'
    return html

def build_dashboard(results, portfolio, output_path, signal_history=None, accuracy=None, intraday=None, quant=None, macro=None, cycle=None):
    today=datetime.now().strftime("%d %B %Y, %H:%M")
    cards_html="\n".join(build_stock_card(r) for r in results)
    stock_advice={r["ticker"]:{"rec":r["reasoning"].get("recommendation",""),"score":r["reasoning"].get("blended_score",0)} for r in results}
    portfolio_html=build_portfolio_html(portfolio, stock_advice)
    signal_history_html=_build_signal_history_html(signal_history or {}, accuracy or {})
    buys=sum(1 for r in results if "BUY" in r["reasoning"].get("recommendation",""))
    holds=sum(1 for r in results if "HOLD" in r["reasoning"].get("recommendation",""))
    avoids=len(results)-buys-holds
    real=portfolio.get("real",{}); holdings_json=json.dumps(real.get("holdings",[]))
    total=len(results)
    # Surfaced on the Market Analysis landing tab too (not just Portfolio) -- the money
    # figure people actually open the dashboard to check shouldn't be a tab away.
    port_value=real.get("total_value",0); port_pnl=real.get("total_pnl",0)
    port_pnl_pct=real.get("total_pnl_pct",0)
    port_pnl_color="#44bb44" if port_pnl>=0 else "#cc0000"
    port_pnl_arrow="▲ " if port_pnl>=0 else "▼ "
    port_pnl_prefix="+" if port_pnl>=0 else ""
    overall_acc=(accuracy or {}).get("overall_accuracy",0)

    # Chart data — per ticker JSON blob
    chart_data_map={r["ticker"]: r.get("chart_data",{}) for r in results if r.get("chart_data")}
    chart_data_json=json.dumps(chart_data_map)

    # Trade Ideas — suggested entries for manual (not automated) paper trading.
    # Reuses buy_sell_reasoning.py's already-computed entry/stop/target per ticker;
    # no new analysis, just surfaces BUY-rated tickers for the user to act on or not.
    suggestions=[]
    for r in results:
        rec=r.get("reasoning",{})
        if not rec.get("recommendation","").startswith(("STRONG", "BUY")):
            continue
        suggestions.append({
            "ticker": r["ticker"], "name": r.get("name", r["ticker"]),
            "price": rec.get("price"), "recommendation": rec.get("recommendation"),
            "rec_color": rec.get("rec_color"), "blended_score": rec.get("blended_score"),
            "confidence": rec.get("confidence"), "timing": rec.get("timing"),
            "reasons": rec.get("reasons", [])[:6],
            "entry_price": rec.get("entry_price"), "entry_type": rec.get("entry_type"),
            "stop_loss": rec.get("stop_loss"), "stop_note": rec.get("stop_note"),
            "take_profit": rec.get("take_profit"), "risk_reward": rec.get("risk_reward"),
        })
    suggestions.sort(key=lambda s: s.get("blended_score") or 0, reverse=True)
    suggestions_json=json.dumps(suggestions)

    # ASX scan results (if available)
    BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    asx_scan_file=os.path.join(BASE,"data","asx_scan_results.json")
    if os.path.exists(asx_scan_file):
        with open(asx_scan_file) as f:
            asx_scan=json.load(f)
    else:
        asx_scan={"results":[],"scanned_at":"Not yet run","total_scanned":0}
    asx_scan_json=json.dumps(asx_scan)

    # Quantitative results
    quant_file=os.path.join(BASE,"data","quant_results.json")
    quant_json=json.dumps({"results":{},"tickers":[]})
    if os.path.exists(quant_file):
        with open(quant_file) as f:
            quant_json=json.dumps(json.load(f))

    # Watchlist
    watchlist_file=os.path.join(BASE,"data","watchlist.json")
    if os.path.exists(watchlist_file):
        with open(watchlist_file) as f:
            watchlist=json.load(f)
    else:
        watchlist={"asx":[],"nasdaq":[],"etf":[]}
    watchlist_json=json.dumps(watchlist)

    # Signal history per ticker for backtest
    history_json=json.dumps(signal_history or {})
    accuracy_json=json.dumps(accuracy or {})

    # Parse macro for template vars
    try:
        _m=macro or {}
        macro_composite=_m.get("composite",50)
        macro_zone=_m.get("zone","—")
        macro_zone_color=_m.get("zone_color","#888")
    except Exception:
        macro_composite=50; macro_zone="—"; macro_zone_color="#888"

    CSS="""<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#0f0f1a;color:#e0e0e0}
header{background:linear-gradient(135deg,#1a1a2e,#16213e);padding:20px 30px;display:flex;justify-content:space-between;align-items:center}
header h1{color:white;font-size:24px}header p{color:#aaa;font-size:13px}
.tab-nav{display:flex;align-items:flex-start;background:#13132a;border-bottom:2px solid #2a2a4a;padding:0 20px;flex-wrap:wrap}
.tab-btn{padding:12px 18px;cursor:pointer;font-size:13px;color:#888;border:none;background:none;border-bottom:3px solid transparent;margin-bottom:-2px;transition:all 0.2s}
.tab-btn:hover{color:#ccc}.tab-btn.active{color:#4a90d9;border-bottom-color:#4a90d9;font-weight:bold}
/* Grouped nav -- 5 sections instead of 15 flat tabs. Each group is a dropdown;
   clicking a child still calls the same showTab(id) as before, so tab content,
   ids, and every existing onclick="showTab('...')" reference keep working
   unchanged -- only how you get to them changed. */
.nav-group{position:relative}
.nav-group-btn{padding:12px 18px;cursor:pointer;font-size:13px;color:#888;border:none;background:none;border-bottom:3px solid transparent;margin-bottom:-2px;transition:all 0.2s;display:flex;align-items:center;gap:5px;font-family:inherit}
.nav-group-btn:hover{color:#ccc}
.nav-group-btn.active{color:#4a90d9;border-bottom-color:#4a90d9;font-weight:bold}
.nav-group-btn .caret{font-size:9px;transition:transform 0.15s}
.nav-group.open .nav-group-btn .caret{transform:rotate(180deg)}
.nav-dropdown{display:none;flex-direction:column;position:absolute;top:100%;left:0;background:#1a1a2e;border:1px solid #2a2a4a;border-radius:0 0 8px 8px;min-width:180px;z-index:50;padding:6px;box-shadow:0 8px 20px rgba(0,0,0,0.4)}
.nav-group.open .nav-dropdown{display:flex}
.nav-dropdown .tab-btn{text-align:left;border-bottom:none;border-radius:6px;padding:9px 14px;margin-bottom:0}
.nav-dropdown .tab-btn:hover{background:#22223f}
.nav-dropdown .tab-btn.active{background:#152238}
.tab-content{display:none}.tab-content.active{display:block}
.section{padding:25px 30px}.section h2{color:#fff;margin-bottom:15px;font-size:18px}
.filter-bar{display:flex;gap:10px;padding:15px 30px;background:#13132a;flex-wrap:wrap;align-items:center}
.filter-btn{padding:6px 16px;border-radius:20px;border:1px solid #444;cursor:pointer;font-size:13px;background:#1e1e3a;color:#ccc;transition:all 0.2s}
.filter-btn.active{background:#4a90d9;color:white;border-color:#4a90d9}.filter-btn:hover{background:#2a2a5a}
input[type=text],input[type=number],input[type=date],select{background:#1e1e3a;color:#ccc;border:1px solid #444;border-radius:6px;padding:6px 12px;font-size:13px}
input[type=range]{width:200px;accent-color:#4a90d9}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:15px;margin-bottom:20px}
.stat-card{background:#1a1a2e;border-radius:10px;padding:15px;text-align:center}
.stat-label{font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:5px}
.stat-value{font-size:20px;font-weight:bold;color:white}
.cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:18px;padding:0 30px 30px}
.stock-card{background:#1a1a2e;border-radius:12px;overflow:hidden;border:1px solid #2a2a4a;transition:transform 0.2s}
.stock-card:hover{transform:translateY(-2px);border-color:#4a90d9}
.card-header{padding:12px 16px;display:flex;justify-content:space-between;align-items:center}
.ticker{font-size:18px;font-weight:bold;margin-right:8px}
.company-name{font-size:12px;opacity:0.8}
.rec-badge{font-size:11px;padding:2px 8px;border-radius:4px;background:rgba(0,0,0,0.3);margin-right:6px}
.score-badge{font-size:14px;font-weight:bold}
.card-body{padding:14px 16px}
.price-row{display:flex;gap:12px;align-items:baseline;margin-bottom:8px}
.price{font-size:20px;font-weight:bold;color:white}
.rsi-badge{font-size:11px;padding:2px 8px;background:#1e1e3a;border-radius:10px;color:#aaa;margin-left:auto}
.score-breakdown{font-size:11px;color:#888;margin-bottom:10px}
.trade-grid{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;background:#0f0f1a;padding:10px;border-radius:8px;margin-bottom:10px}
.trade-grid label{font-size:10px;color:#888;display:block;margin-bottom:2px}
.trade-grid strong{font-size:13px}
.timing{font-size:11px;color:#aaa;margin:6px 0}
.cycle-block{font-size:11px;color:#aaa;background:#0f0f1a;padding:6px 10px;border-radius:6px;margin:6px 0;border-left:3px solid #4a90d9}
.corr-block{font-size:11px;color:#aaa;background:#0f0f1a;padding:6px 10px;border-radius:6px;margin:6px 0;border-left:3px solid #ff9900}
.alert-card{font-size:12px;color:#eee;background:#1a1a2e;border:1px solid #2a2a4a;border-left:4px solid #cc0000;border-radius:8px;padding:12px 16px;margin-bottom:10px}
.alert-card.warn{border-left-color:#ff9900}
.alert-card .alert-ticker{font-weight:bold;font-size:14px;margin-right:8px}
.alert-card .alert-detail{color:#aaa;margin-top:4px;font-size:11px}
details summary{cursor:pointer;color:#4a90d9;font-size:12px;margin-top:8px;padding:4px 0}
.reasons{padding-left:16px;font-size:12px;color:#aaa;margin-top:6px}
.reasons li{margin-bottom:3px}
.holdings-table{width:100%;border-collapse:collapse;font-size:13px}
.holdings-table th{background:#0f0f1a;color:#888;padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase}
.holdings-table td{padding:10px 12px;border-bottom:1px solid #1e1e3a}
.holdings-table tr:hover td{background:#1e1e3a}
.btn-remove{padding:3px 10px;background:#3a0000;border:1px solid #cc0000;color:#ff6666;border-radius:4px;cursor:pointer;font-size:11px}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:15px;max-width:600px}
.form-group{display:flex;flex-direction:column;gap:5px}
.form-group label{font-size:12px;color:#aaa;text-transform:uppercase}
.form-group input,.form-group select{width:100%}
.btn-primary{background:linear-gradient(135deg,#1a6b3c,#0d4a2a);color:white;border:none;padding:10px 24px;border-radius:8px;cursor:pointer;font-size:14px;margin-top:10px}
.btn-primary:hover{background:linear-gradient(135deg,#22883f,#155c35)}
.btn-secondary{background:#1e1e3a;color:#ccc;border:1px solid #444;padding:8px 18px;border-radius:8px;cursor:pointer;font-size:13px}
.btn-secondary:hover{background:#2a2a4a}
.btn-add-watch{padding:3px 10px;background:#0d2a4a;border:1px solid #4a90d9;color:#4a90d9;border-radius:4px;cursor:pointer;font-size:11px}
.token-section{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:10px;padding:20px;max-width:550px;margin-bottom:25px}
.token-section h3{color:#fff;margin-bottom:10px;font-size:15px}
.asx-table{width:100%;border-collapse:collapse;font-size:13px}
.asx-table th{background:#0f0f1a;color:#888;padding:8px 10px;text-align:left;font-size:11px;text-transform:uppercase;position:sticky;top:0}
.asx-table td{padding:8px 10px;border-bottom:1px solid #1a1a2e}
.asx-table tr:hover td{background:#1e1e3a}
.asx-table-wrap{max-height:600px;overflow-y:auto}
.watchlist-chips{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.chip{background:#1e1e3a;border:1px solid #2a2a4a;border-radius:20px;padding:4px 12px;font-size:12px;display:flex;align-items:center;gap:6px}
.chip button{background:none;border:none;color:#cc0000;cursor:pointer;font-size:14px;padding:0}
.backtest-table{width:100%;border-collapse:collapse;font-size:12px}
.backtest-table th{background:#0f0f1a;color:#888;padding:8px 10px;text-align:left;font-size:11px;text-transform:uppercase}
.backtest-table td{padding:8px 10px;border-bottom:1px solid #1a1a2e}
.backtest-table tr:hover td{background:#1e1e3a}
#chartModal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:1000;align-items:center;justify-content:center}
#chartModal.open{display:flex}
#intradayChartModal.open{display:flex}
#chartBox{background:#0f0f1a;border:1px solid #2a2a4a;border-radius:12px;width:90%;max-width:1000px;padding:20px}
#chartBox h3{color:white;margin-bottom:12px}
#chartContainer{height:420px;position:relative}
#rsiContainer{height:120px;position:relative;margin-top:8px}
.close-modal{float:right;background:none;border:none;color:#888;font-size:20px;cursor:pointer}
.accuracy-bar-wrap{height:8px;background:#1e1e3a;border-radius:4px;overflow:hidden;margin-top:6px}
.accuracy-bar{height:100%;background:#44bb44;border-radius:4px}
.quant-subnav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;padding-bottom:15px;border-bottom:1px solid #2a2a4a}
.quant-btn{padding:6px 14px;border-radius:20px;border:1px solid #444;cursor:pointer;font-size:12px;background:#1e1e3a;color:#ccc;transition:all 0.2s}
.quant-btn:hover{background:#2a2a5a}.quant-btn.active{background:#4a90d9;color:white;border-color:#4a90d9}
#intradayChartModal.open{display:flex}
</style>"""

    JS=r"""<script>
// ── Data from nightly Python run ─────────────────────────────────────────────
const CHART_DATA = __CHART_DATA__;
const ASX_SCAN = __ASX_SCAN__;
const WATCHLIST = __WATCHLIST__;
const SIGNAL_HISTORY = __SIGNAL_HISTORY__;
const ACCURACY = __ACCURACY__;

// ── Tab switching ─────────────────────────────────────────────────────────────
// Nav dropdowns -- only one open at a time, closes on outside click or once a
// tab inside it is picked (see showTab below).
function toggleNavGroup(name){
    const g=document.getElementById('navgroup-'+name);
    const wasOpen=g.classList.contains('open');
    document.querySelectorAll('.nav-group').forEach(x=>x.classList.remove('open'));
    if(!wasOpen) g.classList.add('open');
}
document.addEventListener('click', function(e){
    if(!e.target.closest('.nav-group')) document.querySelectorAll('.nav-group').forEach(x=>x.classList.remove('open'));
});

function showTab(id) {
    document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.nav-group-btn').forEach(b=>b.classList.remove('active'));
    document.getElementById('tab-'+id).classList.add('active');
    const btn=document.querySelector(`[onclick="showTab('${id}')"]`);
    btn.classList.add('active');
    const group=btn.closest('.nav-group');
    if(group){ group.querySelector('.nav-group-btn').classList.add('active'); group.classList.remove('open'); }
    if(id==='agent') loadAgentTrades();
    if(id==='market_status') renderMacroGate();
    if(id==='asx') renderASXTable();
    if(id==='watchlist') renderWatchlist();
    if(id==='backtest') populateBacktestSelect();
    if(id==='history') { /* already rendered server-side */ }
    if(id==='intraday') renderIntradayTable();
    if(id==='portfolio') refreshPortfolioPrices();
    if(id==='quantitative') renderQuantTab(window._activeQuantSection||'earnings');
    if(id==='cycle') renderCycleTab();
    if(id==='paper') renderPaperTab();
    if(id==='suggestions') renderSuggestionsTab();
    if(id==='token') updateTokenStatus();
}

// ── Market Analysis filters ───────────────────────────────────────────────────
function filterCards(filter) {
    document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
    event.target.classList.add('active');
    const q = document.getElementById('searchBox').value.toLowerCase();
    document.querySelectorAll('.stock-card').forEach(c=>{
        const rec=c.dataset.rec||''; const ticker=c.dataset.ticker||'';
        const scoreMatch = filter==='ALL' || (filter==='BUY'&&rec.includes('BUY')) ||
            (filter==='HOLD'&&rec==='HOLD') || (filter==='AVOID'&&rec.includes('SELL'));
        const searchMatch = !q || ticker.toLowerCase().includes(q);
        c.style.display = scoreMatch&&searchMatch?'':'none';
    });
}
function searchCards() {
    const q=document.getElementById('searchBox').value.toLowerCase();
    document.querySelectorAll('.stock-card').forEach(c=>{
        c.style.display=c.dataset.ticker.toLowerCase().includes(q)?'':'none';
    });
}
function sortCards(by) {
    const grid=document.getElementById('cardsGrid');
    const cards=[...grid.children];
    cards.sort((a,b)=>{
        if(by==='score') return (b.dataset.score||0)-(a.dataset.score||0);
        if(by==='ticker') return (a.dataset.ticker||'').localeCompare(b.dataset.ticker||'');
        return 0;
    });
    cards.forEach(c=>grid.appendChild(c));
}

// ── GitHub API helpers ─────────────────────────────────────────────────────────
const REPO='Borisp2026/trading-analyser-2';
const PORTFOLIO_PATH='data/portfolio.json';
const WATCHLIST_PATH='data/watchlist.json';

function getToken(){return localStorage.getItem('gh_token')||'';}
async function triggerNightlyRun(){
    const token=getToken();
    if(!token){alert('Enter your GitHub token first (Settings \u2192 Token tab).');return;}
    const btn=document.getElementById('nightlyBtn');
    const orig=btn.textContent;
    btn.textContent='Triggering...';
    btn.disabled=true;
    try{
        const r=await fetch('https://api.github.com/repos/Borisp2026/trading-analyser-2/actions/workflows/nightly.yml/dispatches',{
            method:'POST',
            headers:{'Authorization':'token '+token,'Accept':'application/vnd.github.v3+json','Content-Type':'application/json'},
            body:JSON.stringify({ref:'main'})
        });
        if(r.status===204){
            btn.textContent='\u2713 Triggered!';
            setTimeout(()=>{btn.textContent=orig;btn.disabled=false;},5000);
            setTimeout(()=>alert('Workflow started! Data updates in ~3-5 min. Refresh the page after.'),300);
        }else{
            const err=await r.json().catch(()=>({}));
            alert('Error '+r.status+': '+(err.message||'check your token has workflow scope'));
            btn.textContent=orig;btn.disabled=false;
        }
    }catch(e){
        alert('Network error: '+e.message);
        btn.textContent=orig;btn.disabled=false;
    }
}

function saveToken(){
    const t=document.getElementById('ghToken').value.trim();
    if(!t){alert('Paste a token into the box first.');return;}
    localStorage.setItem('gh_token',t);
    document.getElementById('ghToken').value='';
    updateTokenStatus();
    alert('Token saved. Click "Test Token" to confirm it has repo access.');
}
function updateTokenStatus(){
    const el=document.getElementById('tokenStatus');
    if(!el) return;
    const t=getToken();
    el.textContent = t
        ? '✓ Token saved in this browser (ends …'+t.slice(-4)+'). Click "Test Token" to verify it still works.'
        : '⚠ No token saved yet — Buy/Sell and Add Holding will not work until you save one.';
    el.style.color = t ? '#44bb44' : '#ff9900';
}
async function testToken(){
    const el=document.getElementById('tokenStatus');
    if(!getToken()){alert('No token saved yet — paste one above and click Save Token first.');return;}
    if(el){el.textContent='Testing token...';el.style.color='#888';}
    try{
        await ghGet(PORTFOLIO_PATH);
        if(el){el.textContent='✓ Token works — confirmed read access to the repo.';el.style.color='#44bb44';}
    }catch(e){
        if(el){el.textContent='✗ Token test failed: '+e.message+' — check it has the "repo" scope and hasn\'t expired.';el.style.color='#cc0000';}
    }
}

async function ghGet(path){
    const r=await fetch(`https://api.github.com/repos/${REPO}/contents/${path}`,
        {headers:{'Authorization':'token '+getToken(),'Accept':'application/vnd.github.v3+json'}});
    if(!r.ok)throw new Error('GitHub GET failed: '+r.status);
    return r.json();
}
async function ghPut(path,content,sha){
    const r=await fetch(`https://api.github.com/repos/${REPO}/contents/${path}`,{
        method:'PUT',
        headers:{'Authorization':'token '+getToken(),'Accept':'application/vnd.github.v3+json','Content-Type':'application/json'},
        body:JSON.stringify({message:`Update ${path}`,content:btoa(unescape(encodeURIComponent(JSON.stringify(content,null,2)))),sha})
    });
    if(!r.ok){const e=await r.json();throw new Error(e.message||'GitHub PUT failed');}
    return r.json();
}

let _livePricesFile=null;
async function loadLivePricesFile(){
    // Server-side snapshot written every ~30 min by live_prices.py via yfinance
    // (no browser involved, so no CORS issue at all). Read directly, same-origin.
    if(_livePricesFile) return _livePricesFile;
    try{
        const r=await fetch('data/live_prices.json?_='+Date.now());
        _livePricesFile=await r.json();
    }catch(e){ _livePricesFile={prices:{}}; }
    return _livePricesFile;
}
async function fetchLivePrice(ticker){
    // Yahoo Finance sends no CORS headers for third-party sites, so a direct
    // browser fetch is never possible here. The public proxy this used to go
    // through (corsproxy.io) now requires a paid API key and rejects every
    // request; the remaining free-tier alternative (Corsfix) also isn't free
    // for a live site beyond a trial. So this reads the same-origin snapshot
    // written every ~30 min by live_prices.py via yfinance (server-to-server,
    // no CORS involved at all) instead of live-fetching from the browser.
    try{
        const lp=await loadLivePricesFile();
        const p=lp.prices && lp.prices[ticker.toUpperCase()];
        if(p) return p;
    }catch(e){}
    return null;
}
async function refreshPortfolioPrices(){
    const tbody=document.querySelector('#tab-portfolio .holdings-table tbody');
    if(!tbody) return;
    const rows=[...tbody.querySelectorAll('tr')];
    if(!rows.length) return;
    const h2=document.querySelector('#tab-portfolio .section h2');
    let ind=document.getElementById('port-live-ind');
    if(!ind){ind=document.createElement('span');ind.id='port-live-ind';ind.style.cssText='font-size:12px;color:#888;margin-left:12px;';h2.appendChild(ind);}
    ind.textContent='fetching live prices...';
    let totalValue=0,totalCost=0,successCount=0;
    const fetches=rows.map(async row=>{
        const cells=[...row.querySelectorAll('td')];
        if(cells.length<6) return;
        const ticker=cells[0].querySelector('b')?.textContent?.trim();
        const shares=parseFloat(cells[1].textContent.replace(/,/g,''))||0;
        const buyPrice=parseFloat(cells[2].textContent.replace(/[$,]/g,''))||0;
        if(!ticker||!shares) return;
        let price=await fetchLivePrice(ticker);
        if(price===null){
            // Live fetch failed (e.g. the CORS proxy is down/rate-limited) -- fall back
            // to whatever's already shown (the nightly-baked value, or a prior successful
            // refresh) instead of dropping this holding out of the totals below, which
            // would otherwise wrongly zero out Portfolio Value/P&L when every fetch fails.
            price=parseFloat(cells[3].textContent.replace(/[$,]/g,''))||null;
        }else{
            successCount++;
        }
        if(price===null) return;
        const value=price*shares;
        const cost=buyPrice*shares;
        const pl=value-cost;
        const plPct=cost>0?((pl/cost)*100):0;
        totalValue+=value;
        totalCost+=cost;
        cells[3].textContent='$'+price.toFixed(3);
        cells[4].textContent='$'+value.toLocaleString('en-AU',{minimumFractionDigits:2,maximumFractionDigits:2});
        cells[5].style.color=pl>=0?'green':'red';
        cells[5].textContent=(pl>=0?'+':'')+' $'+Math.abs(pl).toLocaleString('en-AU',{minimumFractionDigits:2,maximumFractionDigits:2})+' ('+(pl>=0?'+':'')+plPct.toFixed(1)+'%)';
    });
    await Promise.all(fetches);
    const cards=[...document.querySelectorAll('#tab-portfolio .stats-grid .stat-value')];
    if(cards.length>=3 && totalCost>0){
        cards[0].textContent='$'+totalValue.toLocaleString('en-AU',{minimumFractionDigits:2,maximumFractionDigits:2});
        const totalPL=totalValue-totalCost;
        const pct=totalCost>0?((totalPL/totalCost)*100):0;
        cards[2].style.color=totalPL>=0?'green':'red';
        cards[2].textContent=(totalPL>=0?'+':'')+' $'+Math.abs(totalPL).toLocaleString('en-AU',{minimumFractionDigits:2,maximumFractionDigits:2})+' ('+(totalPL>=0?'+':'')+pct.toFixed(1)+'%)';
    }
    ind.textContent = successCount>0
        ? 'live as of '+new Date().toLocaleTimeString('en-AU',{hour:'2-digit',minute:'2-digit'})+(successCount<rows.length?' ('+successCount+'/'+rows.length+' updated)':'')
        : 'live price fetch unavailable — showing last known values';
}
setInterval(()=>{if(document.getElementById('tab-portfolio')?.classList.contains('active')) refreshPortfolioPrices();},15*60*1000);
async function readPortfolio(){
    const f=await ghGet(PORTFOLIO_PATH);
    return {data:JSON.parse(atob(f.content)),sha:f.sha};
}
async function writePortfolio(data,sha){return ghPut(PORTFOLIO_PATH,data,sha);}
async function readWatchlistGH(){
    const f=await ghGet(WATCHLIST_PATH);
    return {data:JSON.parse(atob(f.content)),sha:f.sha};
}
async function writeWatchlistGH(data,sha){return ghPut(WATCHLIST_PATH,data,sha);}

// ── Portfolio: Add / Remove holding ──────────────────────────────────────────
async function addHolding(){
    const ticker=document.getElementById('h_ticker').value.toUpperCase().trim();
    const shares=parseFloat(document.getElementById('h_shares').value);
    const price=parseFloat(document.getElementById('h_price').value);
    const date=document.getElementById('h_date').value;
    if(!ticker||!shares||!price){alert('Fill in ticker, shares and buy price.');return;}
    const type=document.getElementById('h_type').value;
    try{
        const {data,sha}=await readPortfolio();
        const holding={ticker,shares,buy_price:price,buy_date:date,type,added:new Date().toISOString()};
        (data.holdings=data.holdings||[]).push(holding);
        await writePortfolio(data,sha);
        alert(`${ticker} added. Dashboard will refresh after next nightly run.`);
    }catch(e){alert('Error: '+e.message);}
}
async function removeHolding(ticker){
    if(!confirm(`Remove ${ticker} from portfolio?`))return;
    try{
        const {data,sha}=await readPortfolio();
        data.holdings=(data.holdings||[]).filter(h=>h.ticker!==ticker);
        await writePortfolio(data,sha);
        alert(`${ticker} removed.`);location.reload();
    }catch(e){alert('Error: '+e.message);}
}
async function addPaperTrade(){
    const ticker=document.getElementById('pt_ticker').value.toUpperCase().trim();
    const direction=document.getElementById('pt_direction').value;
    const entry=parseFloat(document.getElementById('pt_entry').value);
    const qty=parseFloat(document.getElementById('pt_qty').value);
    const stop=parseFloat(document.getElementById('pt_stop').value)||null;
    const target=parseFloat(document.getElementById('pt_target').value)||null;
    if(!ticker||!entry||!qty){alert('Fill in ticker, entry price and quantity.');return;}
    try{
        const {data,sha}=await readPortfolio();
        const trade={ticker,direction,entry_price:entry,qty,stop_loss:stop,take_profit:target,opened:new Date().toISOString(),status:'open'};
        (data.paper_trades=data.paper_trades||[]).push(trade);
        await writePortfolio(data,sha);
        alert(`Paper trade added for ${ticker}.`);
    }catch(e){alert('Error: '+e.message);}
}
async function closePaperTrade(idx){
    const exit=parseFloat(prompt('Exit price?'));
    if(!exit)return;
    try{
        const {data,sha}=await readPortfolio();
        const t=data.paper_trades[idx];
        t.exit_price=exit;t.closed=new Date().toISOString();t.status='closed';
        const mult=t.direction==='LONG'?1:-1;
        t.pnl=mult*(exit-t.entry_price)*t.qty;
        await writePortfolio(data,sha);
        alert(`Trade closed. P&L: $${t.pnl.toFixed(2)}`);location.reload();
    }catch(e){alert('Error: '+e.message);}
}

// ── Watchlist Manager ─────────────────────────────────────────────────────────
let _watchlistCache=JSON.parse(JSON.stringify(WATCHLIST));
function renderWatchlist(){
    const wl=_watchlistCache;
    ['asx','nasdaq','etf'].forEach(cat=>{
        const el=document.getElementById('wl_'+cat);
        if(!el)return;
        el.innerHTML=(wl[cat]||[]).map(t=>
            `<span class="chip">${t}<button onclick="removeFromWatchlist('${cat}','${t}')" title="Remove">&times;</button></span>`
        ).join('');
    });
}
function removeFromWatchlist(cat,ticker){
    _watchlistCache[cat]=(_watchlistCache[cat]||[]).filter(t=>t!==ticker);
    renderWatchlist();
}
function addToWatchlistLocal(){
    const ticker=document.getElementById('wl_new_ticker').value.toUpperCase().trim();
    const cat=document.getElementById('wl_new_cat').value;
    if(!ticker)return;
    if(!(_watchlistCache[cat]||[]).includes(ticker)){
        (_watchlistCache[cat]=_watchlistCache[cat]||[]).push(ticker);
        renderWatchlist();
    }
    document.getElementById('wl_new_ticker').value='';
}
async function saveWatchlist(){
    if(!getToken()){alert('Enter your GitHub token first (Token tab).');return;}
    try{
        const {data,sha}=await readWatchlistGH();
        data.asx=_watchlistCache.asx||[];
        data.nasdaq=_watchlistCache.nasdaq||[];
        data.etf=_watchlistCache.etf||[];
        await writeWatchlistGH(data,sha);
        alert('Watchlist saved. Changes take effect on next nightly run.');
    }catch(e){alert('Error: '+e.message);}
}
async function addToWatchlistFromScan(ticker){
    const cat=ticker.endsWith('.AX')?'asx':'nasdaq';
    if(!(_watchlistCache[cat]||[]).includes(ticker)){
        (_watchlistCache[cat]=_watchlistCache[cat]||[]).push(ticker);
    }
    if(!getToken()){alert('Ticker added locally. Go to Watchlist tab and click Save to push to GitHub.');return;}
    try{
        const {data,sha}=await readWatchlistGH();
        if(!(data[cat]||[]).includes(ticker)){
            (data[cat]=data[cat]||[]).push(ticker);
            await writeWatchlistGH(data,sha);
            alert(`${ticker} added to watchlist and saved.`);
        }else{alert(`${ticker} is already in the watchlist.`);}
    }catch(e){alert('Saved locally only. Push via Watchlist tab. ('+e.message+')');}
}

// ── ASX Scanner tab ───────────────────────────────────────────────────────────
function renderASXTable(){
    const data=ASX_SCAN.results||[];
    const minScore=parseInt(document.getElementById('asxMinScore').value)||0;
    const q=(document.getElementById('asxSearch').value||'').toLowerCase();
    const filtered=data.filter(r=>{
        const s=r.reasoning?.blended_score||0;
        const t=(r.ticker||'').toLowerCase();
        const n=(r.name||'').toLowerCase();
        return s>=minScore&&(!q||t.includes(q)||n.includes(q));
    });
    document.getElementById('asxCount').textContent=`${filtered.length} of ${data.length} stocks`;
    const tbody=document.getElementById('asxBody');
    tbody.innerHTML=filtered.map(r=>{
        const rec=r.reasoning||{};
        const t=r.tech||{};
        const s=rec.blended_score||0;
        const sc=s>=70?'#44bb44':s>=50?'#ff9900':'#cc0000';
        const p1d=t.price_1d_pct||0;
        const pc=p1d>=0?'#44bb44':'#cc0000';
        return `<tr>
            <td><b>${r.ticker}</b></td>
            <td style="font-size:11px;color:#aaa">${(r.name||'').substring(0,28)}</td>
            <td><span style="color:${sc};font-weight:bold">${s.toFixed(0)}</span></td>
            <td><span style="padding:2px 8px;border-radius:4px;font-size:11px;${signalStyleJS(rec.recommendation||'')}">${rec.recommendation||'?'}</span></td>
            <td>$${(t.price||0).toFixed(3)}</td>
            <td style="color:${pc}">${p1d>=0?'+':''}${p1d.toFixed(1)}%</td>
            <td>${(t.rsi||0).toFixed(0)}</td>
            <td style="color:green">${rec.entry_price?'$'+rec.entry_price.toFixed(3):'—'}</td>
            <td style="color:red">${rec.stop_loss?'$'+rec.stop_loss.toFixed(3):'—'}</td>
            <td style="color:#44bb44">${rec.take_profit?'$'+rec.take_profit.toFixed(3):'—'}</td>
            <td><button class="btn-add-watch" onclick="addToWatchlistFromScan('${r.ticker}')">+ Watch</button></td>
        </tr>`;
    }).join('');
}
function signalStyleJS(rec){
    if(rec.includes('STRONG BUY'))return 'background:#00aa00;color:white;';
    if(rec.includes('BUY'))return 'background:#44bb44;color:white;';
    if(rec.includes('HOLD'))return 'background:#ff9900;color:white;';
    if(rec.includes('WEAK'))return 'background:#ff6600;color:white;';
    return 'background:#cc0000;color:white;';
}
function updateScoreLabel(){
    const v=document.getElementById('asxMinScore').value;
    document.getElementById('asxScoreLabel').textContent=v+'%+';
    renderASXTable();
}

// ── Backtest tab ──────────────────────────────────────────────────────────────
function populateBacktestSelect(){
    const sel=document.getElementById('btStockSelect');
    if(!sel)return;
    const current=sel.value;
    sel.innerHTML='<option value="">Select a stock...</option>';
    Object.keys(SIGNAL_HISTORY).sort().forEach(t=>{
        const o=document.createElement('option');
        o.value=t;o.textContent=t;
        sel.appendChild(o);
    });
    if(current)sel.value=current;
}
function runBacktest(){
    const ticker=document.getElementById('btStockSelect').value;
    if(!ticker){alert('Select a stock first.');return;}
    const entries=SIGNAL_HISTORY[ticker]||[];
    // NEUTRAL (HOLD/WATCH) made no directional call -- exclude from accuracy, same as the server-side calc.
    const resolved=entries.filter(e=>e.outcome==='CORRECT'||e.outcome==='WRONG');
    const correct=resolved.filter(e=>e.signal_correct).length;
    const accuracy=resolved.length?((correct/resolved.length)*100).toFixed(1):0;
    const accColor=accuracy>=60?'#44bb44':accuracy>=50?'#ff9900':'#cc0000';

    let html=`<div class="stats-grid" style="margin-bottom:20px">
        <div class="stat-card"><div class="stat-label">Accuracy</div><div class="stat-value" style="color:${accColor}">${accuracy}%</div></div>
        <div class="stat-card"><div class="stat-label">Total Signals</div><div class="stat-value">${resolved.length}</div></div>
        <div class="stat-card"><div class="stat-label">Correct</div><div class="stat-value" style="color:#44bb44">${correct}</div></div>
        <div class="stat-card"><div class="stat-label">Wrong</div><div class="stat-value" style="color:#cc0000">${resolved.length-correct}</div></div>
    </div>`;

    if(resolved.length===0){
        html+='<p style="color:#888">No resolved signals yet. History builds up over time as each nightly recommendation is compared with the next day\'s actual move.</p>';
    } else {
        html+=`<table class="backtest-table"><thead><tr>
            <th>Date</th><th>Signal</th><th>Score</th><th>Price</th>
            <th>Entry</th><th>Stop</th><th>Target</th>
            <th>Next Day</th><th>Outcome</th><th>Notes</th>
        </tr></thead><tbody>`;
        [...resolved].reverse().forEach(e=>{
            const oc=e.signal_correct?'#44bb44':'#cc0000';
            const ac=(e.actual_next_day_pct||0)>=0?'#44bb44':'#cc0000';
            const predicted=e.recommendation.includes('BUY')?'UP':'DOWN';
            const actual=e.actual_direction||'?';
            const note=e.signal_correct?'Direction correct'
                :`Predicted ${predicted}, actually went ${actual}. `+
                (Math.abs(e.actual_next_day_pct||0)<0.3?'Minimal movement — neutral day.':'Strong counter-move.');
            html+=`<tr>
                <td>${e.date}</td>
                <td><span style="padding:2px 8px;border-radius:4px;font-size:11px;${signalStyleJS(e.recommendation)}">${e.recommendation}</span></td>
                <td>${(e.blended_score||0).toFixed(0)}</td>
                <td>$${(e.price||0).toFixed(3)}</td>
                <td>${e.entry_price?'$'+e.entry_price.toFixed(3):'—'}</td>
                <td>${e.stop_loss?'$'+e.stop_loss.toFixed(3):'—'}</td>
                <td>${e.take_profit?'$'+e.take_profit.toFixed(3):'—'}</td>
                <td style="color:${ac}">${e.actual_next_day_pct!=null?(e.actual_next_day_pct>=0?'+':'')+e.actual_next_day_pct.toFixed(2)+'%':'PENDING'}</td>
                <td style="color:${oc};font-weight:bold">${e.outcome}</td>
                <td style="font-size:11px;color:#888">${note}</td>
            </tr>`;
        });
        html+='</tbody></table>';
    }
    document.getElementById('btResults').innerHTML=html;
}

// ── Signal History filter ─────────────────────────────────────────────────────
function filterHistory(){
    const val=document.getElementById('histStockFilter').value;
    document.querySelectorAll('#historyBody tr').forEach(row=>{
        row.style.display=val==='ALL'||row.dataset.ticker===val?'':'none';
    });
}

// ── Chart modal (lightweight-charts from CDN) ─────────────────────────────────
let _chart=null,_candleSeries=null,_rsiChart=null;
function showChart(ticker,overlay){
    const data=CHART_DATA[ticker];
    if(!data||!data.candles||!data.candles.length){alert('No chart data for '+ticker);return;}
    document.getElementById('chartTitle').textContent=ticker+' — 90 Day Chart'+(overlay?' — Cycle Trading':'');
    document.getElementById('chartModal').classList.add('open');
    setTimeout(()=>renderChart(data,overlay),50);
}
function closeChartModal(){
    document.getElementById('chartModal').classList.remove('open');
    if(_chart){_chart.remove();_chart=null;}
    if(_rsiChart){_rsiChart.remove();_rsiChart=null;}
}
function renderChart(data,overlay){
    const container=document.getElementById('chartContainer');
    const rsiContainer=document.getElementById('rsiContainer');
    container.innerHTML='';rsiContainer.innerHTML='';
    if(typeof LightweightCharts==='undefined'){
        container.innerHTML='<p style="color:#888;padding:20px">Chart library not loaded. Check internet connection.</p>';
        return;
    }
    _chart=LightweightCharts.createChart(container,{
        width:container.clientWidth,height:380,
        layout:{background:{color:'#0f0f1a'},textColor:'#888'},
        grid:{vertLines:{color:'#1a1a2e'},horzLines:{color:'#1a1a2e'}},
        crosshair:{mode:LightweightCharts.CrosshairMode.Normal},
        timeScale:{timeVisible:true,secondsVisible:false},
    });
    _candleSeries=_chart.addCandlestickSeries({upColor:'#44bb44',downColor:'#cc0000',borderVisible:false,wickUpColor:'#44bb44',wickDownColor:'#cc0000'});
    _candleSeries.setData(data.candles);
    if(data.sma20&&data.sma20.length){
        const s=_chart.addLineSeries({color:'#ff9900',lineWidth:1,title:'SMA20'});
        s.setData(data.sma20);
    }
    if(data.sma50&&data.sma50.length){
        const s=_chart.addLineSeries({color:'#cc88ff',lineWidth:1,lineStyle:2,title:'SMA50'});
        s.setData(data.sma50);
    }
    if(data.bb_upper&&data.bb_upper.length){
        const u=_chart.addLineSeries({color:'rgba(74,144,217,0.4)',lineWidth:1,title:'BB Upper'});
        u.setData(data.bb_upper);
        const l=_chart.addLineSeries({color:'rgba(74,144,217,0.4)',lineWidth:1,title:'BB Lower'});
        l.setData(data.bb_lower);
    }
    if(data.volume&&data.volume.length){
        const vs=_chart.addHistogramSeries({color:'rgba(74,144,217,0.3)',priceFormat:{type:'volume'},priceScaleId:'vol',scaleMargins:{top:0.8,bottom:0}});
        vs.setData(data.volume);
    }
    // RSI panel
    if(data.rsi&&data.rsi.length){
        _rsiChart=LightweightCharts.createChart(rsiContainer,{
            width:rsiContainer.clientWidth,height:100,
            layout:{background:{color:'#0f0f1a'},textColor:'#888'},
            grid:{vertLines:{color:'#1a1a2e'},horzLines:{color:'#1a1a2e'}},
            timeScale:{visible:false},rightPriceScale:{scaleMargins:{top:0.1,bottom:0.1}},
        });
        const rs=_rsiChart.addLineSeries({color:'#4a90d9',lineWidth:1,title:'RSI'});
        rs.setData(data.rsi);
        const ob=_rsiChart.addLineSeries({color:'rgba(204,0,0,0.4)',lineWidth:1,lineStyle:2});
        ob.setData(data.rsi.map(d=>({time:d.time,value:70})));
        const os=_rsiChart.addLineSeries({color:'rgba(68,187,68,0.4)',lineWidth:1,lineStyle:2});
        os.setData(data.rsi.map(d=>({time:d.time,value:30})));
        _chart.timeScale().subscribeVisibleTimeRangeChange(r=>{if(r&&_rsiChart)_rsiChart.timeScale().setVisibleRange(r);});
    }
    // Cycle Trading overlay: support/resistance band, DCL/HCH/HCL/DCH markers, entry/stop/target
    if(overlay){
        const toTime=d=>Math.floor(new Date(d+'T00:00:00Z').getTime()/1000);
        const asSeries=pts=>(pts||[]).filter(p=>p.date&&p.price!=null).map(p=>({time:toTime(p.date),value:p.price}));
        if(overlay.daily_support_line&&overlay.daily_support_line.length>=2){
            const s=_chart.addLineSeries({color:'#4a90d9',lineWidth:2,title:'Daily Support'});
            s.setData(asSeries(overlay.daily_support_line));
        }
        if(overlay.daily_resistance_line&&overlay.daily_resistance_line.length>=2){
            const s=_chart.addLineSeries({color:'#ff9900',lineWidth:2,title:'Daily Resistance'});
            s.setData(asSeries(overlay.daily_resistance_line));
        }
        if(overlay.intermediate_support_line&&overlay.intermediate_support_line.length>=2){
            const s=_chart.addLineSeries({color:'rgba(74,144,217,0.45)',lineWidth:1,lineStyle:2,title:'IC Support'});
            s.setData(asSeries(overlay.intermediate_support_line));
        }
        if(overlay.intermediate_resistance_line&&overlay.intermediate_resistance_line.length>=2){
            const s=_chart.addLineSeries({color:'rgba(255,153,0,0.45)',lineWidth:1,lineStyle:2,title:'IC Resistance'});
            s.setData(asSeries(overlay.intermediate_resistance_line));
        }
        const markers=[];
        const mk=(m,label,color,shape,position)=>{ if(m&&m.date&&m.price!=null) markers.push({time:toTime(m.date),position:position,color:color,shape:shape,text:label}); };
        const dm=overlay.daily_markers||{};
        mk(dm.dcl0,'DCL0','#44bb44','arrowUp','belowBar');
        mk(dm.hch,'HCH','#cc0000','arrowDown','aboveBar');
        mk(dm.hcl,'HCL','#44bb44','arrowUp','belowBar');
        mk(dm.dch,'DCH','#cc0000','arrowDown','aboveBar');
        if(markers.length){ markers.sort((a,b)=>a.time-b.time); _candleSeries.setMarkers(markers); }
        if(overlay.entry_price!=null) _candleSeries.createPriceLine({price:overlay.entry_price,color:'#4a90d9',lineWidth:1,lineStyle:0,axisLabelVisible:true,title:'Entry'});
        if(overlay.stop_price!=null) _candleSeries.createPriceLine({price:overlay.stop_price,color:'#cc0000',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'Stop'});
        if(overlay.target_price!=null) _candleSeries.createPriceLine({price:overlay.target_price,color:'#44bb44',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'Target'});
    }
}



// ── Agent Trader tab ─────────────────────────────────────────────────────────
const AGENT_RAW_URL = 'https://raw.githubusercontent.com/Borisp2026/trading-analyser-2/main/data/agent_trades.json';
const AI_ASSESSMENT_RAW_URL = 'https://raw.githubusercontent.com/Borisp2026/trading-analyser-2/main/data/ai_assessment.json';

async function loadAgentTrades() {
    document.getElementById('agentProgress').textContent = 'Loading...';
    try {
        const r = await fetch(AGENT_RAW_URL + '?t=' + Date.now());
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const d = await r.json();
        renderAgentDashboard(d);
    } catch(e) {
        document.getElementById('agentProgress').textContent = 'Error loading data: ' + e.message;
    }
}

function renderAgentDashboard(d) {
    const s = d.stats || {};
    const trades = d.trades || [];
    const closed = trades.filter(t=>t.status==='CLOSED').length;
    const target = d.target_trades || 100;
    const pct = Math.min(100, (closed/target)*100);

    document.getElementById('agentProgress').textContent = closed + ' / ' + target + ' trades';
    document.getElementById('agentProgressBar').style.width = pct + '%';
    const targetLabelEl = document.getElementById('agentTargetLabel');
    if(targetLabelEl) targetLabelEl.textContent = target + ' trades';
    const statusEl = document.getElementById('agentStatus');
    statusEl.textContent = d.status==='COMPLETED' ? '✓ COMPLETE — Ready for paper trading'
                         : d.status==='RUNNING'   ? '● Running' : (d.status||'—');
    statusEl.style.color = d.status==='COMPLETED'?'#44bb44':d.status==='RUNNING'?'#ff9900':'#888';

    const wr = s.win_rate || 0;
    document.getElementById('agentWinRate').innerHTML = '<span style="color:'+(wr>=60?'#44bb44':wr>=50?'#ff9900':'#cc0000')+'">'+wr+'%</span>';
    const ag = s.avg_pnl_pct || 0;
    document.getElementById('agentAvgGain').innerHTML = '<span style="color:'+(ag>=0?'#44bb44':'#cc0000')+'">'+(ag>=0?'▲ +':'▼ ')+ag.toFixed(1)+'%</span>';
    document.getElementById('agentWL').innerHTML = '<span class="trade-win">'+(s.wins||0)+'W</span> / <span class="trade-loss">'+(s.losses||0)+'L</span>';
    document.getElementById('agentCapital').textContent = '$'+(s.current_capital||1000).toFixed(2);
    const gr = s.capital_growth || 0;
    document.getElementById('agentGrowth').innerHTML = '<span style="color:'+(gr>=0?'#44bb44':'#cc0000')+'">'+(gr>=0?'▲ +':'▼ ')+gr.toFixed(1)+'%</span>';
    document.getElementById('agentOpen').textContent = Object.keys(d.open_positions||{}).length;

    const scanLog = (d.scan_log||[]).slice(-30).reverse();
    const sbody = document.getElementById('agentScanBody');
    if (!scanLog.length) {
        sbody.innerHTML = '<tr><td colspan="5" style="color:#888;text-align:center;padding:10px">No scans yet</td></tr>';
    } else {
        sbody.innerHTML = scanLog.map(l => {
            const sc = l.signal==='BUY'?'#44bb44':'#888';
            return '<tr><td style="color:#666;font-size:11px">'+(l.time||'')+'</td>'
                +'<td><b>'+(l.ticker||'')+'</b></td>'
                +'<td><span style="color:'+sc+';font-weight:bold">'+(l.signal||'')+'</span></td>'
                +'<td>'+(l.price?'$'+l.price.toFixed(3):'—')+'</td>'
                +'<td style="font-size:11px;color:#888">'+(l.notes||'').substring(0,60)+'</td></tr>';
        }).join('');
    }
}

const MACRO_DATA = __MACRO_DATA__;
// ── Macro Deployment Gate ─────────────────────────────────────────────────────
function renderMacroGate(){
    const d=MACRO_DATA;
    if(!d||!d.signals||!d.signals.length){
        document.getElementById('macroSignalsGrid').innerHTML='<p style="color:#888">No data yet — click Run Nightly Now.</p>';
        return;
    }
    const comp=d.composite||0;
    const col=d.zone_color||'#888';
    document.getElementById('macroComposite').textContent=comp.toFixed(0);
    document.getElementById('macroComposite').style.color=col;
    document.getElementById('macroZone').textContent=d.zone||'—';
    document.getElementById('macroZone').style.color=col;
    const _zd=document.getElementById('macroZoneDesc'); if(_zd) _zd.textContent=d.zone_desc||'';
    const _zc=document.getElementById('macroZoneCard'); if(_zc) _zc.style.borderColor=col;
    const _cb=document.getElementById('macroCompositeBar'); if(_cb){_cb.style.width=comp+'%';_cb.style.background=col;}
    const _sh=document.getElementById('macroScoreHeader'); if(_sh){_sh.textContent=comp.toFixed(0);_sh.style.color=col;}

    const grid=document.getElementById('macroSignalsGrid');
    function signalCard(s){
        const sc=s.score||0;
        const bc=sc>=70?'#44bb44':sc>=50?'#ff9900':sc>=30?'#ff6600':'#cc0000';
        const calm=['CALM','TIGHT','BROAD','UPTREND','CONTANGO','GREEDY'];
        const ic=calm.includes(s.interpretation)?'#44bb44':['NEUTRAL','MIXED','ABOVE 200MA'].includes(s.interpretation)?'#ff9900':'#cc0000';
        return '<div class="macro-signal-card">'
            +'<div class="macro-signal-name">'+s.name+'</div>'
            +'<div class="macro-signal-value" style="color:'+bc+'">'+(s.value_label||'--')+'</div>'
            +'<div style="display:flex;justify-content:space-between;margin-bottom:4px">'
            +'<span style="font-size:11px;color:#666">Score</span>'
            +'<span style="font-size:16px;font-weight:bold;color:'+bc+'">'+sc.toFixed(0)+'/100</span></div>'
            +'<div class="macro-score-bar-wrap"><div class="macro-score-bar" style="width:'+sc+'%;background:'+bc+'"></div></div>'
            +'<div style="text-align:right"><span style="font-size:11px;padding:2px 8px;border-radius:10px;background:'+ic+'22;color:'+ic+'">'+(s.interpretation||'')+'</span></div>'
            +'<div style="font-size:11px;color:#666;margin-top:6px">'+(s.detail||'')+'</div>'
            +'</div>';
    }
    const usS=d.us_signals||d.signals.slice(0,6);
    const asxS=d.asx_signals||d.signals.slice(6);
    const usC=d.us_composite||d.composite||0;
    const axC=d.asx_composite||d.composite||0;
    const uc=usC>=70?'#44bb44':usC>=50?'#ff9900':'#cc0000';
    const ac=axC>=70?'#44bb44':axC>=50?'#ff9900':'#cc0000';
    grid.innerHTML='<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">'
        +'<div><h3 style="color:#ccc;margin:0 0 12px;padding-bottom:8px;border-bottom:1px solid #2a2a4a">US / S&P500 <span style="font-size:20px;font-weight:bold;color:'+uc+'">'+usC.toFixed(0)+'</span></h3>'
        +'<div class="macro-signals-grid">'+usS.map(signalCard).join('')+'</div></div>'
        +'<div><h3 style="color:#ccc;margin:0 0 12px;padding-bottom:8px;border-bottom:1px solid #2a2a4a">ASX / Australia <span style="font-size:20px;font-weight:bold;color:'+ac+'">'+axC.toFixed(0)+'</span></h3>'
        +'<div class="macro-signals-grid">'+asxS.map(signalCard).join('')+'</div></div>'
        +'</div>';
}

const QUANT_DATA = __QUANT_DATA__;
const CYCLE_DATA = __CYCLE_DATA__;
const PAPER_DATA = __PAPER_DATA__;
const SUGGESTIONS_DATA = __SUGGESTIONS_DATA__;
// ── Quantitative Analysis tab ─────────────────────────────────────────────────
function renderQuantTab(section){
  if(section) window._activeQuantSection = section;
    document.querySelectorAll('.quant-btn').forEach(b=>b.classList.remove('active'));
    const btn=document.getElementById('qbtn-'+section);
    if(btn)btn.classList.add('active');
    const results=QUANT_DATA.results||QUANT_DATA||{};
    const tickers=Object.keys(results);
    if(!tickers.length){
        document.getElementById('quantContent').innerHTML='<p style="color:#888;padding:20px">No quantitative data yet — click "Run Nightly Now" to generate.</p>';return;
    }
    if(section==='earnings')     renderEarnings(results,tickers);
    else if(section==='momentum')    renderMomentum(results,tickers);
    else if(section==='rsi')         renderRSIStrategy(results,tickers);
    else if(section==='macd')        renderMACD(results,tickers);
    else if(section==='stochastic')  renderStochastic(results,tickers);
    else if(section==='ema')         renderEMA(results,tickers);
    else if(section==='vwap')        renderVWAP(results,tickers);
    else if(section==='ma')          renderMAStrategy(results,tickers);
    else if(section==='walkforward') renderWalkForward(results,tickers);
    else if(section==='montecarlo')  renderMonteCarlo(results,tickers);
    else if(section==='sensitivity') renderSensitivity(results,tickers);
    else if(section==='top5')      renderTop5Stocks(results,tickers);
}

function renderTop5Stocks(results,tickers){
    // Stocks only -- ETFs (VAS.AX, VTEK.AX, etc.) skew this table when they have
    // too little history for a real ranking, and "Top 5 Stocks" shouldn't include
    // them anyway.
    const etfSet=new Set((WATCHLIST&&WATCHLIST.etf)||[]);
    const scored=tickers.filter(function(t){return !etfSet.has(t)}).map(function(t){
        var r=results[t]||{};
        var mom=r.momentum&&r.momentum.percentile!=null?r.momentum.percentile:null;
        var mc=r.monte_carlo&&r.monte_carlo.prob_up!=null?r.monte_carlo.prob_up:null;
        var maRet=r.ma_strategy&&r.ma_strategy.avg_golden_return_60d!=null?Math.min(100,Math.max(0,r.ma_strategy.avg_golden_return_60d/3)):null;
        // Require all 3 signals -- averaging whatever happens to be present let a
        // ticker missing 2 of 3 (e.g. not enough history for momentum/MA) rank #1
        // off a single strong number instead of a real 3-signal consensus.
        if(mom==null||mc==null||maRet==null) return null;
        var avg=(mom+mc+maRet)/3;
        return {ticker:t,score:Math.round(avg),r:r};
    }).filter(Boolean).sort(function(a,b){return b.score-a.score}).slice(0,5);
    if(!scored.length){document.getElementById('quantContent').innerHTML='<p style="color:#888;padding:20px">No stocks with complete momentum/Monte Carlo/MA data yet.</p>';return;}
    document.getElementById('quantContent').innerHTML=
        '<h3 style="color:#ccc;margin-bottom:16px">&#11088; Top 5 Stocks &mdash; Overall Score</h3>'
        +'<div style="display:grid;gap:12px">'
        +scored.map(function(s,i){
            var col=s.score>=70?'#44bb44':s.score>=50?'#ff9900':s.score>=40?'#ff6600':'#cc0000';
            var mom=s.r.momentum&&s.r.momentum.percentile!=null?s.r.momentum.percentile.toFixed(0):'n/a';
            var mc=s.r.monte_carlo&&s.r.monte_carlo.prob_up!=null?s.r.monte_carlo.prob_up.toFixed(0):'n/a';
            var ma=s.r.ma_strategy&&s.r.ma_strategy.avg_golden_return_60d!=null?s.r.ma_strategy.avg_golden_return_60d.toFixed(1):'n/a';
            var trend=s.r.ma_strategy?s.r.ma_strategy.trend||'n/a':'n/a';
            return '<div style=\"background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid '+(i===0?col:'#2a2a4a')+'\">'
                +'<div style=\"display:flex;justify-content:space-between;align-items:center;margin-bottom:10px\">'
                +'<div><span style=\"font-size:26px;font-weight:bold;color:#555;margin-right:10px\">#'+(i+1)+'</span>'
                +'<span style=\"font-size:20px;font-weight:bold;color:#fff\">'+s.ticker+'</span></div>'
                +'<span style=\"font-size:28px;font-weight:bold;color:'+col+'\">'+s.score+'</span></div>'
                +'<div style=\"background:#0f0f1a;border-radius:6px;height:8px;margin-bottom:10px\">'
                +'<div style=\"height:8px;border-radius:6px;background:'+col+';width:'+Math.min(100,s.score)+'%\"></div></div>'
                +'<div style=\"display:grid;grid-template-columns:repeat(4,1fr);gap:6px;font-size:12px;text-align:center\">'
                +'<div><div style=\"color:#666\">Momentum</div><div style=\"color:#ccc;font-weight:bold\">'+mom+'th</div></div>'
                +'<div><div style=\"color:#666\">MC Prob</div><div style=\"color:#ccc;font-weight:bold\">'+mc+'%</div></div>'
                +'<div><div style=\"color:#666\">MA Return</div><div style=\"color:#ccc;font-weight:bold\">'+ma+'%</div></div>'
                +'<div><div style=\"color:#666\">Trend</div><div style=\"color:#ccc;font-weight:bold\">'+trend+'</div></div>'
                +'</div></div>';
        }).join('')+'</div>';
}

// ── Cycle Trading tab ────────────────────────────────────────────────────────
function renderCycleTab(){
  const d = CYCLE_DATA || {};
  renderCombinedRisk(d);
  renderCycleAlerts(d.failed_cycle_alerts||[], 'cycleFailedAlerts', 'FAILED CYCLE', '#cc0000');
  renderCycleAlerts(d.high_risk_alerts||[], 'cycleHighRiskAlerts', 'HIGH RISK ZONE', '#ff9900');
  renderCycleCandidates(d.candidates||[]);
}
async function renderCombinedRisk(cycleData){
  const el=document.getElementById('combinedRiskPanel');
  if(!el) return;
  const cd=cycleData.drawdown||{};
  const cycleCapital=10000, cycleAtRisk=cycleCapital*(cd.drawdown_pct||0)/100;
  let agentCapital=10000, agentStart=10000, agentDrawdownPct=0;
  try{
    const r=await fetch(AGENT_RAW_URL+'?t='+Date.now());
    if(r.ok){
      const ad=await r.json();
      agentCapital=ad.capital!=null?ad.capital:agentCapital;
      agentStart=ad.starting_capital||agentStart;
      agentDrawdownPct=Math.max(0,(agentStart-agentCapital)/agentStart*100);
    }
  }catch(e){/* Agent Trader data unavailable, show Cycle Trading only */}
  const combinedCapital=cycleCapital+agentStart;
  const combinedAtRisk=cycleAtRisk+(agentStart*agentDrawdownPct/100);
  const ddColor=p=>p>=15?'#cc0000':p>=8?'#ff9900':'#44bb44';
  el.innerHTML='<h3 style="color:#ccc;margin-bottom:10px">Combined Risk (Cycle Trading + Agent Trader)</h3>'
    +'<div class="stats-grid">'
    +'<div class="stat-card"><div class="stat-label">Cycle Trading Drawdown</div>'
    +'<div class="stat-value" style="color:'+ddColor(cd.drawdown_pct||0)+'">'+(cd.drawdown_pct||0).toFixed(1)+'%'+(cd.halted?' (HALTED)':'')+'</div></div>'
    +'<div class="stat-card"><div class="stat-label">Agent Trader Drawdown</div>'
    +'<div class="stat-value" style="color:'+ddColor(agentDrawdownPct)+'">'+agentDrawdownPct.toFixed(1)+'%</div></div>'
    +'<div class="stat-card"><div class="stat-label">Combined Capital Deployed</div>'
    +'<div class="stat-value">$'+combinedCapital.toLocaleString()+'</div></div>'
    +'<div class="stat-card"><div class="stat-label">Combined $ At Risk (drawdown)</div>'
    +'<div class="stat-value" style="color:'+ddColor(combinedAtRisk/combinedCapital*100)+'">$'+combinedAtRisk.toFixed(0)+'</div></div>'
    +'</div>';
}
function renderCycleAlerts(list, elId, label, color){
  const el=document.getElementById(elId);
  if(!el) return;
  el.innerHTML = list.length ? list.map(a=>
    '<div class="alert-card" style="border-left-color:'+color+'">'
    +'<span class="alert-ticker">'+a.ticker+'</span>'
    +'<span style="color:'+color+';font-weight:bold;font-size:11px">'+label+'</span>'
    +'<div class="alert-detail">'+(a.detail||'')+'</div></div>'
  ).join('') : '';
}
function showCandidateChart(ticker){
  const c=(CYCLE_DATA.candidates||[]).find(x=>x.ticker===ticker);
  showChart(ticker, c?c.chart_overlay:null);
}
function showCycleTradeChart(ticker){
  const t=(CYCLE_DATA.open_trades||[]).find(x=>x.ticker===ticker)
       || (CYCLE_DATA.closed_trades||[]).find(x=>x.ticker===ticker);
  showChart(ticker, t?t.chart_overlay:null);
}
function showSimpleTradeChart(ticker,entry,stop,target){
  showChart(ticker, {entry_price:entry, stop_price:stop, target_price:target});
}
function cycleTradeStatusBadge(status){
  if(status==='OPENED_THIS_RUN') return '<span style="background:#44bb4422;color:#44bb44;font-size:10px;font-weight:bold;padding:3px 8px;border-radius:10px">✓ OPENED TONIGHT</span>';
  if(status==='ALREADY_OPEN') return '<span style="background:#4a90d922;color:#4a90d9;font-size:10px;font-weight:bold;padding:3px 8px;border-radius:10px">✓ POSITION OPEN</span>';
  if(status==='SKIPPED_COOLDOWN') return '<span style="background:#ff990022;color:#ff9900;font-size:10px;font-weight:bold;padding:3px 8px;border-radius:10px">⏳ COOLDOWN</span>';
  if(status==='SKIPPED_ALREADY_HELD_REAL') return '<span style="background:#ff990022;color:#ff9900;font-size:10px;font-weight:bold;padding:3px 8px;border-radius:10px">⚠ ALREADY HELD (REAL)</span>';
  return '<span style="background:#88888822;color:#888;font-size:10px;font-weight:bold;padding:3px 8px;border-radius:10px">NOT ENTERED</span>';
}
function renderCycleCandidates(list){
  const el=document.getElementById('cycleCandidatesGrid');
  if(!el) return;
  if(!list.length){ el.innerHTML='<p style="color:#888;padding:20px">No qualifying candidates tonight.</p>'; return; }
  el.innerHTML = list.map((c,i)=>{
    const col=c.cycle_score>=70?'#44bb44':c.cycle_score>=50?'#ff9900':c.cycle_score>=40?'#ff6600':'#cc0000';
    const pm=c.predicted_move||{};
    return '<div style="background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid '+(i===0?col:'#2a2a4a')+'">'
      +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
      +'<div><span style="font-size:20px;font-weight:bold;color:#fff">'+c.ticker+'</span>'
      +'<span style="color:#888;font-size:12px;margin-left:8px">'+(c.entry_zone||'—')+' ('+(c.risk||'—')+' risk)</span></div>'
      +'<span style="font-size:26px;font-weight:bold;color:'+col+'">'+c.cycle_score+'</span></div>'
      +'<div style="margin-bottom:10px">'+cycleTradeStatusBadge(c.paper_trade_status)+'</div>'
      +'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;font-size:12px;text-align:center">'
      +'<div><div style="color:#666">Price</div><div style="color:#ccc">$'+c.price+'</div></div>'
      +'<div><div style="color:#666">Target</div><div style="color:#44bb44">'+(pm.target_price?('$'+pm.target_price):'—')+'</div></div>'
      +'<div><div style="color:#666">Stop</div><div style="color:#cc0000">'+(c.stop_price?('$'+c.stop_price):'—')+'</div></div>'
      +'<div><div style="color:#666">DC in IC</div><div style="color:#ccc">'+(c.dc_num_in_ic||'—')+'</div></div></div>'
      +'<div style="font-size:11px;color:#aaa;margin-top:8px">'+(c.reasons||[]).join(' | ')+'</div>'
      +'<button class="btn-primary" style="margin-top:10px;padding:6px 14px;font-size:12px" onclick="showCandidateChart(\''+c.ticker+'\')">📈 Chart</button>'
      +'</div>';
  }).join('');
}
// ── Paper Trading tab — merges Cycle Trading (+ manual) portfolio.json trades
// with Agent Trader's separate ledger into one view, tagged by source. ──────
function normalizePortfolioPaperTrades(){
  const open=(PAPER_DATA.open_trades||[]).map(t=>({...t,_openFlag:true}));
  const closed=(PAPER_DATA.closed_trades_detail||[]).map(t=>({...t,_openFlag:false}));
  return [...open,...closed].map(t=>{
    const strat=(t.meta||{}).strategy;
    const qty=t.shares!=null?t.shares:t.qty;
    const entry=t.buy_price!=null?t.buy_price:t.entry_price;
    return {
      source: strat==='cycle_trading' ? 'Cycle Trading' : strat==='suggested_trades' ? 'Trade Ideas' : (strat||'Manual'),
      ticker: t.ticker, entry, qty,
      positionCost: (qty!=null && entry!=null) ? qty*entry : null,
      stop: t.stop_price!=null?t.stop_price:t.stop_loss,
      target: t.target_price!=null?t.target_price:t.take_profit,
      opened: t.buy_date || (t.opened||'').slice(0,10),
      closed: t.sell_date || (t.closed||'').slice(0,10),
      exit: t.sell_price!=null?t.sell_price:t.exit_price,
      pnlDollar: t.pnl!=null?t.pnl:null,
      pnlPct: t.pnl_pct!=null?t.pnl_pct:null,
      reason: t.close_reason||'',
      open: !!t._openFlag,
    };
  });
}
function normalizeAgentTrades(d){
  return (d.trades||[]).map(t=>({
    source:'Agent Trader', ticker:t.ticker, entry:t.entry_price, qty:null,
    positionCost: t.position_size!=null?t.position_size:null,
    stop:t.stop, target:t.target,
    opened:(t.entry_time||'').slice(0,10), closed:(t.exit_time||'').slice(0,10),
    exit:t.exit_price, pnlDollar:t.pnl_dollar, pnlPct:t.pnl_pct,
    reason:t.exit_reason||'', open: t.status!=='CLOSED',
  }));
}
function fmtMoney(v){ return v==null ? '—' : '$'+Number(v).toFixed(2); }
function fmtPct(v){ return v==null ? '—' : (v>=0?'▲ +':'▼ ')+v.toFixed(2)+'%'; }
function priceAtPct(v,pct){ return v==null ? null : Math.round(Number(v)*(1+pct/100)*10000)/10000; }
function profitLevel(v,pct){ const p=priceAtPct(v,pct); return p==null ? '—' : '$'+p.toFixed(3); }
// Trade Ideas' standard stop across every source (nightly, live scan, Cycle Trading
// candidates) -- one flat -5% rule instead of each source's own varied stop logic.
function tradeIdeasStop(price){ return priceAtPct(price,-5); }
// % gain if a position were sold at its own suggested/target price, as opposed to
// the generic +5%/+10% reference markers profitLevels() shows.
function pctAtPrice(entry,targetPrice){
  return (entry==null||targetPrice==null) ? null : Math.round((targetPrice-entry)/entry*10000)/100;
}
// "% if sold at target" cards, formatted once here (colour + colour-blind-safe
// arrow) instead of the same three-times-repeated ternary at each call site.
function pctAtPriceStr(entry,targetPrice){
  const pct=pctAtPrice(entry,targetPrice);
  if(pct==null) return {color:'#888', text:'—'};
  return {color: pct>=0?'#44bb44':'#cc0000', text: (pct>=0?'▲ +':'▼ ')+pct+'%'};
}
function profitLevels(v){ return v==null ? '—' : profitLevel(v,5)+' / '+profitLevel(v,10); }
// Last nightly close from the already-loaded watchlist chart data -- used as a fast
// fallback when a live fetch isn't available/fails, and for tickers outside the
// watchlist that have no live-fetchable current price at all.
function getCurrentPrice(ticker){
  const cd=CHART_DATA[ticker];
  if(cd && cd.candles && cd.candles.length) return cd.candles[cd.candles.length-1].close;
  return null;
}
// True live price for open-position tables ("Current" should mean right now, not
// last night's close) -- falls back to the nightly close if the live fetch fails.
async function getLiveCurrentPrice(ticker){
  const live=await fetchLivePrice(ticker);
  return live!=null ? live : getCurrentPrice(ticker);
}
// Fetches live prices for a set of tickers and returns {ticker: price}. Sequential
// with a small delay, not Promise.all -- firing many corsproxy.io requests at once
// (confirmed via testing) makes some of them silently fail and fall back to last
// close even though the exact same ticker succeeds fine when fetched on its own.
async function getLiveCurrentPrices(tickers){
  const uniq=[...new Set(tickers)];
  const out={};
  for(const t of uniq){
    out[t]=await getLiveCurrentPrice(t);
    await new Promise(r=>setTimeout(r,150));
  }
  return out;
}
function chartButton(r){
  const btn='<button class="btn-primary" style="padding:2px 8px;font-size:10px;margin-left:4px" onclick="%ONCLICK%">📈</button>';
  const onclick = r.source==='Cycle Trading'
    ? "showCycleTradeChart('"+r.ticker+"')"
    : "showSimpleTradeChart('"+r.ticker+"',"+(r.entry??'null')+","+(r.stop??'null')+","+(r.target??'null')+")";
  return ' '+btn.replace('%ONCLICK%', onclick);
}
// Agent Trader is excluded here -- it's a live 5-min automated bot with its own
// separate ledger file (agent_trades.json); manually closing a position from the
// dashboard would race against its own cron-driven exit logic and capital tracking.
function sellButton(r){
  if(r.source==='Agent Trader') return '';
  return '<button class="btn-primary" style="padding:4px 10px;font-size:11px;background:#5a1a1a;border-color:#8a2a2a" onclick="sellPaperTrade(\''+r.ticker+'\',\''+r.source+'\')">Sell</button>';
}
async function sellPaperTrade(ticker, source){
  if(!getToken()){alert('Set your GitHub token first (Token tab).');showTab('token');return;}
  const strategy = source==='Cycle Trading' ? 'cycle_trading' : source==='Trade Ideas' ? 'suggested_trades' : null;
  try{
    const {data,sha}=await readPortfolio();
    const t=(data.paper_trades||[]).find(x=>x.ticker===ticker && x.status==='open'
      && (strategy ? (x.meta||{}).strategy===strategy : !(x.meta||{}).strategy));
    if(!t){alert('No open '+source+' position found for '+ticker+'.');return;}
    const suggested=t.target_price!=null?t.target_price:null;
    const exitStr=prompt('Exit price for '+ticker+' ('+source+')?\n'+(suggested!=null?'Suggested target: $'+suggested:'No suggested target set for this position.'),
      suggested!=null?String(suggested):'');
    if(!exitStr) return;
    const exit=parseFloat(exitStr);
    if(!exit||exit<=0) return;
    const pnl=Math.round((exit-t.buy_price)*t.shares*100)/100;
    t.status='closed'; t.sell_price=exit; t.sell_date=new Date().toISOString().slice(0,10);
    t.pnl=pnl; t.pnl_pct=Math.round((exit-t.buy_price)/t.buy_price*10000)/100;
    t.close_reason='MANUAL';
    await writePortfolio(data,sha);
    alert('Closed '+ticker+': P&L $'+pnl.toFixed(2));
    if(document.getElementById('tab-paper')?.classList.contains('active')) renderPaperTab();
    if(document.getElementById('tab-suggestions')?.classList.contains('active')) renderSuggestionsTab();
  }catch(e){alert('Error: '+e.message);}
}
// Fetches the hourly Claude check-in on open positions -- advisory only, this
// never places, closes, or modifies a trade on its own. Populates _aiPerPosition
// (ticker -> one-line read) so ANY open-positions table -- Paper Trading's or
// Trade Ideas' own -- can show it inline on the row it's about, plus renders the
// full panel when that element exists (Paper Trading tab only). Fetched live
// (not baked into the nightly build) since it updates on its own hourly cycle.
// Cached per page-load once successfully fetched, so visiting both tabs doesn't
// re-fetch every time.
let _aiPerPosition={};
let _aiFetched=false;
let _aiLastRender=null;
async function renderAiAssessment(){
  const el=document.getElementById('aiAssessmentPanel');
  if(_aiFetched){
    // Already have the data this page-load -- just (re)render the panel if present.
    if(el && _aiLastRender) el.innerHTML=_aiLastRender;
    return;
  }
  try{
    const r=await fetch(AI_ASSESSMENT_RAW_URL+'?t='+Date.now());
    if(!r.ok) throw new Error('HTTP '+r.status);
    const d=await r.json();
    _aiFetched=true;
    if(!d.enabled){
      _aiLastRender='<p style="color:#888;margin:0">Not set up yet — needs an <code>ANTHROPIC_API_KEY</code> repo secret before this can run. See the AI Position Assessment workflow.</p>';
      if(el) el.innerHTML=_aiLastRender;
      return;
    }
    const when=d.generated_at ? new Date(d.generated_at) : null;
    const whenStr=when ? when.toLocaleString('en-AU',{weekday:'short',hour:'2-digit',minute:'2-digit'}) : '—';
    if(d.error){
      _aiLastRender='<div style="font-size:11px;color:#666;margin-bottom:10px">Last attempted: '+whenStr+' · '+(d.positions_checked||0)+' position(s)</div>'
        +'<p style="color:#cc0000;margin:0">Assessment failed: '+d.error+'</p>';
      if(el) el.innerHTML=_aiLastRender;
      return;
    }
    _aiPerPosition = (d.per_position && Object.keys(d.per_position).length) ? d.per_position : {};
    const header='<div style="font-size:11px;color:#666;margin-bottom:10px">As of '+whenStr+' · '+(d.positions_checked||0)+' position(s) checked · '+(d.model||'')+'</div>';
    if(Object.keys(_aiPerPosition).length){
      // Per-position reads now show inline on each Open Positions row (Paper
      // Trading and Trade Ideas both) -- this panel becomes the portfolio-level
      // note plus a pointer, not a wall of per-ticker text duplicated everywhere.
      _aiLastRender=header
        +'<div style="color:#ccc;font-size:13px;line-height:1.6">'+(d.portfolio_note||'No portfolio-level note returned.')+'</div>'
        +'<p style="color:#666;font-size:11px;margin-top:10px">Per-position reads shown inline on each row in Open Positions.</p>';
    }else{
      _aiLastRender=header
        +'<div style="color:#ccc;font-size:13px;line-height:1.6;white-space:pre-wrap">'+(d.assessment||'No assessment text returned.')+'</div>';
    }
    if(el) el.innerHTML=_aiLastRender;
  }catch(e){
    _aiLastRender='<p style="color:#888;margin:0">AI assessment unavailable right now ('+e.message+').</p>';
    if(el) el.innerHTML=_aiLastRender;
  }
}
async function renderPaperTab(){
  let rows = normalizePortfolioPaperTrades();
  try{
    const r=await fetch(AGENT_RAW_URL+'?t='+Date.now());
    if(r.ok) rows = rows.concat(normalizeAgentTrades(await r.json()));
  }catch(e){/* Agent Trader data unavailable, show other sources only */}
  await renderAiAssessment();  // awaited so _aiPerPosition is populated before rows render below

  const openRows=rows.filter(r=>r.open);
  const closedRows=rows.filter(r=>!r.open);
  const wins=closedRows.filter(r=>(r.pnlDollar||0)>0).length;
  const winRate=closedRows.length?(wins/closedRows.length*100):0;
  const realizedPnl=closedRows.reduce((s,r)=>s+(r.pnlDollar||0),0);
  const deployed=openRows.reduce((s,r)=>s+(r.positionCost||0),0);

  const ovEl=document.getElementById('paperOverviewGrid');
  if(ovEl) ovEl.innerHTML=
      '<div class="stat-card"><div class="stat-label">Combined Capital</div><div class="stat-value">$30,000</div></div>'
    + '<div class="stat-card"><div class="stat-label">Deployed (Open)</div><div class="stat-value">'+fmtMoney(deployed)+'</div></div>'
    + '<div class="stat-card"><div class="stat-label">Open Positions</div><div class="stat-value">'+openRows.length+'</div></div>'
    + '<div class="stat-card"><div class="stat-label">Closed Trades</div><div class="stat-value">'+closedRows.length+'</div></div>'
    + '<div class="stat-card"><div class="stat-label">Win Rate</div><div class="stat-value" style="color:'+(winRate>=50?'#44bb44':'#cc0000')+'">'+winRate.toFixed(1)+'%</div></div>'
    + '<div class="stat-card"><div class="stat-label">Realized P&amp;L</div><div class="stat-value" style="color:'+(realizedPnl>=0?'#44bb44':'#cc0000')+'">'+(realizedPnl>=0?'▲ ':'▼ ')+fmtMoney(realizedPnl)+'</div></div>';

  const sources=[...new Set(rows.map(r=>r.source))];
  const srcEl=document.getElementById('paperSourceGrid');
  if(srcEl) srcEl.innerHTML=sources.map(src=>{
    const sr=rows.filter(r=>r.source===src);
    const sOpen=sr.filter(r=>r.open).length;
    const sClosed=sr.filter(r=>!r.open);
    const sPnl=sClosed.reduce((s,r)=>s+(r.pnlDollar||0),0);
    return '<div class="stat-card"><div class="stat-label">'+src+'</div>'
      +'<div class="stat-value" style="font-size:15px">'+sOpen+' open / '+sClosed.length+' closed</div>'
      +'<div style="font-size:12px;margin-top:4px;color:'+(sPnl>=0?'#44bb44':'#cc0000')+'">'+(sPnl>=0?'▲ ':'▼ ')+fmtMoney(sPnl)+' realized</div></div>';
  }).join('');

  const openBody=document.getElementById('paperOpenBody');
  const renderOpenRows=(prices)=> openRows.length ? openRows.map(r=>{
    const cur = prices ? prices[r.ticker] : getCurrentPrice(r.ticker);
    const curColor = (cur==null||r.entry==null) ? '#888' : (cur>=r.entry?'#44bb44':'#cc0000');
    const pct = pctAtPrice(r.entry, r.target);
    const pctArrow=(pct||0)>=0?'▲ ':'▼ ';
    // AI Assessment's per-ticker read, right on the row it's about instead of a
    // separate panel the reader has to cross-reference by ticker themselves.
    const aiRead=_aiPerPosition[r.ticker];
    const aiLine=aiRead ? '<div style="font-size:10px;color:#7fa8d9;margin-top:2px;max-width:220px">🤖 '+aiRead+'</div>' : '';
    return '<tr><td>'+r.source+'</td><td><b>'+r.ticker+'</b>'+chartButton(r)+aiLine
    +'</td><td>'+fmtMoney(r.entry)+'</td><td style="color:'+curColor+'">'+fmtMoney(cur)+'</td><td>'+fmtMoney(r.positionCost)+'</td>'
    +'<td style="color:#cc0000">'+fmtMoney(r.stop)+'</td><td style="color:#44bb44">'+fmtMoney(r.target)+'</td>'
    +'<td style="font-size:11px;color:'+((pct||0)>=0?'#44bb44':'#cc0000')+'">'+(pct!=null?pctArrow+(pct>=0?'+':'')+pct+'%':'—')+'</td>'
    +'<td style="font-size:11px;color:#888">'+(r.opened||'—')+'</td><td>'+sellButton(r)+'</td></tr>';
  }).join('') : '<tr><td colspan="10" style="color:#888;text-align:center;padding:20px">No open positions</td></tr>';
  if(openBody) openBody.innerHTML=renderOpenRows(null);  // fast render with last-close fallback first
  if(openRows.length){
    getLiveCurrentPrices(openRows.map(r=>r.ticker)).then(prices=>{
      if(document.getElementById('paperOpenBody')) document.getElementById('paperOpenBody').innerHTML=renderOpenRows(prices);
    });
  }

  const closedBody=document.getElementById('paperClosedBody');
  if(closedBody) closedBody.innerHTML = closedRows.length ? closedRows.map(r=>
    '<tr><td>'+r.source+'</td><td><b>'+r.ticker+'</b>'+chartButton(r)+'</td><td>'+fmtMoney(r.entry)+'</td><td>'+fmtMoney(r.exit)+'</td>'
    +'<td>'+fmtMoney(r.positionCost)+'</td>'
    +'<td style="font-size:11px;color:#888">'+(r.opened||'—')+'</td><td style="font-size:11px;color:#888">'+(r.closed||'—')+'</td>'
    +'<td style="font-size:11px">'+(r.reason||'')+'</td>'
    +'<td style="color:'+((r.pnlDollar||0)>=0?'#44bb44':'#cc0000')+';font-weight:bold">'+((r.pnlDollar||0)>=0?'▲ ':'▼ ')+fmtMoney(r.pnlDollar)+'</td>'
    +'<td style="color:'+((r.pnlPct||0)>=0?'#44bb44':'#cc0000')+'">'+fmtPct(r.pnlPct)+'</td></tr>'
  ).join('') : '<tr><td colspan="10" style="color:#888;text-align:center;padding:20px">No closed trades yet</td></tr>';
}

// ── Trade Ideas tab — suggested entries the user decides on manually. ───────
// Buy/Sell write straight to portfolio.json via the GitHub token (same path as
// Add Paper Trade); nothing here executes on its own.
const IDEAS_STRATEGY='suggested_trades';
const IDEAS_BUDGET=10000;
function renderSuggestionCards(){
  const el=document.getElementById('ideasCandidatesGrid');
  if(!el) return;
  const list=SUGGESTIONS_DATA||[];
  if(!list.length){ el.innerHTML='<p style="color:#888;padding:20px">No BUY-rated candidates tonight.</p>'; return; }
  el.innerHTML=list.map((s,i)=>{
    const col=s.rec_color||(s.blended_score>=63?'#00aa00':s.blended_score>=58?'#44bb44':'#888');
    return '<div style="background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid '+(i===0?col:'#2a2a4a')+'">'
      +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
      +'<div><span style="font-size:20px;font-weight:bold;color:#fff">'+s.ticker+'</span>'
      +'<span style="color:'+col+';font-size:12px;margin-left:8px;font-weight:bold">'+(s.recommendation||'')+'</span>'
      +'<span style="color:#888;font-size:11px;margin-left:8px">confidence: '+(s.confidence||'—')+'</span></div>'
      +'<span style="font-size:26px;font-weight:bold;color:'+col+'">'+(s.blended_score!=null?s.blended_score:'—')+'</span></div>'
      +'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;font-size:12px;text-align:center;margin-bottom:6px">'
      +'<div><div style="color:#666">Current</div><div style="color:#ccc">'+fmtMoney(getCurrentPrice(s.ticker)??s.price)+'</div></div>'
      +'<div><div style="color:#666">Suggested Entry</div><div style="color:#4a90d9">'+fmtMoney(s.entry_price)+'</div></div>'
      +'<div><div style="color:#666">Stop (-5%)</div><div style="color:#cc0000">'+fmtMoney(tradeIdeasStop(s.price))+'</div></div></div>'
      +'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;font-size:12px;text-align:center;margin-bottom:10px">'
      +'<div><div style="color:#666">Target</div><div style="color:#44bb44">'+fmtMoney(s.take_profit)+'</div></div>'
      +'<div><div style="color:#666">% if sold at target</div><div style="color:'+pctAtPriceStr(s.price,s.take_profit).color+'">'+pctAtPriceStr(s.price,s.take_profit).text+'</div></div>'
      +'<div><div style="color:#666">+5% / +10%</div><div style="color:#888;font-size:10px">'+profitLevels(s.price)+'</div></div></div>'
      +'<div style="font-size:11px;color:#aaa;margin-bottom:6px"><b>Entry:</b> '+(s.entry_type||'—')+'</div>'
      +'<div style="font-size:11px;color:#aaa;margin-bottom:6px"><b>Exit guide:</b> stop at -5% ('+fmtMoney(tradeIdeasStop(s.price))+'), target '+fmtMoney(s.take_profit)+(s.timing?' | '+s.timing:'')+'</div>'
      +'<div style="font-size:11px;color:#888;margin-bottom:10px">'+(s.reasons||[]).join(' | ')+'</div>'
      +'<button class="btn-primary" style="padding:6px 14px;font-size:12px" onclick="buyIdea(\''+s.ticker+'\')">Buy</button>'
      +' <button class="btn-primary" style="padding:6px 14px;font-size:12px;margin-left:6px" onclick="showSimpleTradeChart(\''+s.ticker+'\','+(s.entry_price??'null')+','+(tradeIdeasStop(s.price)??'null')+','+(s.take_profit??'null')+')">📈 Chart</button>'
      +'</div>';
  }).join('');
}
async function renderSuggestionsTab(){
  renderSuggestionCards();
  renderCycleIdeas();
  if(_liveIdeas.length) renderLiveIdeas();
  await renderAiAssessment();  // cached after first call this page-load; populates _aiPerPosition for the row below
  const openBody=document.getElementById('ideasOpenBody');
  const ovEl=document.getElementById('ideasOverviewGrid');
  if(!getToken()){
    if(openBody) openBody.innerHTML='<tr><td colspan="10" style="color:#888;text-align:center;padding:20px">Set your GitHub token on the Token tab to view live positions and use Buy/Sell.</td></tr>';
    if(ovEl) ovEl.innerHTML='<div class="stat-card"><div class="stat-label">Budget</div><div class="stat-value">$'+IDEAS_BUDGET.toLocaleString()+'</div></div>';
    return;
  }
  try{
    const {data}=await readPortfolio();
    const trades=(data.paper_trades||[]).filter(t=>(t.meta||{}).strategy===IDEAS_STRATEGY);
    const open=trades.filter(t=>t.status==='open');
    const closed=trades.filter(t=>t.status==='closed');
    const deployed=open.reduce((s,t)=>s+t.shares*t.buy_price,0);
    const realizedPnl=closed.reduce((s,t)=>s+(t.pnl||0),0);
    if(ovEl) ovEl.innerHTML=
        '<div class="stat-card"><div class="stat-label">Budget</div><div class="stat-value">$'+IDEAS_BUDGET.toLocaleString()+'</div></div>'
      + '<div class="stat-card"><div class="stat-label">Deployed</div><div class="stat-value">'+fmtMoney(deployed)+'</div></div>'
      + '<div class="stat-card"><div class="stat-label">Remaining</div><div class="stat-value">'+fmtMoney(IDEAS_BUDGET-deployed)+'</div></div>'
      + '<div class="stat-card"><div class="stat-label">Open Positions</div><div class="stat-value">'+open.length+'</div></div>'
      + '<div class="stat-card"><div class="stat-label">Realized P&amp;L</div><div class="stat-value" style="color:'+(realizedPnl>=0?'#44bb44':'#cc0000')+'">'+(realizedPnl>=0?'▲ ':'▼ ')+fmtMoney(realizedPnl)+'</div></div>';
    const renderIdeasOpenRows=(prices)=> open.length ? open.map(t=>{
      const cur = prices ? prices[t.ticker] : getCurrentPrice(t.ticker);
      const curColor = (cur==null) ? '#888' : (cur>=t.buy_price?'#44bb44':'#cc0000');
      const pct = pctAtPrice(t.buy_price, t.target_price);
      const pctArrow=(pct||0)>=0?'▲ ':'▼ ';
      const aiRead=_aiPerPosition[t.ticker];
      const aiLine=aiRead ? '<div style="font-size:10px;color:#7fa8d9;margin-top:2px;max-width:220px">🤖 '+aiRead+'</div>' : '';
      return '<tr><td><b>'+t.ticker+'</b>'+aiLine+'</td><td>'+fmtMoney(t.buy_price)+'</td><td style="color:'+curColor+'">'+fmtMoney(cur)+'</td><td>'+t.shares+'</td>'
      +'<td>'+fmtMoney(t.shares*t.buy_price)+'</td>'
      +'<td style="color:#cc0000">'+fmtMoney(t.stop_price)+'</td><td style="color:#44bb44">'+fmtMoney(t.target_price)+'</td>'
      +'<td style="font-size:11px;color:'+((pct||0)>=0?'#44bb44':'#cc0000')+'">'+(pct!=null?pctArrow+(pct>=0?'+':'')+pct+'%':'—')+'</td>'
      +'<td style="font-size:11px;color:#888">'+(t.buy_date||'—')+'</td>'
      +'<td><button class="btn-primary" style="padding:4px 10px;font-size:11px" onclick="sellIdea(\''+t.ticker+'\')">Sell</button></td></tr>';
    }).join('') : '<tr><td colspan="10" style="color:#888;text-align:center;padding:20px">No open Trade Ideas positions</td></tr>';
    if(openBody) openBody.innerHTML=renderIdeasOpenRows(null);
    if(open.length){
      getLiveCurrentPrices(open.map(t=>t.ticker)).then(prices=>{
        const ob=document.getElementById('ideasOpenBody');
        if(ob) ob.innerHTML=renderIdeasOpenRows(prices);
      });
    }
  }catch(e){
    if(openBody) openBody.innerHTML='<tr><td colspan="10" style="color:#cc0000;text-align:center;padding:20px">Error loading: '+e.message+'</td></tr>';
  }
}
// Every buy path (Trade Ideas, Cycle Trading, Live Scan, Add Your Own Trade) funnels
// through here, which just opens the shared confirm modal -- nothing writes to the
// portfolio until confirmBuyFromModal() runs off a deliberate "Confirm Buy" click,
// with ticker/price/shares/stop/target all visible at once instead of a chain of
// separate prompt() dialogs.
let _pendingBuy=null;
async function executeIdeaBuy(idea, opts){
  opts = opts || {};
  if(!idea || !idea.price){alert('No data for '+(idea&&idea.ticker));return;}
  if(!getToken()){alert('Set your GitHub token first (Token tab).');showTab('token');return;}
  _pendingBuy = {idea, opts};
  document.getElementById('bc_ticker').textContent = idea.ticker;
  document.getElementById('bc_ticker2').textContent = idea.ticker;
  document.getElementById('bc_price').textContent = fmtMoney(idea.price);
  document.getElementById('bc_amount').value = opts.amount!=null ? opts.amount : 1000;
  document.getElementById('bc_stop').value = idea.stop!=null ? idea.stop : '';
  document.getElementById('bc_target').value = idea.target!=null ? idea.target : '';
  updateBuyConfirmShares();
  document.getElementById('buyConfirmModal').style.display='flex';
}
function closeBuyConfirmModal(){
  document.getElementById('buyConfirmModal').style.display='none';
  _pendingBuy=null;
}
function updateBuyConfirmShares(){
  if(!_pendingBuy) return;
  const amt=parseFloat(document.getElementById('bc_amount').value)||0;
  const price=_pendingBuy.idea.price;
  const shares = (price>0 && amt>0) ? Math.round((amt/price)*10000)/10000 : 0;
  document.getElementById('bc_shares').textContent = shares>0 ? shares+' share'+(shares===1?'':'s') : '—';
}
async function confirmBuyFromModal(){
  if(!_pendingBuy) return;
  const {idea,opts}=_pendingBuy;
  const amt=parseFloat(document.getElementById('bc_amount').value);
  if(!amt||amt<=0){alert('Enter a valid dollar amount.');return;}
  const stopVal=parseFloat(document.getElementById('bc_stop').value);
  const targetVal=parseFloat(document.getElementById('bc_target').value);
  const stopPrice=(!isNaN(stopVal)&&stopVal>0)?stopVal:null;
  const targetPrice=(!isNaN(targetVal)&&targetVal>0)?targetVal:null;
  try{
    const {data,sha}=await readPortfolio();
    const openCost=(data.paper_trades||[]).filter(t=>t.status==='open'&&(t.meta||{}).strategy===IDEAS_STRATEGY)
      .reduce((sum,t)=>sum+t.shares*t.buy_price,0);
    if(openCost+amt>IDEAS_BUDGET){alert('That would exceed the $'+IDEAS_BUDGET.toLocaleString()+' Trade Ideas budget ($'+openCost.toFixed(2)+' already deployed).');return;}
    const shares=Math.round((amt/idea.price)*10000)/10000;
    if(shares<=0){alert('Amount too small.');return;}
    const trade={ticker:idea.ticker, shares, buy_price:idea.price, buy_date:new Date().toISOString().slice(0,10),
      signal:idea.recommendation||'DAY_BUY', reason:idea.reason||'Trade Ideas suggestion',
      status:'open', type:'paper', stop_price:stopPrice, target_price:targetPrice,
      meta:{strategy:IDEAS_STRATEGY, entry_type:idea.entry_type, confidence:idea.confidence, blended_score:idea.blended_score, source:idea.source||'nightly'}};
    (data.paper_trades=data.paper_trades||[]).push(trade);
    await writePortfolio(data,sha);
    closeBuyConfirmModal();
    if(opts && typeof opts.onConfirmed==='function') opts.onConfirmed();
    alert(idea.ticker+' bought: '+shares+' shares @ $'+idea.price+' ($'+amt.toFixed(2)+')'
      +(stopPrice!=null?' | stop $'+stopPrice:'')+(targetPrice!=null?' | target $'+targetPrice:''));
    renderSuggestionsTab();
  }catch(e){alert('Error: '+e.message);}
}
async function buyIdea(ticker){
  const s=(SUGGESTIONS_DATA||[]).find(x=>x.ticker===ticker);
  if(!s){alert('No data for '+ticker);return;}
  // Trade Ideas standardizes on a flat -5% stop across every source (nightly, live
  // scan, Cycle Trading candidates) rather than each source's own varied stop logic
  // (ATR-based here, HCL-based for Cycle Trading, etc.) -- one simple, consistent
  // risk rule for this specifically discretionary/manual system.
  executeIdeaBuy({ticker:s.ticker, price:s.price, stop:tradeIdeasStop(s.price), target:s.take_profit,
    recommendation:s.recommendation, reason:(s.reasons||[]).slice(0,2).join('; '),
    entry_type:s.entry_type, confidence:s.confidence, blended_score:s.blended_score, source:'nightly'});
}
async function buyLiveIdea(ticker){
  const s=(_liveIdeas||[]).find(x=>x.ticker===ticker);
  if(!s){alert('No live scan data for '+ticker);return;}
  executeIdeaBuy({ticker:s.ticker, price:s.price, stop:tradeIdeasStop(s.price), target:s.sellZone,
    recommendation:'LIVE_DAY_BUY', reason:'Live intraday scan: '+(s.vs>=0?'+':'')+s.vs.toFixed(2)+'% vs VWAP, RSI '+s.rsi.toFixed(1),
    entry_type:'Live intraday Day Buy signal', confidence:'MEDIUM', blended_score:null, source:'live_scan'});
}
async function sellIdea(ticker){ return sellPaperTrade(ticker, 'Trade Ideas'); }

// ── Manual entry: any ticker, your own price/stop/target, no suggestion needed ──
async function lookUpManualTicker(){
  const ticker=(document.getElementById('mt_ticker').value||'').trim().toUpperCase();
  const resEl=document.getElementById('mt_lookup_result');
  if(!ticker){alert('Enter a ticker first.');return;}
  if(resEl){resEl.style.color='#888';resEl.textContent='Looking up '+ticker+'...';}
  let cur=await fetchLivePrice(ticker);
  if(cur==null) cur=getCurrentPrice(ticker);
  if(cur==null){
    if(resEl){resEl.style.color='#cc0000';resEl.textContent='Could not find a price for '+ticker+'. Check the ticker code (e.g. EOS.AX for ASX, NVDA for NASDAQ) and enter prices manually.';}
    return;
  }
  const entrySuggest=priceAtPct(cur,-1);
  const stopSuggest=tradeIdeasStop(cur);
  const targetSuggest=priceAtPct(cur,5);
  document.getElementById('mt_price').value=entrySuggest;
  document.getElementById('mt_stop').value=stopSuggest;
  document.getElementById('mt_target').value=targetSuggest;
  if(resEl){
    resEl.style.color='#4a90d9';
    resEl.innerHTML='Current price: <b>'+fmtMoney(cur)+'</b> — filled in: entry '+fmtMoney(entrySuggest)+' (-1%), stop '+fmtMoney(stopSuggest)+' (-5%), sale guide '+fmtMoney(targetSuggest)+' (+5%). Adjust any of these before buying.';
  }
}
async function addManualTrade(){
  const ticker=(document.getElementById('mt_ticker').value||'').trim().toUpperCase();
  const price=parseFloat(document.getElementById('mt_price').value);
  const amt=parseFloat(document.getElementById('mt_amount').value);
  const stopVal=parseFloat(document.getElementById('mt_stop').value);
  const targetVal=parseFloat(document.getElementById('mt_target').value);
  if(!ticker){alert('Enter a ticker.');return;}
  if(!price||price<=0){alert('Enter a valid buy price.');return;}
  if(!amt||amt<=0){alert('Enter a valid dollar amount.');return;}
  await executeIdeaBuy({
    ticker, price,
    stop: (!isNaN(stopVal)&&stopVal>0)?stopVal:null,
    target: (!isNaN(targetVal)&&targetVal>0)?targetVal:null,
    recommendation:'MANUAL_ENTRY', reason:'Manually entered', entry_type:'Manual entry',
    confidence:null, blended_score:null, source:'manual_entry',
  }, {amount:amt, onConfirmed: function(){
    document.getElementById('mt_ticker').value='';
    document.getElementById('mt_price').value='';
    document.getElementById('mt_amount').value='';
    document.getElementById('mt_stop').value='';
    document.getElementById('mt_target').value='';
  }});
}

// ── Cycle Trading candidates, surfaced here too as another idea source ──────
function renderCycleIdeas(){
  const el=document.getElementById('ideasCycleGrid');
  if(!el) return;
  const list=(CYCLE_DATA&&CYCLE_DATA.candidates)||[];
  if(!list.length){ el.innerHTML='<p style="color:#888;padding:20px">No Cycle Trading candidates tonight.</p>'; return; }
  el.innerHTML=list.map((c,i)=>{
    const col=c.cycle_score>=70?'#44bb44':c.cycle_score>=50?'#ff9900':c.cycle_score>=40?'#ff6600':'#cc0000';
    const pm=c.predicted_move||{};
    return '<div style="background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid '+(i===0?col:'#2a2a4a')+'">'
      +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
      +'<div><span style="font-size:20px;font-weight:bold;color:#fff">'+c.ticker+'</span>'
      +'<span style="color:#888;font-size:12px;margin-left:8px">'+(c.entry_zone||'—')+' ('+(c.risk||'—')+' risk)</span></div>'
      +'<span style="font-size:26px;font-weight:bold;color:'+col+'">'+c.cycle_score+'</span></div>'
      +'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;font-size:12px;text-align:center;margin-bottom:6px">'
      +'<div><div style="color:#666">Current</div><div style="color:#ccc">'+fmtMoney(getCurrentPrice(c.ticker)??c.price)+'</div></div>'
      +'<div><div style="color:#666">Stop (-5%)</div><div style="color:#cc0000">'+fmtMoney(tradeIdeasStop(c.price))+'</div></div>'
      +'<div><div style="color:#666">Target</div><div style="color:#44bb44">'+fmtMoney(pm.target_price)+'</div></div></div>'
      +'<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:6px;font-size:12px;text-align:center;margin-bottom:10px">'
      +'<div><div style="color:#666">% if sold at target</div><div style="color:'+pctAtPriceStr(c.price,pm.target_price).color+'">'+pctAtPriceStr(c.price,pm.target_price).text+'</div></div>'
      +'<div><div style="color:#666">+5% / +10%</div><div style="color:#888;font-size:11px">'+profitLevels(c.price)+'</div></div></div>'
      +'<div style="font-size:11px;color:#aaa;margin-bottom:10px">'+(c.reasons||[]).slice(0,3).join(' | ')+'</div>'
      +'<button class="btn-primary" style="padding:6px 14px;font-size:12px" onclick="buyCycleIdea(\''+c.ticker+'\')">Buy</button>'
      +' <button class="btn-primary" style="padding:6px 14px;font-size:12px;margin-left:6px" onclick="showCandidateChart(\''+c.ticker+'\')">📈 Chart</button>'
      +'</div>';
  }).join('');
}
async function buyCycleIdea(ticker){
  const c=((CYCLE_DATA&&CYCLE_DATA.candidates)||[]).find(x=>x.ticker===ticker);
  if(!c){alert('No Cycle Trading data for '+ticker);return;}
  const pm=c.predicted_move||{};
  executeIdeaBuy({ticker:c.ticker, price:c.price, stop:tradeIdeasStop(c.price), target:pm.target_price,
    recommendation:'CYCLE_'+(c.cycle_signal||'BUY'), reason:(c.reasons||[]).slice(0,2).join('; '),
    entry_type:c.entry_zone, confidence:null, blended_score:c.cycle_score, source:'cycle_trading_idea'});
}

// ── Live Day-Buy scan for Trade Ideas — same VWAP/RSI "Day Buy" definition
// already used by the Day Trading tab's live scanner. Used to fetch 15-min
// bars straight from Yahoo via a public CORS proxy on each click; that proxy
// (corsproxy.io) now requires a paid API key and rejects every request, and
// the only free alternative (Corsfix) isn't free for a live site either. So
// this now reads data/live_ideas.json, computed server-side via yfinance
// every ~30 min by live_ideas.py (see that file) -- no proxy involved at all,
// "on demand" just means "re-read the latest snapshot" rather than a fresh
// live fetch. ─────────────────────────────────────────────────────────────
let _liveIdeas=[];
async function scanMarketForIdeas(){
  const statusEl=document.getElementById('ideasScanStatus');
  if(statusEl) statusEl.textContent='Loading latest scan...';
  try{
    const r=await fetch('data/live_ideas.json?_='+Date.now());
    const data=await r.json();
    _liveIdeas=data.ideas||[];
    const asOf=data.generated_at?new Date(data.generated_at.replace(' ','T')).toLocaleTimeString('en-AU',{hour:'2-digit',minute:'2-digit'}):'—';
    if(statusEl) statusEl.textContent=(data.scanned_count||0)+' tickers scanned, '+_liveIdeas.length
      +' Day Buy signal(s) — as of '+asOf+' (refreshes every ~30 min)';
  }catch(e){
    _liveIdeas=[];
    if(statusEl) statusEl.textContent='Could not load the live scan snapshot.';
  }
  renderLiveIdeas();
}
function renderLiveIdeas(){
  const el=document.getElementById('ideasLiveGrid');
  if(!el) return;
  if(!_liveIdeas.length){ el.innerHTML='<p style="color:#888;padding:20px">No live Day Buy signals right now.</p>'; return; }
  el.innerHTML=_liveIdeas.map(s=>
    '<div style="background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid #2a2a4a">'
    +'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
    +'<span style="font-size:20px;font-weight:bold;color:#fff">'+s.ticker+'</span>'
    +'<span style="color:#00aa00;font-size:12px;font-weight:bold">LIVE DAY BUY</span></div>'
    +'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;font-size:12px;text-align:center;margin-bottom:6px">'
    +'<div><div style="color:#666">Current</div><div style="color:#ccc">'+fmtMoney(s.price)+'</div></div>'
    +'<div><div style="color:#666">Buy Zone</div><div style="color:#4a90d9">'+fmtMoney(s.buyZone)+'</div></div>'
    +'<div><div style="color:#666">Stop (-5%)</div><div style="color:#cc0000">'+fmtMoney(tradeIdeasStop(s.price))+'</div></div></div>'
    +'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;font-size:12px;text-align:center;margin-bottom:10px">'
    +'<div><div style="color:#666">Sell Zone</div><div style="color:#44bb44">'+fmtMoney(s.sellZone)+'</div></div>'
    +'<div><div style="color:#666">% if sold at target</div><div style="color:'+pctAtPriceStr(s.price,s.sellZone).color+'">'+pctAtPriceStr(s.price,s.sellZone).text+'</div></div>'
    +'<div><div style="color:#666">RSI</div><div style="color:#ccc">'+s.rsi.toFixed(1)+'</div></div></div>'
    +'<div style="font-size:11px;color:#aaa;margin-bottom:10px">'
    +'<b>Entry:</b> at/near buy zone, '+(s.vs>=0?'+':'')+s.vs.toFixed(2)+'% vs VWAP, momentum '+(s.mo>=0?'up':'down')+'<br>'
    +'<b>Exit guide:</b> stop at -5% ('+fmtMoney(tradeIdeasStop(s.price))+'), take profit near sell zone</div>'
    +'<button class="btn-primary" style="padding:6px 14px;font-size:12px" onclick="buyLiveIdea(\''+s.ticker+'\')">Buy</button>'
    +' <button class="btn-primary" style="padding:6px 14px;font-size:12px;margin-left:6px" onclick="showSimpleTradeChart(\''+s.ticker+'\','+s.buyZone+','+tradeIdeasStop(s.price)+','+s.sellZone+')">📈 Chart</button>'
    +'</div>'
  ).join('');
}

function renderEarnings(results,tickers){
    let h='<h3 style="color:#ccc;margin-bottom:15px">Earnings Reports — Next Date &amp; Last 4 Quarters</h3>';
    h+='<div class="asx-table-wrap"><table class="asx-table"><thead><tr><th>Ticker</th><th>Next Earnings</th><th>Q1</th><th>Q2</th><th>Q3</th><th>Q4</th></tr></thead><tbody>';
    tickers.forEach(t=>{
        const e=(results[t]||{}).earnings||{};
        const hist=e.history||[];
        h+=`<tr><td><b>${t}</b></td><td style="color:#4a90d9">${e.next_earnings||'N/A'}</td>`;
        for(let i=0;i<4;i++){
            const q=hist[i]||{};
            const surp=(q.actual!=null&&q.estimate)?((q.actual-q.estimate)/Math.abs(q.estimate)*100).toFixed(1):null;
            const sc=surp>0?'#44bb44':surp<0?'#cc0000':'#888';
            h+=`<td style="font-size:11px">${q.date?q.date.substring(0,7):'—'}<br>`;
            h+=`A:<b>${q.actual!=null?q.actual.toFixed(2):'—'}</b> E:${q.estimate!=null?q.estimate.toFixed(2):'—'}`;
            if(surp!==null)h+=` <span style="color:${sc}">${surp>0?'+':''}${surp}%</span>`;
            h+='</td>';
        }
        h+='</tr>';
    });
    h+='</tbody></table></div>';
    document.getElementById('quantContent').innerHTML=h;
}

function renderMomentum(results,tickers){
    let h='<h3 style="color:#ccc;margin-bottom:5px">12-1 Month Momentum Strategy</h3>';
    h+='<p style="color:#888;font-size:12px;margin-bottom:15px">Momentum = 12-month return minus last-month return. BUY signal when percentile ≥ 80th across the universe (avoids reversal).</p>';
    h+='<div class="asx-table-wrap"><table class="asx-table"><thead><tr><th>Ticker</th><th>12m Return</th><th>1m Return</th><th>Momentum Score</th><th>Percentile</th><th>Signal</th></tr></thead><tbody>';
    const sorted=[...tickers].sort((a,b)=>((results[b]||{}).momentum?.momentum||0)-((results[a]||{}).momentum?.momentum||0));
    sorted.forEach(t=>{
        const m=(results[t]||{}).momentum||{};
        if(m.error){h+=`<tr><td><b>${t}</b></td><td colspan="5" style="color:#666">${m.error}</td></tr>`;return;}
        const rc12=m.ret_12m>=0?'#44bb44':'#cc0000'; const rc1=m.ret_1m>=0?'#44bb44':'#cc0000';
        const rcp=m.percentile>=80?'#44bb44':m.percentile>=50?'#ff9900':'#cc0000';
        const sc=m.signal==='BUY'?'background:#44bb44;color:white':m.signal==='WATCH'?'background:#ff9900;color:white':'background:#333;color:#aaa';
        h+=`<tr><td><b>${t}</b></td>
            <td style="color:${rc12}">${m.ret_12m>=0?'+':''}${(m.ret_12m||0).toFixed(1)}%</td>
            <td style="color:${rc1}">${m.ret_1m>=0?'+':''}${(m.ret_1m||0).toFixed(1)}%</td>
            <td style="font-weight:bold">${(m.momentum||0).toFixed(1)}</td>
            <td style="color:${rcp}">${(m.percentile||0).toFixed(0)}th</td>
            <td><span style="padding:2px 8px;border-radius:4px;font-size:11px;${sc}">${m.signal||'?'}</span></td></tr>`;
    });
    h+='</tbody></table></div>';
    document.getElementById('quantContent').innerHTML=h;
}

function renderRSIStrategy(results,tickers){
    let h='<h3 style="color:#ccc;margin-bottom:5px">RSI Crossover Strategy Backtest</h3>';
    h+='<p style="color:#888;font-size:12px;margin-bottom:15px">Buy when RSI crosses above 30 (oversold recovery). Win rate = % of signals where price was higher 20 days later.</p>';
    h+='<div class="asx-table-wrap"><table class="asx-table"><thead><tr><th>Ticker</th><th>Current RSI</th><th>Buy Signals Tested</th><th>Win Rate</th><th>Wins</th><th>Recent Signals</th></tr></thead><tbody>';
    tickers.forEach(t=>{
        const r=(results[t]||{}).rsi_strategy||{};
        if(r.error){h+=`<tr><td><b>${t}</b></td><td colspan="5" style="color:#666">${r.error}</td></tr>`;return;}
        const rc=r.current_rsi<30?'#44bb44':r.current_rsi>70?'#cc0000':'#ccc';
        const wc=(r.win_rate||0)>=60?'#44bb44':(r.win_rate||0)>=50?'#ff9900':'#cc0000';
        const sigs=(r.signals||[]).slice(-3).map(s=>`<span style="font-size:10px;padding:1px 5px;border-radius:3px;${s.type==='BUY'?'background:#224422;color:#44bb44':'background:#440000;color:#cc0000'}">${s.type} ${(s.date||'').substring(5)}</span>`).join(' ');
        h+=`<tr><td><b>${t}</b></td>
            <td style="color:${rc};font-weight:bold">${(r.current_rsi||50).toFixed(0)}</td>
            <td>${r.total_signals||0}</td>
            <td style="color:${wc};font-weight:bold">${r.win_rate!=null?r.win_rate+'%':'N/A'}</td>
            <td>${r.wins||0}</td>
            <td>${sigs||'—'}</td></tr>`;
    });
    h+='</tbody></table></div>';
    document.getElementById('quantContent').innerHTML=h;
}

function _sigBadges(signals){
    return (signals||[]).slice(-3).map(s=>`<span style="font-size:10px;padding:1px 5px;border-radius:3px;${s.type==='BUY'?'background:#224422;color:#44bb44':'background:#440000;color:#cc0000'}">${s.type} ${(s.date||'').substring(5)}</span>`).join(' ')||'—';
}
function _winRateCell(r){
    const wc=(r.win_rate||0)>=60?'#44bb44':(r.win_rate||0)>=50?'#ff9900':'#cc0000';
    return `<td>${r.total_signals||0}</td><td style="color:${wc};font-weight:bold">${r.win_rate!=null?r.win_rate+'%':'N/A'}</td><td>${r.wins||0}</td>`;
}

function renderMACD(results,tickers){
    let h='<h3 style="color:#ccc;margin-bottom:5px">MACD (Moving Average Convergence Divergence)</h3>';
    h+='<p style="color:#888;font-size:12px;margin-bottom:15px">Buy when the MACD line crosses above its signal line. Win rate = % of signals where price was higher 20 days later.</p>';
    h+='<div class="asx-table-wrap"><table class="asx-table"><thead><tr><th>Ticker</th><th>MACD</th><th>Signal</th><th>Histogram</th><th>State</th><th>Buy Signals Tested</th><th>Win Rate</th><th>Wins</th><th>Recent Signals</th></tr></thead><tbody>';
    tickers.forEach(t=>{
        const r=(results[t]||{}).macd||{};
        if(r.error){h+=`<tr><td><b>${t}</b></td><td colspan="8" style="color:#666">${r.error}</td></tr>`;return;}
        const sc=r.state==='BULLISH_CROSS'?'#44bb44':r.state==='BEARISH_CROSS'?'#cc0000':r.state==='ABOVE_SIGNAL'?'#88cc44':'#ff9900';
        h+=`<tr><td><b>${t}</b></td>
            <td>${(r.macd!=null?r.macd:0).toFixed(4)}</td>
            <td>${(r.signal!=null?r.signal:0).toFixed(4)}</td>
            <td style="color:${(r.histogram||0)>=0?'#44bb44':'#cc0000'}">${(r.histogram!=null?r.histogram:0).toFixed(4)}</td>
            <td style="color:${sc};font-weight:bold">${(r.state||'').replace(/_/g,' ')}</td>
            ${_winRateCell(r)}
            <td>${_sigBadges(r.signals)}</td></tr>`;
    });
    h+='</tbody></table></div>';
    document.getElementById('quantContent').innerHTML=h;
}

function renderStochastic(results,tickers){
    let h='<h3 style="color:#ccc;margin-bottom:5px">Stochastic Oscillator</h3>';
    h+='<p style="color:#888;font-size:12px;margin-bottom:15px">Tracks close price relative to its recent high-low range -- faster than RSI, useful for spotting quick overbought/oversold turns in choppy markets. Buy when %K crosses above %D from below 20.</p>';
    h+='<div class="asx-table-wrap"><table class="asx-table"><thead><tr><th>Ticker</th><th>%K</th><th>%D</th><th>State</th><th>Buy Signals Tested</th><th>Win Rate</th><th>Wins</th><th>Recent Signals</th></tr></thead><tbody>';
    tickers.forEach(t=>{
        const r=(results[t]||{}).stochastic||{};
        if(r.error){h+=`<tr><td><b>${t}</b></td><td colspan="7" style="color:#666">${r.error}</td></tr>`;return;}
        const sc=r.state==='OVERSOLD'?'#44bb44':r.state==='OVERBOUGHT'?'#cc0000':'#ccc';
        h+=`<tr><td><b>${t}</b></td>
            <td>${(r.k!=null?r.k:50).toFixed(1)}</td>
            <td>${(r.d!=null?r.d:50).toFixed(1)}</td>
            <td style="color:${sc};font-weight:bold">${r.state||'—'}</td>
            ${_winRateCell(r)}
            <td>${_sigBadges(r.signals)}</td></tr>`;
    });
    h+='</tbody></table></div>';
    document.getElementById('quantContent').innerHTML=h;
}

function renderEMA(results,tickers){
    let h='<h3 style="color:#ccc;margin-bottom:5px">EMA (9 / 21 / 50)</h3>';
    h+='<p style="color:#888;font-size:12px;margin-bottom:15px">Short-term traders lean on the 9/21/50-period EMAs -- they weight recent price action more heavily than a simple MA, so they react faster to reversals. Buy signal = fast 9-EMA crossing above the 21-EMA.</p>';
    h+='<div class="asx-table-wrap"><table class="asx-table"><thead><tr><th>Ticker</th><th>Price</th><th>EMA9</th><th>EMA21</th><th>EMA50</th><th>Trend</th><th>Buy Signals Tested</th><th>Win Rate</th><th>Wins</th><th>Recent Signals</th></tr></thead><tbody>';
    tickers.forEach(t=>{
        const r=(results[t]||{}).ema||{};
        if(r.error){h+=`<tr><td><b>${t}</b></td><td colspan="9" style="color:#666">${r.error}</td></tr>`;return;}
        const tc=r.trend==='STRONG_UPTREND'?'#44bb44':r.trend==='STRONG_DOWNTREND'?'#cc0000':r.trend==='SHORT_TERM_BULLISH'?'#88cc44':'#ff9900';
        h+=`<tr><td><b>${t}</b></td>
            <td>$${(r.price||0).toFixed(3)}</td>
            <td style="color:${r.price>r.ema9?'#44bb44':'#cc0000'}">$${(r.ema9||0).toFixed(3)}</td>
            <td style="color:${r.price>r.ema21?'#44bb44':'#cc0000'}">$${(r.ema21||0).toFixed(3)}</td>
            <td style="color:${r.price>r.ema50?'#44bb44':'#cc0000'}">$${(r.ema50||0).toFixed(3)}</td>
            <td style="color:${tc};font-weight:bold">${(r.trend||'').replace(/_/g,' ')}</td>
            ${_winRateCell(r)}
            <td>${_sigBadges(r.signals)}</td></tr>`;
    });
    h+='</tbody></table></div>';
    document.getElementById('quantContent').innerHTML=h;
}

function renderVWAP(results,tickers){
    let h='<h3 style="color:#ccc;margin-bottom:5px">VWAP (20-Day Rolling, Daily Chart)</h3>';
    h+='<p style="color:#888;font-size:12px;margin-bottom:15px">'
      +'The true intraday session VWAP (from 1-min bars) already drives entries on the '
      +'<a href="#" onclick="showTab(\'intraday\');return false" style="color:#4a90d9">Day Trading</a> tab and Agent Trader. '
      +'This tab works from 2 years of daily bars, where a single session doesn\'t apply -- so this is a 20-day '
      +'rolling volume-weighted average price instead: same "price crossing above VWAP = bullish" read, on a daily-chart timeframe.</p>';
    h+='<div class="asx-table-wrap"><table class="asx-table"><thead><tr><th>Ticker</th><th>Price</th><th>20d VWAP</th><th>vs VWAP</th><th>State</th><th>Buy Signals Tested</th><th>Win Rate</th><th>Wins</th><th>Recent Signals</th></tr></thead><tbody>';
    tickers.forEach(t=>{
        const r=(results[t]||{}).vwap||{};
        if(r.error){h+=`<tr><td><b>${t}</b></td><td colspan="8" style="color:#666">${r.error}</td></tr>`;return;}
        const sc=r.state==='ABOVE_VWAP'?'#44bb44':r.state==='BELOW_VWAP'?'#cc0000':'#888';
        h+=`<tr><td><b>${t}</b></td>
            <td>$${(r.price||0).toFixed(3)}</td>
            <td>${r.vwap!=null?'$'+r.vwap.toFixed(3):'—'}</td>
            <td style="color:${(r.vs_vwap_pct||0)>=0?'#44bb44':'#cc0000'}">${r.vs_vwap_pct!=null?(r.vs_vwap_pct>=0?'+':'')+r.vs_vwap_pct+'%':'—'}</td>
            <td style="color:${sc};font-weight:bold">${(r.state||'').replace(/_/g,' ')}</td>
            ${_winRateCell(r)}
            <td>${_sigBadges(r.signals)}</td></tr>`;
    });
    h+='</tbody></table></div>';
    document.getElementById('quantContent').innerHTML=h;
}

function renderMAStrategy(results,tickers){
    let h='<h3 style="color:#ccc;margin-bottom:5px">Moving Average Crossover</h3>';
    h+='<p style="color:#888;font-size:12px;margin-bottom:15px">Golden cross = 50MA above 200MA (bullish). Avg 60-day return measured after each historical golden cross.</p>';
    h+='<div class="asx-table-wrap"><table class="asx-table"><thead><tr><th>Ticker</th><th>Price</th><th>MA50</th><th>MA200</th><th>Trend</th><th>Last Cross</th><th>Days Since</th><th>Hist Avg 60d Return</th></tr></thead><tbody>';
    tickers.forEach(t=>{
        const m=(results[t]||{}).ma_strategy||{};
        if(m.error){h+=`<tr><td><b>${t}</b></td><td colspan="7" style="color:#666">${m.error}</td></tr>`;return;}
        const tc=m.trend==='UPTREND'?'#44bb44':'#cc0000';
        const cc=m.cross_type==='GOLDEN'?'#44bb44':m.cross_type==='DEATH'?'#cc0000':'#888';
        const rc=(m.avg_golden_return_60d||0)>=0?'#44bb44':'#cc0000';
        h+=`<tr><td><b>${t}</b></td>
            <td>$${(m.price||0).toFixed(3)}</td>
            <td style="color:${m.price>m.ma50?'#44bb44':'#cc0000'}">$${(m.ma50||0).toFixed(3)}</td>
            <td style="color:${m.price>m.ma200?'#44bb44':'#cc0000'}">$${(m.ma200||0).toFixed(3)}</td>
            <td style="color:${tc};font-weight:bold">${m.trend||'?'}</td>
            <td style="color:${cc}">${m.cross_type||'NONE'}${m.cross_date?' ('+m.cross_date+')':''}</td>
            <td>${m.days_since_cross!=null?m.days_since_cross+'d':'—'}</td>
            <td style="color:${rc}">${m.avg_golden_return_60d!=null?(m.avg_golden_return_60d>=0?'+':'')+m.avg_golden_return_60d.toFixed(1)+'% ('+m.n_golden_crosses+' crosses)':'N/A'}</td></tr>`;
    });
    h+='</tbody></table></div>';
    document.getElementById('quantContent').innerHTML=h;
}

function renderWalkForward(results,tickers){
    let h='<h3 style="color:#ccc;margin-bottom:5px">Walk Forward Validation</h3>';
    h+='<p style="color:#888;font-size:12px;margin-bottom:15px">Optimize RSI threshold on 6-month train window → test on next 21 trading days. 5 rolling windows. Measures out-of-sample robustness.</p>';
    h+='<div class="asx-table-wrap"><table class="asx-table"><thead><tr><th>Ticker</th><th>Avg Win Rate</th><th>Win 1</th><th>Win 2</th><th>Win 3</th><th>Win 4</th><th>Win 5</th></tr></thead><tbody>';
    tickers.forEach(t=>{
        const wf=(results[t]||{}).walk_forward||{};
        if(wf.error){h+=`<tr><td><b>${t}</b></td><td colspan="6" style="color:#666">${wf.error}</td></tr>`;return;}
        const aw=wf.avg_win_rate; const awc=aw>=60?'#44bb44':aw>=50?'#ff9900':'#cc0000';
        h+=`<tr><td><b>${t}</b></td><td style="color:${awc};font-weight:bold">${aw!=null?aw+'%':'N/A'}</td>`;
        const wins=wf.windows||[];
        for(let i=0;i<5;i++){
            const w=wins[i];
            if(!w){h+='<td style="color:#555">—</td>';continue;}
            const wc=(w.win_rate||0)>=60?'#44bb44':(w.win_rate||0)>=50?'#ff9900':'#cc0000';
            h+=`<td><small style="color:#555">${(w.period||'').substring(0,10)}</small><br><span style="color:${wc}">${w.win_rate!=null?w.win_rate+'%':'—'}</span></td>`;
        }
        h+='</tr>';
    });
    h+='</tbody></table></div>';

    h+='<h3 style="color:#ccc;margin:30px 0 5px">5 Strategies — Out-of-Sample Win Rate Comparison</h3>';
    h+='<p style="color:#888;font-size:12px;margin-bottom:15px">Same walk-forward idea applied to all five crossover-signal strategies side by side, so accuracy can be compared rather than taken on faith per-tab. RSI re-optimizes its oversold threshold per window; MACD/Stochastic/EMA/VWAP test their fixed signal’s consistency across the same 4 rolling windows. (MA Crossover isn’t included here — it measures average return after a golden cross, not a per-signal win rate, so it isn’t comparable on this scale.)</p>';
    h+='<div class="asx-table-wrap"><table class="asx-table"><thead><tr><th>Ticker</th><th>RSI</th><th>MACD</th><th>Stochastic</th><th>EMA</th><th>VWAP</th></tr></thead><tbody>';
    const wfCell=(wf)=>{
        if(!wf || wf.error) return '<td style="color:#666">—</td>';
        const aw=wf.avg_win_rate;
        const c=aw==null?'#888':aw>=60?'#44bb44':aw>=50?'#ff9900':'#cc0000';
        return `<td style="color:${c};font-weight:bold">${aw!=null?aw+'%':'N/A'}</td>`;
    };
    tickers.forEach(t=>{
        const r=results[t]||{};
        h+=`<tr><td><b>${t}</b></td>`
          +wfCell(r.walk_forward)
          +wfCell(r.macd_walk_forward)
          +wfCell(r.stochastic_walk_forward)
          +wfCell(r.ema_walk_forward)
          +wfCell(r.vwap_walk_forward)
          +'</tr>';
    });
    h+='</tbody></table></div>';
    document.getElementById('quantContent').innerHTML=h;
}

function renderMonteCarlo(results,tickers){
    let h='<h3 style="color:#ccc;margin-bottom:5px">Monte Carlo Simulation — 63 Trading Day Outlook</h3>';
    h+='<p style="color:#888;font-size:12px;margin-bottom:15px">300 simulated price paths based on historical daily return distribution (μ, σ). P10/P90 = bear/bull extremes.</p>';
    h+='<div class="asx-table-wrap"><table class="asx-table"><thead><tr><th>Ticker</th><th>Current</th><th>P10 Bear</th><th>P25</th><th>P50 Median</th><th>P75</th><th>P90 Bull</th><th>Prob Up</th><th>Daily σ</th></tr></thead><tbody>';
    tickers.forEach(t=>{
        const mc=(results[t]||{}).monte_carlo||{};
        if(mc.error){h+=`<tr><td><b>${t}</b></td><td colspan="8" style="color:#666">${mc.error}</td></tr>`;return;}
        const cp=mc.current_price||0; const pu=mc.prob_up||0;
        const puc=pu>=60?'#44bb44':pu>=50?'#ff9900':'#cc0000';
        const p50c=(mc.p50||0)>cp?'#44bb44':'#cc0000';
        h+=`<tr><td><b>${t}</b></td>
            <td>$${cp.toFixed(3)}</td>
            <td style="color:#cc0000">$${(mc.p10||0).toFixed(3)}</td>
            <td style="color:#ff9900">$${(mc.p25||0).toFixed(3)}</td>
            <td style="color:${p50c};font-weight:bold">$${(mc.p50||0).toFixed(3)}</td>
            <td style="color:#ff9900">$${(mc.p75||0).toFixed(3)}</td>
            <td style="color:#44bb44">$${(mc.p90||0).toFixed(3)}</td>
            <td style="color:${puc};font-weight:bold">${pu.toFixed(0)}%</td>
            <td style="color:#888">${(mc.sigma_daily||0).toFixed(2)}%</td></tr>`;
    });
    h+='</tbody></table></div>';
    document.getElementById('quantContent').innerHTML=h;
}

function renderSensitivity(results,tickers){
    let h='<h3 style="color:#ccc;margin-bottom:5px">Sensitivity Analysis</h3>';
    h+='<p style="color:#888;font-size:12px;margin-bottom:10px">Score stability across RSI periods (7/10/14/21) and MA pairs. Small range = robust signal. Large range = parameter-sensitive.</p>';
    h+='<div style="display:flex;gap:10px;align-items:center;margin-bottom:15px"><label style="color:#aaa">Stock: </label>';
    h+='<select id="sensSelect" onchange="renderSensGrid()" style="background:#1e1e3a;color:#ccc;border:1px solid #444;padding:6px;border-radius:6px">';
    tickers.forEach(t=>{h+=`<option value="${t}">${t}</option>`;});
    h+='</select></div><div id="sensGrid"></div>';
    h+='<h3 style="color:#ccc;margin:20px 0 10px">Robustness Summary</h3>';
    h+='<div class="asx-table-wrap"><table class="asx-table"><thead><tr><th>Ticker</th><th>Mean Score</th><th>Min</th><th>Max</th><th>Range</th><th>Robustness</th></tr></thead><tbody>';
    tickers.forEach(t=>{
        const s=(results[t]||{}).sensitivity||{};
        if(s.error)return;
        const rng=s.score_range||0; const rc=rng<=10?'#44bb44':rng<=20?'#ff9900':'#cc0000';
        const rob=rng<=10?'HIGH':rng<=20?'MEDIUM':'LOW';
        h+=`<tr><td><b>${t}</b></td>
            <td style="font-weight:bold">${(s.score_mean||0).toFixed(0)}</td>
            <td>${s.score_min||0}</td><td>${s.score_max||0}</td>
            <td style="color:${rc}">${rng.toFixed(0)} pts</td>
            <td style="color:${rc};font-weight:bold">${rob}</td></tr>`;
    });
    h+='</tbody></table></div>';
    document.getElementById('quantContent').innerHTML=h;
    setTimeout(()=>renderSensGrid(),50);
}

function renderSensGrid(){
    const t=(document.getElementById('sensSelect')||{value:''}).value;
    const s=(QUANT_DATA.results||QUANT_DATA||{})[t]?.sensitivity||{};
    const grid=s.grid||[];
    if(!grid.length)return;
    const rsiPs=[...new Set(grid.map(r=>r.rsi_period))];
    const maCombos=[...new Set(grid.map(r=>r.ma_short+'d/'+r.ma_long+'d'))];
    let h=`<p style="color:#aaa;font-size:12px;margin-bottom:8px">Score grid for <b>${t}</b>:</p>`;
    h+='<table class="asx-table"><thead><tr><th>RSI Period</th>';
    maCombos.forEach(c=>{h+=`<th>MA ${c}</th>`;});
    h+='</tr></thead><tbody>';
    rsiPs.forEach(rp=>{
        h+=`<tr><td>RSI ${rp}</td>`;
        maCombos.forEach(c=>{
            const [sh,lo]=c.split('/').map(v=>parseInt(v));
            const cell=grid.find(r=>r.rsi_period===rp&&r.ma_short===sh&&r.ma_long===lo);
            if(!cell){h+='<td>—</td>';return;}
            const sc=cell.score>=70?'#44bb44':cell.score>=55?'#ff9900':cell.score<=40?'#cc0000':'#ccc';
            h+=`<td style="color:${sc};font-weight:bold;text-align:center">${cell.score}</td>`;
        });
        h+='</tr>';
    });
    h+='</tbody></table>';
    document.getElementById('sensGrid').innerHTML=h;
}

window.addEventListener('resize',()=>{
    if(_chart){_chart.resize(document.getElementById('chartContainer').clientWidth,380);}
    if(_rsiChart){_rsiChart.resize(document.getElementById('rsiContainer').clientWidth,100);}
});
</script>"""

    # Replace placeholders safely after the raw string
    JS=JS.replace("__CHART_DATA__", chart_data_json)
    JS=JS.replace("__ASX_SCAN__", asx_scan_json)
    JS=JS.replace("__WATCHLIST__", watchlist_json)
    JS=JS.replace("__SIGNAL_HISTORY__", history_json)
    # _SIDE_PANEL_APPENDED — do not remove this comment
    import base64 as _b64_sp
    JS += _b64_sp.b64decode(
        b'CjwhLS0gU3RvY2sgRGV0YWlsIFNpZGUgUGFuZWwgLS0+CjxkaXYgaWQ9InN0b2NrLXNpZGUtcGFuZWwiIHN0eWxlPSJwb3NpdGlvbjpmaXhlZDtyaWdodDowO3RvcDowO2hlaWdodDoxMDAlO3dpZHRoOjUwMHB4O21heC13aWR0aDo5NnZ3O2JhY2tncm91bmQ6IzBkMGQxYTtib3JkZXItbGVmdDoxcHggc29saWQgIzJhMmE0YTt6LWluZGV4OjEwMDA7dHJhbnNmb3JtOnRyYW5zbGF0ZVgoMTAwJSk7dHJhbnNpdGlvbjp0cmFuc2Zvcm0gMC4zcyBlYXNlO292ZXJmbG93LXk6YXV0bztwYWRkaW5nOjIwcHg7Ym94LXNpemluZzpib3JkZXItYm94O2JveC1zaGFkb3c6LTRweCAwIDIwcHggcmdiYSgwLDAsMCwwLjUpIj4KICA8ZGl2IHN0eWxlPSJkaXNwbGF5OmZsZXg7anVzdGlmeS1jb250ZW50OnNwYWNlLWJldHdlZW47YWxpZ24taXRlbXM6Y2VudGVyO21hcmdpbi1ib3R0b206MTZweDtwYWRkaW5nLWJvdHRvbToxMnB4O2JvcmRlci1ib3R0b206MXB4IHNvbGlkICMyYTJhNGEiPgogICAgPGRpdj4KICAgICAgPGgzIGlkPSJwYW5lbC10aWNrZXItbmFtZSIgc3R5bGU9ImNvbG9yOndoaXRlO2ZvbnQtc2l6ZToyMHB4O21hcmdpbjowO2ZvbnQtd2VpZ2h0OmJvbGQiPi08L2gzPgogICAgICA8ZGl2IGlkPSJwYW5lbC10aWNrZXItcHJpY2UiIHN0eWxlPSJjb2xvcjojODg4O2ZvbnQtc2l6ZToxM3B4O21hcmdpbi10b3A6MnB4Ij48L2Rpdj4KICAgIDwvZGl2PgogICAgPGJ1dHRvbiBvbmNsaWNrPSJjbG9zZVN0b2NrUGFuZWwoKSIgc3R5bGU9ImJhY2tncm91bmQ6bm9uZTtib3JkZXI6bm9uZTtjb2xvcjojODg4O2ZvbnQtc2l6ZToyNHB4O2N1cnNvcjpwb2ludGVyO3BhZGRpbmc6MDtsaW5lLWhlaWdodDoxIj54PC9idXR0b24+CiAgPC9kaXY+CiAgPGRpdiBzdHlsZT0iZGlzcGxheTpmbGV4O2dhcDo0cHg7bWFyZ2luLWJvdHRvbToxNnB4O2ZsZXgtd3JhcDp3cmFwIj4KICAgIDxidXR0b24gaWQ9InB0YWItcHJlZGljdGlvbiIgb25jbGljaz0ic2hvd1BhbmVsVGFiKCdwcmVkaWN0aW9uJykiIHN0eWxlPSJwYWRkaW5nOjVweCAxMHB4O2ZvbnQtc2l6ZToxMnB4O2JvcmRlcjoxcHggc29saWQgIzNhM2E2YTtib3JkZXItcmFkaXVzOjRweDtjdXJzb3I6cG9pbnRlcjtiYWNrZ3JvdW5kOiMyYTJhNGE7Y29sb3I6IzRhOTBkOSI+UHJlZGljdGlvbjwvYnV0dG9uPgogICAgPGJ1dHRvbiBpZD0icHRhYi1kaXZpZGVuZHMiIG9uY2xpY2s9InNob3dQYW5lbFRhYignZGl2aWRlbmRzJykiIHN0eWxlPSJwYWRkaW5nOjVweCAxMHB4O2ZvbnQtc2l6ZToxMnB4O2JvcmRlcjoxcHggc29saWQgIzJhMmEzYTtib3JkZXItcmFkaXVzOjRweDtjdXJzb3I6cG9pbnRlcjtiYWNrZ3JvdW5kOiMxYTFhMmU7Y29sb3I6Izg4OCI+RGl2aWRlbmRzPC9idXR0b24+CiAgICA8YnV0dG9uIGlkPSJwdGFiLWFuYWx5c3QiIG9uY2xpY2s9InNob3dQYW5lbFRhYignYW5hbHlzdCcpIiBzdHlsZT0icGFkZGluZzo1cHggMTBweDtmb250LXNpemU6MTJweDtib3JkZXI6MXB4IHNvbGlkICMyYTJhM2E7Ym9yZGVyLXJhZGl1czo0cHg7Y3Vyc29yOnBvaW50ZXI7YmFja2dyb3VuZDojMWExYTJlO2NvbG9yOiM4ODgiPkFuYWx5c3Q8L2J1dHRvbj4KICAgIDxidXR0b24gaWQ9InB0YWItbmV3cyIgb25jbGljaz0ic2hvd1BhbmVsVGFiKCduZXdzJykiIHN0eWxlPSJwYWRkaW5nOjVweCAxMHB4O2ZvbnQtc2l6ZToxMnB4O2JvcmRlcjoxcHggc29saWQgIzJhMmEzYTtib3JkZXItcmFkaXVzOjRweDtjdXJzb3I6cG9pbnRlcjtiYWNrZ3JvdW5kOiMxYTFhMmU7Y29sb3I6Izg4OCI+TmV3czwvYnV0dG9uPgogIDwvZGl2PgogIDxkaXYgaWQ9InBhbmVsLXByZWRpY3Rpb24iPjxwIHN0eWxlPSJjb2xvcjojODg4Ij5Mb2FkaW5nLi4uPC9wPjwvZGl2PgogIDxkaXYgaWQ9InBhbmVsLWRpdmlkZW5kcyIgc3R5bGU9ImRpc3BsYXk6bm9uZSI+PHAgc3R5bGU9ImNvbG9yOiM4ODgiPkxvYWRpbmcuLi48L3A+PC9kaXY+CiAgPGRpdiBpZD0icGFuZWwtYW5hbHlzdCIgc3R5bGU9ImRpc3BsYXk6bm9uZSI+PHAgc3R5bGU9ImNvbG9yOiM4ODgiPkxvYWRpbmcuLi48L3A+PC9kaXY+CiAgPGRpdiBpZD0icGFuZWwtbmV3cyIgc3R5bGU9ImRpc3BsYXk6bm9uZSI+PHAgc3R5bGU9ImNvbG9yOiM4ODgiPkxvYWRpbmcuLi48L3A+PC9kaXY+CjwvZGl2Pgo8ZGl2IGlkPSJwYW5lbC1vdmVybGF5IiBvbmNsaWNrPSJjbG9zZVN0b2NrUGFuZWwoKSIgc3R5bGU9ImRpc3BsYXk6bm9uZTtwb3NpdGlvbjpmaXhlZDtpbnNldDowO2JhY2tncm91bmQ6cmdiYSgwLDAsMCwwLjQpO3otaW5kZXg6OTk5Ij48L2Rpdj4KCjxzY3JpcHQ+CmFzeW5jIGZ1bmN0aW9uIGZldGNoTGl2ZVByaWNlKHRpY2tlcil7CiAgdHJ5ewogICAgY29uc3QgdXJsPSdodHRwczovL2NvcnNwcm94eS5pby8/dXJsPScrZW5jb2RlVVJJQ29tcG9uZW50KCdodHRwczovL3F1ZXJ5MS5maW5hbmNlLnlhaG9vLmNvbS92OC9maW5hbmNlL2NoYXJ0LycrdGlja2VyKyc/aW50ZXJ2YWw9MWQmcmFuZ2U9MTVkJyk7CiAgICBjb25zdCByPWF3YWl0IGZldGNoKHVybCk7Y29uc3Qgaj1hd2FpdCByLmpzb24oKTsKICAgIHJldHVybiBqLmNoYXJ0LnJlc3VsdFswXS5tZXRhLnJlZ3VsYXJNYXJrZXRQcmljZTsKICB9Y2F0Y2goZSl7cmV0dXJuIG51bGw7fQp9CmFzeW5jIGZ1bmN0aW9uIGZldGNoNURheUhpc3RvcnkodGlja2VyKXsKICB0cnl7CiAgICBjb25zdCB1cmw9J2h0dHBzOi8vY29yc3Byb3h5LmlvLz91cmw9JytlbmNvZGVVUklDb21wb25lbnQoJ2h0dHBzOi8vcXVlcnkxLmZpbmFuY2UueWFob28uY29tL3Y4L2ZpbmFuY2UvY2hhcnQvJyt0aWNrZXIrJz9pbnRlcnZhbD0xZCZyYW5nZT0xNWQnKTsKICAgIGNvbnN0IHI9YXdhaXQgZmV0Y2godXJsKTtjb25zdCBqPWF3YWl0IHIuanNvbigpOwogICAgY29uc3QgcmVzPWouY2hhcnQucmVzdWx0WzBdOwogICAgY29uc3QgdHM9cmVzLnRpbWVzdGFtcCxjbD1yZXMuaW5kaWNhdG9ycy5xdW90ZVswXS5jbG9zZTsKICAgIHJldHVybiB0cy5tYXAoZnVuY3Rpb24odCxpKXtyZXR1cm57ZDpuZXcgRGF0ZSh0KjEwMDApLnRvTG9jYWxlRGF0ZVN0cmluZygnZW4tQVUnLHt3ZWVrZGF5OidzaG9ydCcsZGF5OidudW1lcmljJ30pLGM6Y2xbaV19O30pLmZpbHRlcihmdW5jdGlvbih4KXtyZXR1cm4geC5jIT1udWxsO30pLnNsaWNlKC01KTsKICB9Y2F0Y2goZSl7cmV0dXJuIG51bGw7fQp9CmZ1bmN0aW9uIHNwYXJrbGluZVNWRyhwcmljZXMsaXNVcCl7CiAgaWYoIXByaWNlc3x8cHJpY2VzLmxlbmd0aDwyKSByZXR1cm4gJzxzcGFuIHN0eWxlPSJjb2xvcjojNTU1Ij4tPC9zcGFuPic7CiAgdmFyIHZhbHM9cHJpY2VzLm1hcChmdW5jdGlvbihwKXtyZXR1cm4gcC5jO30pOwogIHZhciBtbj1NYXRoLm1pbi5hcHBseShudWxsLHZhbHMpLG14PU1hdGgubWF4LmFwcGx5KG51bGwsdmFscykscm5nPShteC1tbil8fDAuMDE7CiAgdmFyIFc9NzAsSD0yNjsKICB2YXIgcHRzPXZhbHMubWFwKGZ1bmN0aW9uKHYsaSl7cmV0dXJuKChpLyh2YWxzLmxlbmd0aC0xKSkqVykudG9GaXhlZCgxKSsnLCcrKEgtKHYtbW4pL3JuZypIKjAuOC1IKjAuMSkudG9GaXhlZCgxKTt9KS5qb2luKCcgJyk7CiAgdmFyIGNvbG9yPWlzVXA/JyM0NGJiNDQnOicjY2MwMDAwJzsKICByZXR1cm4gJzxkaXYgc3R5bGU9ImRpc3BsYXk6ZmxleDthbGlnbi1pdGVtczpjZW50ZXI7Z2FwOjRweCI+PHN2ZyB3aWR0aD0iJytXKyciIGhlaWdodD0iJytIKyciPjxwb2x5bGluZSBwb2ludHM9IicrcHRzKyciIGZpbGw9Im5vbmUiIHN0cm9rZT0iJytjb2xvcisnIiBzdHJva2Utd2lkdGg9IjEuNSIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPjxzcGFuIHN0eWxlPSJmb250LXNpemU6MTBweDtjb2xvcjojODg4Ij4kJyt2YWxzW3ZhbHMubGVuZ3RoLTFdLnRvRml4ZWQoMikrJzwvc3Bhbj48L2Rpdj4nOwp9CmFzeW5jIGZ1bmN0aW9uIHJlZnJlc2hQb3J0Zm9saW9QcmljZXMoKXsKICB2YXIgdGJvZHk9ZG9jdW1lbnQucXVlcnlTZWxlY3RvcignI3RhYi1wb3J0Zm9saW8gLmhvbGRpbmdzLXRhYmxlIHRib2R5Jyk7CiAgaWYoIXRib2R5KSByZXR1cm47CiAgdmFyIHJvd3M9W10uc2xpY2UuY2FsbCh0Ym9keS5xdWVyeVNlbGVjdG9yQWxsKCd0cicpKTsKICBpZighcm93cy5sZW5ndGgpIHJldHVybjsKICB2YXIgaDI9ZG9jdW1lbnQucXVlcnlTZWxlY3RvcignI3RhYi1wb3J0Zm9saW8gLnNlY3Rpb24gaDInKTsKICB2YXIgaW5kPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdwb3J0LWxpdmUtaW5kJyk7CiAgaWYoIWluZCl7aW5kPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoJ3NwYW4nKTtpbmQuaWQ9J3BvcnQtbGl2ZS1pbmQnO2luZC5zdHlsZS5jc3NUZXh0PSdmb250LXNpemU6MTJweDtjb2xvcjojODg4O21hcmdpbi1sZWZ0OjEycHg7JztoMi5hcHBlbmRDaGlsZChpbmQpO30KICBpbmQudGV4dENvbnRlbnQ9J2ZldGNoaW5nIGxpdmUgcHJpY2VzLi4uJzsKICB2YXIgdGhlYWQ9ZG9jdW1lbnQucXVlcnlTZWxlY3RvcignI3RhYi1wb3J0Zm9saW8gLmhvbGRpbmdzLXRhYmxlIHRoZWFkIHRyJyk7CiAgaWYodGhlYWQmJnRoZWFkLmNlbGxzLmxlbmd0aDw9OSl7CiAgICBbJzUtRGF5JywnJ10uZm9yRWFjaChmdW5jdGlvbih0eHQpewogICAgICB2YXIgdGg9ZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgndGgnKTt0aC50ZXh0Q29udGVudD10eHQ7CiAgICAgIHRoZWFkLmluc2VydEJlZm9yZSh0aCx0aGVhZC5jZWxsc1t0aGVhZC5jZWxscy5sZW5ndGgtMV0pOwogICAgfSk7CiAgfQogIHZhciB0b3RhbFZhbHVlPTAsdG90YWxDb3N0PTA7CiAgdmFyIGZldGNoZXM9cm93cy5tYXAoZnVuY3Rpb24ocm93KXsKICAgIHJldHVybiAoYXN5bmMgZnVuY3Rpb24oKXsKICAgICAgdmFyIGNlbGxzPVtdLnNsaWNlLmNhbGwocm93LnF1ZXJ5U2VsZWN0b3JBbGwoJ3RkJykpOwogICAgICBpZihjZWxscy5sZW5ndGg8NikgcmV0dXJuOwogICAgICB2YXIgYkVsPWNlbGxzWzBdLnF1ZXJ5U2VsZWN0b3IoJ2InKXx8Y2VsbHNbMF07CiAgICAgIHZhciB0aWNrZXI9KGJFbC50ZXh0Q29udGVudHx8JycpLnRyaW0oKTsKICAgICAgdmFyIHNoYXJlcz1wYXJzZUZsb2F0KGNlbGxzWzFdLnRleHRDb250ZW50LnJlcGxhY2UoLywvZywnJykpfHwwOwogICAgICB2YXIgYnV5UHJpY2U9cGFyc2VGbG9hdChjZWxsc1syXS50ZXh0Q29udGVudC5yZXBsYWNlKC9bJCxdL2csJycpKXx8MDsKICAgICAgaWYoIXRpY2tlcnx8IXNoYXJlcykgcmV0dXJuOwogICAgICBpZighYkVsLl93aXJlZCl7YkVsLl93aXJlZD0xO2JFbC5zdHlsZS5jc3NUZXh0PSdjdXJzb3I6cG9pbnRlcjtjb2xvcjojNGE5MGQ5O3RleHQtZGVjb3JhdGlvbjp1bmRlcmxpbmUnO2JFbC5vbmNsaWNrPWZ1bmN0aW9uKCl7b3BlblN0b2NrUGFuZWwodGlja2VyKTt9O30KICAgICAgdmFyIHJlc3VsdHM9YXdhaXQgUHJvbWlzZS5hbGwoW2ZldGNoTGl2ZVByaWNlKHRpY2tlciksZmV0Y2g1RGF5SGlzdG9yeSh0aWNrZXIpXSk7CiAgICAgIHZhciBwcmljZT1yZXN1bHRzWzBdLGhpc3Rvcnk9cmVzdWx0c1sxXTsKICAgICAgaWYocHJpY2U9PT1udWxsKXsgcHJpY2U9cGFyc2VGbG9hdChjZWxsc1szXS50ZXh0Q29udGVudC5yZXBsYWNlKC9bJCxdL2csJycpKXx8bnVsbDsgfQogICAgICBpZihwcmljZT09PW51bGwpIHJldHVybjsKICAgICAgdmFyIHZhbHVlPXByaWNlKnNoYXJlcyxjb3N0PWJ1eVByaWNlKnNoYXJlcyxwbD12YWx1ZS1jb3N0LHBsUGN0PWNvc3Q+MD8oKHBsL2Nvc3QpKjEwMCk6MDsKICAgICAgdG90YWxWYWx1ZSs9dmFsdWU7dG90YWxDb3N0Kz1jb3N0OwogICAgICBjZWxsc1szXS50ZXh0Q29udGVudD0nJCcrcHJpY2UudG9GaXhlZCgzKTsKICAgICAgY2VsbHNbNF0udGV4dENvbnRlbnQ9JyQnK3ZhbHVlLnRvTG9jYWxlU3RyaW5nKCdlbi1BVScse21pbmltdW1GcmFjdGlvbkRpZ2l0czoyLG1heGltdW1GcmFjdGlvbkRpZ2l0czoyfSk7CiAgICAgIGNlbGxzWzVdLnN0eWxlLmNvbG9yPXBsPj0wPydncmVlbic6J3JlZCc7CiAgICAgIGNlbGxzWzVdLnRleHRDb250ZW50PShwbD49MD8nKyc6JycpKycgJCcrTWF0aC5hYnMocGwpLnRvTG9jYWxlU3RyaW5nKCdlbi1BVScse21pbmltdW1GcmFjdGlvbkRpZ2l0czoyLG1heGltdW1GcmFjdGlvbkRpZ2l0czoyfSkrJyAoJysocGw+PTA/JysnOicnKStwbFBjdC50b0ZpeGVkKDEpKyclKSc7CiAgICAgIHZhciByZW1vdmVDZWxsPXJvdy5jZWxsc1tyb3cuY2VsbHMubGVuZ3RoLTFdOwogICAgICByb3cucmVtb3ZlQ2hpbGQocmVtb3ZlQ2VsbCk7CiAgICAgIHdoaWxlKHJvdy5jZWxscy5sZW5ndGg8OCl7cm93LmFwcGVuZENoaWxkKGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoJ3RkJykpO30KICAgICAgdmFyIHNwYXJrVGQ9ZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgndGQnKTsKICAgICAgdmFyIGJ0blRkPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoJ3RkJyk7CiAgICAgIHJvdy5hcHBlbmRDaGlsZChzcGFya1RkKTtyb3cuYXBwZW5kQ2hpbGQoYnRuVGQpO3Jvdy5hcHBlbmRDaGlsZChyZW1vdmVDZWxsKTsKICAgICAgaWYoaGlzdG9yeSkgc3BhcmtUZC5pbm5lckhUTUw9c3BhcmtsaW5lU1ZHKGhpc3RvcnksaGlzdG9yeS5sZW5ndGg+PTImJnByaWNlPj1oaXN0b3J5WzBdLmMpOwogICAgICBpZighYnRuVGQucXVlcnlTZWxlY3RvcignYnV0dG9uJykpewogICAgICAgIHZhciBidG49ZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgnYnV0dG9uJyk7CiAgICAgICAgYnRuLnRleHRDb250ZW50PSdDaGFydCc7CiAgICAgICAgYnRuLnN0eWxlLmNzc1RleHQ9J3BhZGRpbmc6M3B4IDhweDtmb250LXNpemU6MTFweDtiYWNrZ3JvdW5kOiMxYTFhM2E7Ym9yZGVyOjFweCBzb2xpZCAjM2EzYTZhO2JvcmRlci1yYWRpdXM6NHB4O2NvbG9yOiM0YTkwZDk7Y3Vyc29yOnBvaW50ZXInOwogICAgICAgIGJ0bi5vbmNsaWNrPWZ1bmN0aW9uKCl7b3BlblN0b2NrUGFuZWwodGlja2VyKTt9OwogICAgICAgIGJ0blRkLmFwcGVuZENoaWxkKGJ0bik7CiAgICAgIH0KICAgIH0pKCk7CiAgfSk7CiAgYXdhaXQgUHJvbWlzZS5hbGwoZmV0Y2hlcyk7CiAgdmFyIGNhcmRzPVtdLnNsaWNlLmNhbGwoZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnI3RhYi1wb3J0Zm9saW8gLnN0YXRzLWdyaWQgLnN0YXQtdmFsdWUnKSk7CiAgaWYoY2FyZHMubGVuZ3RoPj0zICYmIHRvdGFsQ29zdD4wKXsKICAgIGNhcmRzWzBdLnRleHRDb250ZW50PSckJyt0b3RhbFZhbHVlLnRvTG9jYWxlU3RyaW5nKCdlbi1BVScse21pbmltdW1GcmFjdGlvbkRpZ2l0czoyLG1heGltdW1GcmFjdGlvbkRpZ2l0czoyfSk7CiAgICB2YXIgdG90YWxQTD10b3RhbFZhbHVlLXRvdGFsQ29zdCxwY3Q9dG90YWxDb3N0PjA/KCh0b3RhbFBML3RvdGFsQ29zdCkqMTAwKTowOwogICAgY2FyZHNbMl0uc3R5bGUuY29sb3I9dG90YWxQTD49MD8nZ3JlZW4nOidyZWQnOwogICAgY2FyZHNbMl0udGV4dENvbnRlbnQ9KHRvdGFsUEw+PTA/JysnOicnKSsnICQnK01hdGguYWJzKHRvdGFsUEwpLnRvTG9jYWxlU3RyaW5nKCdlbi1BVScse21pbmltdW1GcmFjdGlvbkRpZ2l0czoyLG1heGltdW1GcmFjdGlvbkRpZ2l0czoyfSkrJyAoJysodG90YWxQTD49MD8nKyc6JycpK3BjdC50b0ZpeGVkKDEpKyclKSc7CiAgfQogIGluZC50ZXh0Q29udGVudD0nbGl2ZSBhcyBvZiAnK25ldyBEYXRlKCkudG9Mb2NhbGVUaW1lU3RyaW5nKCdlbi1BVScse2hvdXI6JzItZGlnaXQnLG1pbnV0ZTonMi1kaWdpdCd9KTsKfQpzZXRJbnRlcnZhbChmdW5jdGlvbigpe2lmKGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCd0YWItcG9ydGZvbGlvJykmJmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCd0YWItcG9ydGZvbGlvJykuY2xhc3NMaXN0LmNvbnRhaW5zKCdhY3RpdmUnKSkgcmVmcmVzaFBvcnRmb2xpb1ByaWNlcygpO30sMTUqNjAqMTAwMCk7CmZ1bmN0aW9uIG9wZW5TdG9ja1BhbmVsKHRpY2tlcil7CiAgdmFyIHBhbmVsPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdzdG9jay1zaWRlLXBhbmVsJyk7CiAgdmFyIG92PWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdwYW5lbC1vdmVybGF5Jyk7CiAgaWYoIXBhbmVsKSByZXR1cm47CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3BhbmVsLXRpY2tlci1uYW1lJykudGV4dENvbnRlbnQ9dGlja2VyOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdwYW5lbC10aWNrZXItcHJpY2UnKS50ZXh0Q29udGVudD0nTG9hZGluZy4uLic7CiAgWydwcmVkaWN0aW9uJywnZGl2aWRlbmRzJywnYW5hbHlzdCcsJ25ld3MnXS5mb3JFYWNoKGZ1bmN0aW9uKHQpe2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdwYW5lbC0nK3QpLmlubmVySFRNTD0nPHAgc3R5bGU9ImNvbG9yOiM4ODg7cGFkZGluZzoxMnB4Ij5Mb2FkaW5nLi4uPC9wPic7fSk7CiAgcGFuZWwuc3R5bGUudHJhbnNmb3JtPSd0cmFuc2xhdGVYKDApJzsKICBpZihvdikgb3Yuc3R5bGUuZGlzcGxheT0nYmxvY2snOwogIHNob3dQYW5lbFRhYigncHJlZGljdGlvbicpOwogIGxvYWRQYW5lbERhdGEodGlja2VyKTsKfQpmdW5jdGlvbiBjbG9zZVN0b2NrUGFuZWwoKXsKICB2YXIgcGFuZWw9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3N0b2NrLXNpZGUtcGFuZWwnKTsKICB2YXIgb3Y9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3BhbmVsLW92ZXJsYXknKTsKICBpZihwYW5lbCkgcGFuZWwuc3R5bGUudHJhbnNmb3JtPSd0cmFuc2xhdGVYKDEwMCUpJzsKICBpZihvdikgb3Yuc3R5bGUuZGlzcGxheT0nbm9uZSc7Cn0KZnVuY3Rpb24gc2hvd1BhbmVsVGFiKHRhYil7CiAgWydwcmVkaWN0aW9uJywnZGl2aWRlbmRzJywnYW5hbHlzdCcsJ25ld3MnXS5mb3JFYWNoKGZ1bmN0aW9uKHQpewogICAgdmFyIGVsPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdwYW5lbC0nK3QpOwogICAgdmFyIGJ0bj1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgncHRhYi0nK3QpOwogICAgaWYoZWwpIGVsLnN0eWxlLmRpc3BsYXk9dD09PXRhYj8nYmxvY2snOidub25lJzsKICAgIGlmKGJ0bil7YnRuLnN0eWxlLmJhY2tncm91bmQ9dD09PXRhYj8nIzJhMmE0YSc6JyMxYTFhMmUnO2J0bi5zdHlsZS5jb2xvcj10PT09dGFiPycjNGE5MGQ5JzonIzg4OCc7YnRuLnN0eWxlLmJvcmRlckNvbG9yPXQ9PT10YWI/JyMzYTNhNmEnOicjMmEyYTNhJzt9CiAgfSk7Cn0KZnVuY3Rpb24gY29tcHV0ZVJTSShjbG9zZXMscGVyaW9kKXsKICBwZXJpb2Q9cGVyaW9kfHwxNDsKICBpZihjbG9zZXMubGVuZ3RoPHBlcmlvZCsxKSByZXR1cm4gNTA7CiAgdmFyIGdhaW5zPVtdLGxvc3Nlcz1bXTsKICBmb3IodmFyIGk9MTtpPGNsb3Nlcy5sZW5ndGg7aSsrKXt2YXIgZD1jbG9zZXNbaV0tY2xvc2VzW2ktMV07Z2FpbnMucHVzaChkPjA/ZDowKTtsb3NzZXMucHVzaChkPDA/LWQ6MCk7fQogIHZhciBhZz1nYWlucy5zbGljZSgtcGVyaW9kKS5yZWR1Y2UoZnVuY3Rpb24oYSxiKXtyZXR1cm4gYStiO30sMCkvcGVyaW9kOwogIHZhciBhbD1sb3NzZXMuc2xpY2UoLXBlcmlvZCkucmVkdWNlKGZ1bmN0aW9uKGEsYil7cmV0dXJuIGErYjt9LDApL3BlcmlvZDsKICByZXR1cm4gYWw9PT0wPzEwMDoxMDAtMTAwLygxK2FnL2FsKTsKfQpmdW5jdGlvbiBjb21wdXRlRU1BKGFycixwKXsKICBpZihhcnIubGVuZ3RoPHApIHJldHVybiBhcnJbYXJyLmxlbmd0aC0xXTsKICB2YXIgaz0yLyhwKzEpLGVtPWFyci5zbGljZSgwLHApLnJlZHVjZShmdW5jdGlvbihhLGIpe3JldHVybiBhK2I7fSwwKS9wOwogIGZvcih2YXIgaT1wO2k8YXJyLmxlbmd0aDtpKyspIGVtPWFycltpXSprK2VtKigxLWspOwogIHJldHVybiBlbTsKfQpmdW5jdGlvbiBjb21wdXRlTUFDRChjbG9zZXMpewogIGlmKGNsb3Nlcy5sZW5ndGg8MjYpIHJldHVybntidWxsaXNoOm51bGx9OwogIHJldHVybntidWxsaXNoOmNvbXB1dGVFTUEoY2xvc2VzLDEyKT5jb21wdXRlRU1BKGNsb3NlcywyNil9Owp9CmFzeW5jIGZ1bmN0aW9uIGxvYWRQYW5lbERhdGEodGlja2VyKXsKICB0cnl7CiAgICB2YXIgcXI9YXdhaXQgZmV0Y2goJ2h0dHBzOi8vY29yc3Byb3h5LmlvLz91cmw9JytlbmNvZGVVUklDb21wb25lbnQoJ2h0dHBzOi8vcXVlcnkxLmZpbmFuY2UueWFob28uY29tL3YxMC9maW5hbmNlL3F1b3RlU3VtbWFyeS8nK3RpY2tlcisnP21vZHVsZXM9Y2FsZW5kYXJFdmVudHMsZmluYW5jaWFsRGF0YSxyZWNvbW1lbmRhdGlvblRyZW5kLGRlZmF1bHRLZXlTdGF0aXN0aWNzLHByaWNlJykpOwogICAgdmFyIGhyPWF3YWl0IGZldGNoKCdodHRwczovL2NvcnNwcm94eS5pby8/dXJsPScrZW5jb2RlVVJJQ29tcG9uZW50KCdodHRwczovL3F1ZXJ5MS5maW5hbmNlLnlhaG9vLmNvbS92OC9maW5hbmNlL2NoYXJ0LycrdGlja2VyKyc/aW50ZXJ2YWw9MWQmcmFuZ2U9OTBkJykpOwogICAgdmFyIHFqPWF3YWl0IHFyLmpzb24oKSxoaj1hd2FpdCBoci5qc29uKCk7CiAgICB2YXIgcXM9cWoucXVvdGVTdW1tYXJ5fHx7fTsKICAgIHZhciByZXM9KChxcy5yZXN1bHQmJnFzLnJlc3VsdC5sZW5ndGgpP3FzLnJlc3VsdFswXTpudWxsKXx8e307CiAgICB2YXIgY2hhcnRSZXM9aGouY2hhcnQmJmhqLmNoYXJ0LnJlc3VsdCYmaGouY2hhcnQucmVzdWx0WzBdOwogICAgaWYoIWNoYXJ0UmVzKSB0aHJvdyBuZXcgRXJyb3IoJ05vIHByaWNlIGhpc3RvcnkgYXZhaWxhYmxlIGZvciAnK3RpY2tlcik7CiAgICB2YXIgY2xvc2VzPWNoYXJ0UmVzLmluZGljYXRvcnMucXVvdGVbMF0uY2xvc2UuZmlsdGVyKGZ1bmN0aW9uKGMpe3JldHVybiBjIT1udWxsO30pOwogICAgdmFyIGN1cj1jaGFydFJlcy5tZXRhLnJlZ3VsYXJNYXJrZXRQcmljZTsKICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdwYW5lbC10aWNrZXItcHJpY2UnKS50ZXh0Q29udGVudD0nJCcrY3VyLnRvRml4ZWQoMykrJyBBVUQnOwogICAgcmVuZGVyUHJlZGljdGlvblBhbmVsKGNsb3NlcyxyZXMsY3VyKTsKICAgIHJlbmRlckRpdmlkZW5kc1BhbmVsKHJlcyk7CiAgICByZW5kZXJBbmFseXN0UGFuZWwocmVzLGN1cik7CiAgfWNhdGNoKGUpewogICAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3BhbmVsLXByZWRpY3Rpb24nKS5pbm5lckhUTUw9JzxwIHN0eWxlPSJjb2xvcjojY2M0NDQ0O3BhZGRpbmc6MTJweCI+JytlLm1lc3NhZ2UrJzwvcD4nOwogICAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3BhbmVsLWRpdmlkZW5kcycpLmlubmVySFRNTD0nPHAgc3R5bGU9ImNvbG9yOiM4ODg7cGFkZGluZzoxMnB4Ij5VbmF2YWlsYWJsZTwvcD4nOwogICAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3BhbmVsLWFuYWx5c3QnKS5pbm5lckhUTUw9JzxwIHN0eWxlPSJjb2xvcjojODg4O3BhZGRpbmc6MTJweCI+VW5hdmFpbGFibGU8L3A+JzsKICB9CiAgdHJ5ewogICAgdmFyIG5yPWF3YWl0IGZldGNoKCdodHRwczovL2NvcnNwcm94eS5pby8/dXJsPScrZW5jb2RlVVJJQ29tcG9uZW50KCdodHRwczovL3F1ZXJ5Mi5maW5hbmNlLnlhaG9vLmNvbS92MS9maW5hbmNlL3NlYXJjaD9xPScrdGlja2VyKycmbmV3c0NvdW50PTgnKSk7CiAgICB2YXIgbmo9YXdhaXQgbnIuanNvbigpOwogICAgcmVuZGVyTmV3c1BhbmVsKG5qLm5ld3N8fFtdKTsKICB9Y2F0Y2goZSl7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3BhbmVsLW5ld3MnKS5pbm5lckhUTUw9JzxwIHN0eWxlPSJjb2xvcjojODg4O3BhZGRpbmc6MTJweCI+TmV3cyB1bmF2YWlsYWJsZTwvcD4nO30KfQpmdW5jdGlvbiByZW5kZXJQcmVkaWN0aW9uUGFuZWwoY2xvc2VzLHF1b3RlLGN1cil7CiAgdmFyIHJzaT1jb21wdXRlUlNJKGNsb3NlcyksbWFjZD1jb21wdXRlTUFDRChjbG9zZXMpOwogIHZhciBtYTIwPWNsb3Nlcy5zbGljZSgtMjApLnJlZHVjZShmdW5jdGlvbihhLGIpe3JldHVybiBhK2I7fSwwKS9NYXRoLm1pbigyMCxjbG9zZXMubGVuZ3RoKTsKICB2YXIgbW9tNT1jbG9zZXMubGVuZ3RoPj02PygoY3VyLWNsb3Nlc1tjbG9zZXMubGVuZ3RoLTZdKS9jbG9zZXNbY2xvc2VzLmxlbmd0aC02XSoxMDApOjA7CiAgdmFyIHA9cXVvdGUucHJpY2V8fHt9LGZkPXF1b3RlLmZpbmFuY2lhbERhdGF8fHt9OwogIHZhciB5SD0ocC5maWZ0eVR3b1dlZWtIaWdoJiZwLmZpZnR5VHdvV2Vla0hpZ2gucmF3KXx8Y3VyLHlMPShwLmZpZnR5VHdvV2Vla0xvdyYmcC5maWZ0eVR3b1dlZWtMb3cucmF3KXx8Y3VyOwogIHZhciB5UG9zPShjdXIteUwpLygoeUgteUwpfHwxKSoxMDA7CiAgdmFyIHRndD0oZmQudGFyZ2V0TWVhblByaWNlJiZmZC50YXJnZXRNZWFuUHJpY2UucmF3KXx8MDsKICB2YXIgYVVwPXRndD8oKHRndC1jdXIpL2N1cioxMDApOm51bGw7CiAgdmFyIHNpZ3M9WwogICAge246J1JTSSAoMTQpJyx2OnJzaS50b0ZpeGVkKDApLGI6cnNpPj00MCYmcnNpPD02NSxub3RlOnJzaT43MD8nT3ZlcmJvdWdodCc6cnNpPDMwPydPdmVyc29sZCc6J0hlYWx0aHkgKDQwLTY1KSd9LAogICAge246J01BQ0QnLHY6bWFjZC5idWxsaXNoPT09bnVsbD8nTi9BJzptYWNkLmJ1bGxpc2g/J0J1bGxpc2gnOidCZWFyaXNoJyxiOm1hY2QuYnVsbGlzaCxub3RlOm1hY2QuYnVsbGlzaD8nMTJFTUEgPiAyNkVNQSc6JzEyRU1BIDwgMjZFTUEnfSwKICAgIHtuOid2cyAyMC1EYXkgTUEnLHY6KChjdXItbWEyMCkvbWEyMCoxMDA+PTA/JysnOicnKSsoKGN1ci1tYTIwKS9tYTIwKjEwMCkudG9GaXhlZCgxKSsnJScsYjpjdXI+bWEyMCxub3RlOmN1cj5tYTIwPydBYm92ZSBNQSc6J0JlbG93IE1BJ30sCiAgICB7bjondnMgMjAtRGF5IE1BJyx2OigoY3VyLW1hMjApL21hMjAqMTAwPj0wPycrJzonJykrKChjdXItbWEyMCkvbWEyMCoxMDApLnRvRml4ZWQoMSkrJyUnLGI6Y3VyPm1hMjAsbm90ZTpjdXI+bWEyMD8nQWJvdmUgTUEnOidCZWxvdyBNQSd9LAogICAge246JzUtRGF5IE1vbWVudHVtJyx2Oihtb201Pj0wPycrJzonJykrbW9tNS50b0ZpeGVkKDEpKyclJyxiOm1vbTU+MCxub3RlOm1vbTU+Mz8nU3Ryb25nIHVwdHJlbmQnOm1vbTU8LTM/J0Rvd250cmVuZCc6J1NpZGV3YXlzJ30sCiAgICB7bjonNTItV2VlayBQb3NpdGlvbicsdjp5UG9zLnRvRml4ZWQoMCkrJyUnLGI6eVBvczw4MCYmeVBvcz4xNSxub3RlOnlQb3M+ODU/J05lYXIgNTJXIGhpZ2gnOnlQb3M8MTU/J05lYXIgNTJXIGxvdyc6J01pZC1yYW5nZSd9CiAgXTsKICBpZihhVXAhPT1udWxsKSBzaWdzLnB1c2goe246J0FuYWx5c3QgVGFyZ2V0Jyx2OihhVXA+PTA/JysnOicnKSthVXAudG9GaXhlZCgxKSsnJScsYjphVXA+NSxub3RlOidUYXJnZXQgJCcrdGd0LnRvRml4ZWQoMil9KTsKICB2YXIgYnVsbHM9c2lncy5maWx0ZXIoZnVuY3Rpb24ocyl7cmV0dXJuIHMuYj09PXRydWU7fSkubGVuZ3RoLHRvdD1zaWdzLmxlbmd0aCxwY3Q9TWF0aC5yb3VuZChidWxscy90b3QqMTAwKTsKICB2YXIgc2lnLGNvbDsKICBpZihwY3Q+PTcwKXtzaWc9J0JVTExJU0gnO2NvbD0nIzQ0YmI0NCc7fWVsc2UgaWYocGN0Pj01NSl7c2lnPSdNSUxETFkgQlVMTElTSCc7Y29sPScjODhjYzQ0Jzt9ZWxzZSBpZihwY3Q+PTQwKXtzaWc9J05FVVRSQUwnO2NvbD0nI2ZmOTkwMCc7fWVsc2V7c2lnPSdCRUFSSVNIJztjb2w9JyNjYzAwMDAnO30KICB2YXIgaHRtbD0nPGRpdiBzdHlsZT0idGV4dC1hbGlnbjpjZW50ZXI7cGFkZGluZzoxNnB4O2JhY2tncm91bmQ6IzBmMWYwZjtib3JkZXItcmFkaXVzOjhweDtib3JkZXI6MXB4IHNvbGlkICcrY29sKyczMzttYXJnaW4tYm90dG9tOjE2cHgiPicKICAgICsnPGRpdiBzdHlsZT0iZm9udC1zaXplOjIycHg7Zm9udC13ZWlnaHQ6Ym9sZDtjb2xvcjonK2NvbCsnIj4nK3NpZysnPC9kaXY+JwogICAgKyc8ZGl2IHN0eWxlPSJmb250LXNpemU6MTNweDtjb2xvcjojODg4O21hcmdpbi10b3A6NnB4Ij4nK3BjdCsnJSBidWxsaXNoICgnK2J1bGxzKycvJyt0b3QrJyBzaWduYWxzKTwvZGl2PicKICAgICsnPC9kaXY+PGRpdiBzdHlsZT0iZGlzcGxheTpncmlkO2dhcDo4cHgiPicKICAgICtzaWdzLm1hcChmdW5jdGlvbihzKXsKICAgICAgdmFyIGM9cy5iPT09dHJ1ZT8nIzQ0YmI0NCc6cy5iPT09ZmFsc2U/JyNjYzAwMDAnOicjZmY5OTAwJzsKICAgICAgdmFyIGFycm93PXMuYj09PXRydWU/J1VQJzpzLmI9PT1mYWxzZT8nRE4nOictLSc7CiAgICAgIHJldHVybiAnPGRpdiBzdHlsZT0iZGlzcGxheTpmbGV4O2p1c3RpZnktY29udGVudDpzcGFjZS1iZXR3ZWVuO2FsaWduLWl0ZW1zOmNlbnRlcjtwYWRkaW5nOjEwcHggMTJweDtiYWNrZ3JvdW5kOiMxNDE0Mjg7Ym9yZGVyLXJhZGl1czo2cHg7Ym9yZGVyLWxlZnQ6M3B4IHNvbGlkICcrYysnIj4nCiAgICAgICAgKyc8ZGl2PjxkaXYgc3R5bGU9ImZvbnQtc2l6ZToxMnB4O2NvbG9yOiNjY2M7Zm9udC13ZWlnaHQ6NTAwIj4nK3MubisnPC9kaXY+PGRpdiBzdHlsZT0iZm9udC1zaXplOjEwcHg7Y29sb3I6IzU1NTttYXJnaW4tdG9wOjJweCI+JytzLm5vdGUrJzwvZGl2PjwvZGl2PicKICAgICAgICArJzxzcGFuIHN0eWxlPSJjb2xvcjonK2MrJztmb250LXdlaWdodDpib2xkO2ZvbnQtc2l6ZToxMnB4O3doaXRlLXNwYWNlOm5vd3JhcDttYXJnaW4tbGVmdDo4cHgiPlsnK2Fycm93KyddICcrcy52Kyc8L3NwYW4+PC9kaXY+JzsKICAgIH0pLmpvaW4oJycpKyc8L2Rpdj4nCiAgICArJzxwIHN0eWxlPSJmb250LXNpemU6MTBweDtjb2xvcjojMzMzO21hcmdpbi10b3A6MTJweDt0ZXh0LWFsaWduOmNlbnRlciI+Tm90IGZpbmFuY2lhbCBhZHZpY2UuPC9wPic7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3BhbmVsLXByZWRpY3Rpb24nKS5pbm5lckhUTUw9aHRtbDsKfQpmdW5jdGlvbiByZW5kZXJEaXZpZGVuZHNQYW5lbChxdW90ZSl7CiAgdmFyIGNhbD1xdW90ZS5jYWxlbmRhckV2ZW50c3x8e30sZGtzPXF1b3RlLmRlZmF1bHRLZXlTdGF0aXN0aWNzfHx7fTsKICB2YXIgcm93cz1bCiAgICB7bDonRGl2aWRlbmQgWWllbGQgKFRUTSknLHY6KGRrcy50cmFpbGluZ0FubnVhbERpdmlkZW5kWWllbGQmJmRrcy50cmFpbGluZ0FubnVhbERpdmlkZW5kWWllbGQucmF3KT8oZGtzLnRyYWlsaW5nQW5udWFsRGl2aWRlbmRZaWVsZC5yYXcqMTAwKS50b0ZpeGVkKDIpKyclJzonTi9BJ30sCiAgICB7bDonQW5udWFsIERpdmlkZW5kL1NoYXJlJyx2Oihka3MudHJhaWxpbmdBbm51YWxEaXZpZGVuZFJhdGUmJmRrcy50cmFpbGluZ0FubnVhbERpdmlkZW5kUmF0ZS5yYXcpPyckJytka3MudHJhaWxpbmdBbm51YWxEaXZpZGVuZFJhdGUucmF3LnRvRml4ZWQoMyk6J04vQSd9LAogICAge2w6J0V4LURpdmlkZW5kIERhdGUnLHY6KGNhbC5leERpdmlkZW5kRGF0ZSYmY2FsLmV4RGl2aWRlbmREYXRlLmZtdCl8fCdOL0EnfSwKICAgIHtsOidQYXkgRGF0ZScsdjooY2FsLmRpdmlkZW5kRGF0ZSYmY2FsLmRpdmlkZW5kRGF0ZS5mbXQpfHwnTi9BJ30sCiAgICB7bDonUGF5b3V0IFJhdGlvJyx2Oihka3MucGF5b3V0UmF0aW8mJmRrcy5wYXlvdXRSYXRpby5yYXcpPyhka3MucGF5b3V0UmF0aW8ucmF3KjEwMCkudG9GaXhlZCgxKSsnJSc6J04vQSd9LAogICAge2w6JzUtWWVhciBBdmcgWWllbGQnLHY6KGRrcy5maXZlWWVhckF2Z0RpdmlkZW5kWWllbGQmJmRrcy5maXZlWWVhckF2Z0RpdmlkZW5kWWllbGQucmF3KT9ka3MuZml2ZVllYXJBdmdEaXZpZGVuZFlpZWxkLnJhdy50b0ZpeGVkKDIpKyclJzonTi9BJ30KICBdOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdwYW5lbC1kaXZpZGVuZHMnKS5pbm5lckhUTUw9JzxkaXYgc3R5bGU9ImRpc3BsYXk6Z3JpZDtnYXA6OHB4Ij4nK3Jvd3MubWFwKGZ1bmN0aW9uKHIpe3JldHVybic8ZGl2IHN0eWxlPSJkaXNwbGF5OmZsZXg7anVzdGlmeS1jb250ZW50OnNwYWNlLWJldHdlZW47cGFkZGluZzoxMHB4IDEycHg7YmFja2dyb3VuZDojMTQxNDI4O2JvcmRlci1yYWRpdXM6NnB4Ij48c3BhbiBzdHlsZT0iY29sb3I6Izg4ODtmb250LXNpemU6MTNweCI+JytyLmwrJzwvc3Bhbj48c3BhbiBzdHlsZT0iY29sb3I6I2NjYztmb250LXdlaWdodDpib2xkO2ZvbnQtc2l6ZToxM3B4Ij4nK3IudisnPC9zcGFuPjwvZGl2Pic7fSkuam9pbignJykrJzwvZGl2Pic7Cn0KZnVuY3Rpb24gcmVuZGVyQW5hbHlzdFBhbmVsKHF1b3RlLGN1cil7CiAgdmFyIGZkPXF1b3RlLmZpbmFuY2lhbERhdGF8fHt9OwogIHZhciByZWM9KChxdW90ZS5yZWNvbW1lbmRhdGlvblRyZW5kJiZxdW90ZS5yZWNvbW1lbmRhdGlvblRyZW5kLnRyZW5kKXx8W10pWzBdfHx7fTsKICB2YXIgc2I9cmVjLnN0cm9uZ0J1eXx8MCxiPXJlYy5idXl8fDAsaD1yZWMuaG9sZHx8MCxzPXJlYy5zZWxsfHwwLHNzPXJlYy5zdHJvbmdTZWxsfHwwLHRvdD1zYitiK2grcytzc3x8MTsKICB2YXIgYmFycz1be246J1N0ciBCdXknLHY6c2IsYzonIzAwYWEwMCd9LHtuOidCdXknLHY6YixjOicjNDRiYjQ0J30se246J0hvbGQnLHY6aCxjOicjZmY5OTAwJ30se246J1NlbGwnLHY6cyxjOicjY2M0NDQ0J30se246J1N0ciBTZWxsJyx2OnNzLGM6JyNjYzAwMDAnfV07CiAgdmFyIGh0bWw9JzxkaXYgc3R5bGU9InBhZGRpbmc6MTJweDtiYWNrZ3JvdW5kOiMxNDE0Mjg7Ym9yZGVyLXJhZGl1czo2cHg7bWFyZ2luLWJvdHRvbTo4cHgiPicKICAgICsnPGRpdiBzdHlsZT0iZm9udC1zaXplOjExcHg7Y29sb3I6IzY2NjttYXJnaW4tYm90dG9tOjhweCI+QU5BTFlTVCBSQVRJTkdTICgnK3RvdCsnIGFuYWx5c3RzKTwvZGl2PicKICAgICsnPGRpdiBzdHlsZT0iZGlzcGxheTpmbGV4O2dhcDo0cHg7YWxpZ24taXRlbXM6ZmxleC1lbmQ7aGVpZ2h0OjQ4cHgiPicKICAgICtiYXJzLm1hcChmdW5jdGlvbihyKXtyZXR1cm4nPGRpdiBzdHlsZT0iZmxleDoxO2Rpc3BsYXk6ZmxleDtmbGV4LWRpcmVjdGlvbjpjb2x1bW47YWxpZ24taXRlbXM6Y2VudGVyO2dhcDoycHgiPjxzcGFuIHN0eWxlPSJmb250LXNpemU6OXB4O2NvbG9yOiM2NjYiPicrci52Kyc8L3NwYW4+PGRpdiBzdHlsZT0id2lkdGg6MTAwJTtiYWNrZ3JvdW5kOicrci5jKyc7aGVpZ2h0OicrTWF0aC5tYXgoNCxNYXRoLnJvdW5kKHIudi90b3QqNDApKSsncHg7Ym9yZGVyLXJhZGl1czoycHggMnB4IDAgMCI+PC9kaXY+PC9kaXY+Jzt9KS5qb2luKCcnKQogICAgKyc8L2Rpdj48ZGl2IHN0eWxlPSJkaXNwbGF5OmZsZXg7bWFyZ2luLXRvcDo0cHgiPicrYmFycy5tYXAoZnVuY3Rpb24ocil7cmV0dXJuJzxzcGFuIHN0eWxlPSJmb250LXNpemU6OHB4O2NvbG9yOiM1NTU7ZmxleDoxO3RleHQtYWxpZ246Y2VudGVyIj4nK3IubisnPC9zcGFuPic7fSkuam9pbignJykrJzwvZGl2PjwvZGl2Pic7CiAgdmFyIHRndHM9WwogICAge2w6J1RhcmdldCBMb3cnLHY6KGZkLnRhcmdldExvd1ByaWNlJiZmZC50YXJnZXRMb3dQcmljZS5yYXcpPyckJytmZC50YXJnZXRMb3dQcmljZS5yYXcudG9GaXhlZCgyKTpudWxsfSwKICAgIHtsOidUYXJnZXQgTWVhbicsdjooZmQudGFyZ2V0TWVhblByaWNlJiZmZC50YXJnZXRNZWFuUHJpY2UucmF3KT8nJCcrZmQudGFyZ2V0TWVhblByaWNlLnJhdy50b0ZpeGVkKDIpOm51bGx9LAogICAge2w6J1RhcmdldCBIaWdoJyx2OihmZC50YXJnZXRIaWdoUHJpY2UmJmZkLnRhcmdldEhpZ2hQcmljZS5yYXcpPyckJytmZC50YXJnZXRIaWdoUHJpY2UucmF3LnRvRml4ZWQoMik6bnVsbH0sCiAgICB7bDonVXBzaWRlIChNZWFuKScsdjooZmQudGFyZ2V0TWVhblByaWNlJiZmZC50YXJnZXRNZWFuUHJpY2UucmF3KT8oKGZkLnRhcmdldE1lYW5QcmljZS5yYXctY3VyKS9jdXIqMTAwPj0wPycrJzonJykrKChmZC50YXJnZXRNZWFuUHJpY2UucmF3LWN1cikvY3VyKjEwMCkudG9GaXhlZCgxKSsnJSc6bnVsbH0sCiAgICB7bDonUmVjb21tZW5kYXRpb24nLHY6ZmQucmVjb21tZW5kYXRpb25LZXk/ZmQucmVjb21tZW5kYXRpb25LZXkudG9VcHBlckNhc2UoKS5yZXBsYWNlKC9fL2csJyAnKTpudWxsfQogIF07CiAgaHRtbCs9dGd0cy5maWx0ZXIoZnVuY3Rpb24odCl7cmV0dXJuIHQudjt9KS5tYXAoZnVuY3Rpb24odCl7cmV0dXJuJzxkaXYgc3R5bGU9ImRpc3BsYXk6ZmxleDtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2VlbjtwYWRkaW5nOjEwcHggMTJweDtiYWNrZ3JvdW5kOiMxNDE0Mjg7Ym9yZGVyLXJhZGl1czo2cHg7bWFyZ2luLWJvdHRvbTo2cHgiPjxzcGFuIHN0eWxlPSJjb2xvcjojODg4O2ZvbnQtc2l6ZToxM3B4Ij4nK3QubCsnPC9zcGFuPjxzcGFuIHN0eWxlPSJjb2xvcjojY2NjO2ZvbnQtd2VpZ2h0OmJvbGQ7Zm9udC1zaXplOjEzcHgiPicrdC52Kyc8L3NwYW4+PC9kaXY+Jzt9KS5qb2luKCcnKTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgncGFuZWwtYW5hbHlzdCcpLmlubmVySFRNTD1odG1sOwp9CmZ1bmN0aW9uIHJlbmRlck5ld3NQYW5lbChuZXdzKXsKICBpZighbmV3cy5sZW5ndGgpe2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdwYW5lbC1uZXdzJykuaW5uZXJIVE1MPSc8cCBzdHlsZT0iY29sb3I6Izg4ODtwYWRkaW5nOjEycHgiPk5vIHJlY2VudCBuZXdzLjwvcD4nO3JldHVybjt9CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3BhbmVsLW5ld3MnKS5pbm5lckhUTUw9JzxkaXYgc3R5bGU9ImRpc3BsYXk6Z3JpZDtnYXA6OHB4Ij4nK25ld3Muc2xpY2UoMCw4KS5tYXAoZnVuY3Rpb24oaXRlbSl7CiAgICB2YXIgZD1pdGVtLnByb3ZpZGVyUHVibGlzaFRpbWU/bmV3IERhdGUoaXRlbS5wcm92aWRlclB1Ymxpc2hUaW1lKjEwMDApLnRvTG9jYWxlRGF0ZVN0cmluZygnZW4tQVUnLHtkYXk6J251bWVyaWMnLG1vbnRoOidzaG9ydCd9KTonJzsKICAgIHZhciBocmVmPWl0ZW0ubGlua3x8JyMnOwogICAgcmV0dXJuJzxkaXYgc3R5bGU9InBhZGRpbmc6MTBweCAxMnB4O2JhY2tncm91bmQ6IzE0MTQyODtib3JkZXItcmFkaXVzOjZweCI+JwogICAgICArJzxhIGhyZWY9IicraHJlZisnIiB0YXJnZXQ9Il9ibGFuayIgcmVsPSJub29wZW5lciBub3JlZmVycmVyIiBzdHlsZT0iY29sb3I6I2M4ZDhmMDtmb250LXNpemU6MTJweDtsaW5lLWhlaWdodDoxLjQ7ZGlzcGxheTpibG9jazttYXJnaW4tYm90dG9tOjZweDt0ZXh0LWRlY29yYXRpb246bm9uZSI+JytpdGVtLnRpdGxlKyc8L2E+JwogICAgICArJzxkaXYgc3R5bGU9ImRpc3BsYXk6ZmxleDtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2Vlbjtmb250LXNpemU6MTBweDtjb2xvcjojNTU1Ij48c3Bhbj4nKyhpdGVtLnB1Ymxpc2hlcnx8JycpKyc8L3NwYW4+PHNwYW4+JytkKyc8L3NwYW4+PC9kaXY+PC9kaXY+JzsKICB9KS5qb2luKCcnKSsnPC9kaXY+JzsKfQo8L3NjcmlwdD4='
    ).decode('utf-8')

    # _INTRADAY_LIVE_APPENDED — do not remove
    JS += _b64_sp.b64decode(
        b'CjxzY3JpcHQ+Ci8qIExpdmUgaW50cmFkYXkgcGF0Y2hfZml4NzogYnV5L3NlbGwgem9uZXMgKyBBVFIgKi8KKGZ1bmN0aW9uKCl7Cid1c2Ugc3RyaWN0JzsKdmFyIFBST1hZPSdodHRwczovL2NvcnNwcm94eS5pby8/dXJsPSc7CmZ1bmN0aW9uIGNhbGNWV0FQKGJhcnMpe3ZhciB0cHY9MCx2b2w9MDtiYXJzLmZvckVhY2goZnVuY3Rpb24oYil7dmFyIHRwPShiWzJdK2JbM10rYls0XSkvMzt0cHYrPXRwKmJbNV07dm9sKz1iWzVdO30pO3JldHVybiB2b2w+MD90cHYvdm9sOjA7fQpmdW5jdGlvbiBjYWxjUlNJKGFycixwKXtwPXB8fDE0O2lmKGFyci5sZW5ndGg8cCsxKXJldHVybiA1MDt2YXIgZz0wLGw9MDtmb3IodmFyIGk9YXJyLmxlbmd0aC1wO2k8YXJyLmxlbmd0aDtpKyspe3ZhciBkPWFycltpXS1hcnJbaS0xXTtkPjA/Zys9ZDpsLT1kO312YXIgYWc9Zy9wLGFsPWwvcDtyZXR1cm4gYWw9PT0wPzEwMDoxMDAtMTAwLygxK2FnL2FsKTt9CmZ1bmN0aW9uIGNhbGNBVFIoYmFycyxwKXtwPXB8fDE0O2lmKGJhcnMubGVuZ3RoPDIpcmV0dXJuIDA7dmFyIHRyPVtdO2Zvcih2YXIgaT0xO2k8YmFycy5sZW5ndGg7aSsrKXt0ci5wdXNoKE1hdGgubWF4KGJhcnNbaV1bMl0tYmFyc1tpXVszXSxNYXRoLmFicyhiYXJzW2ldWzJdLWJhcnNbaS0xXVs0XSksTWF0aC5hYnMoYmFyc1tpXVszXS1iYXJzW2ktMV1bNF0pKSk7fXZhciBzbD10ci5zbGljZSgtcCk7cmV0dXJuIHNsLnJlZHVjZShmdW5jdGlvbihhLGIpe3JldHVybiBhK2I7fSwwKS9zbC5sZW5ndGg7fQpmdW5jdGlvbiBnZXRTaWduYWwodnMscnNpLG1vKXsKICBpZih2cz4wJiZyc2k+PTQ1JiZyc2k8PTc1JiZtbz4wKXJldHVybntzOidkYicsbGFiZWw6J0RheSBCdXknLGNvbG9yOicjMDBhYTAwJ307CiAgaWYodnM8LTEuNSYmcnNpPDM1KXJldHVybntzOidzcycsbGFiZWw6J1N0ciBTZWxsJyxjb2xvcjonI2NjMDAwMCd9OwogIGlmKHZzPi0wLjUmJnJzaT49MzgmJnJzaTw9ODIpcmV0dXJue3M6J3cnLGxhYmVsOidXYXRjaCcsY29sb3I6JyNmZmFhMDAnfTsKICBpZih2czwtMXx8cnNpPDMwKXJldHVybntzOidhdicsbGFiZWw6J0F2b2lkJyxjb2xvcjonI2NjNDQ0NCd9OwogIHJldHVybntzOiduJyxsYWJlbDonTmV1dHJhbCcsY29sb3I6JyM4ODg4ODgnfTsKfQphc3luYyBmdW5jdGlvbiBmZXRjaFRpY2tlcih0aWNrZXIpewogIHZhciBpc0FYPXRpY2tlci5lbmRzV2l0aCgnLkFYJyksZHA9aXNBWD8zOjI7CiAgdmFyIHVybD0naHR0cHM6Ly9xdWVyeTEuZmluYW5jZS55YWhvby5jb20vdjgvZmluYW5jZS9jaGFydC8nK2VuY29kZVVSSUNvbXBvbmVudCh0aWNrZXIpKyc/aW50ZXJ2YWw9MTVtJnJhbmdlPTFkJmluY2x1ZGVQcmVQb3N0PWZhbHNlJzsKICB2YXIgaj1hd2FpdChhd2FpdCBmZXRjaChQUk9YWStlbmNvZGVVUklDb21wb25lbnQodXJsKSkpLmpzb24oKTsKICB2YXIgcmVzPWouY2hhcnQmJmouY2hhcnQucmVzdWx0JiZqLmNoYXJ0LnJlc3VsdFswXTtpZighcmVzKXRocm93IG5ldyBFcnJvcignbm8gZGF0YScpOwogIHZhciBxPXJlcy5pbmRpY2F0b3JzLnF1b3RlWzBdLG1ldGE9cmVzLm1ldGF8fHt9LHRzPXJlcy50aW1lc3RhbXB8fFtdOwogIHZhciBwcmV2PW1ldGEuY2hhcnRQcmV2aW91c0Nsb3NlfHxtZXRhLnByZXZpb3VzQ2xvc2V8fHEuY2xvc2VbMF07CiAgdmFyIGJhcnM9W107CiAgZm9yKHZhciBpPTA7aTx0cy5sZW5ndGg7aSsrKXtpZihxLmNsb3NlW2ldPT1udWxsKWNvbnRpbnVlO2JhcnMucHVzaChbdHNbaV0scS5vcGVuW2ldfHxxLmNsb3NlW2ldLHEuaGlnaFtpXXx8cS5jbG9zZVtpXSxxLmxvd1tpXXx8cS5jbG9zZVtpXSxxLmNsb3NlW2ldLHEudm9sdW1lW2ldfHwwXSk7fQogIGlmKCFiYXJzLmxlbmd0aCl0aHJvdyBuZXcgRXJyb3IoJ25vIGJhcnMnKTsKICB2YXIgcHJpY2U9YmFyc1tiYXJzLmxlbmd0aC0xXVs0XTsKICB2YXIgZ3A9cHJldj8oKGJhcnNbMF1bMV0tcHJldikvcHJldioxMDApOjA7CiAgdmFyIGd0PWdwPjAuMz8nR2FwIFVwJzpncDwtMC4zPydHYXAgRG93bic6J0ZsYXQnOwogIHZhciB2dz1jYWxjVldBUChiYXJzKSx2cz12dz4wPyhwcmljZS12dykvdncqMTAwOjA7CiAgdmFyIHJzaT1jYWxjUlNJKGJhcnMubWFwKGZ1bmN0aW9uKGIpe3JldHVybiBiWzRdO30pLDE0KTsKICB2YXIgbW89YmFycy5sZW5ndGg+PTY/cHJpY2UtYmFyc1tiYXJzLmxlbmd0aC02XVs0XTowOwogIHZhciBhdHI9Y2FsY0FUUihiYXJzLDE0KTsKICB2YXIgc2lnPWdldFNpZ25hbCh2cyxyc2ksbW8pOwogIHZhciBiej0nLS0nLHN6PSctLSc7CiAgaWYoc2lnLnM9PT0nZGInKXtiej0nJCcrKHZ3PjAmJnZ3PHByaWNlP3Z3OnByaWNlKjAuOTkpLnRvRml4ZWQoZHApO3N6PSckJysoYXRyPjA/cHJpY2UrYXRyKjI6cHJpY2UqMS4wNCkudG9GaXhlZChkcCk7fQogIGVsc2UgaWYoc2lnLnM9PT0ndycpe2J6PSckJysodnc+MD92dzpwcmljZSkudG9GaXhlZChkcCk7fQogIHJldHVybnt0azp0aWNrZXIscHI6cHJpY2UsZ3A6Z3AsZ3Q6Z3Qsdnc6dncsdnM6dnMscnM6cnNpLG1vOm1vLHNpZzpzaWcsYno6Ynosc3o6c3p9Owp9CmZ1bmN0aW9uIG1ha2VSb3cocil7CiAgdmFyIGRwPXIudGsuZW5kc1dpdGgoJy5BWCcpPzM6MixnYz1yLmdwPj0wPycjNDRiYjQ0JzonI2NjNDQ0NCcsdmM9ci52cz49MD8nIzQ0YmI0NCc6JyNjYzQ0NDQnOwogIHJldHVybiAnPHRyIGRhdGEtc2lnbmFsPSInK3Iuc2lnLnMrJyIgZGF0YS10az0iJytyLnRrKyciPicKICAgICsnPHRkPicrci50aysnPC90ZD48dGQ+JCcrci5wci50b0ZpeGVkKGRwKSsnPC90ZD4nCiAgICArJzx0ZCBzdHlsZT0iY29sb3I6JytnYysnIj4nKyhyLmdwPj0wPycrJzonJykrci5ncC50b0ZpeGVkKDIpKyclPC90ZD4nCiAgICArJzx0ZD4nK3IuZ3QrJzwvdGQ+PHRkPiQnK3IudncudG9GaXhlZChkcCkrJzwvdGQ+JwogICAgKyc8dGQgc3R5bGU9ImNvbG9yOicrdmMrJyI+Jysoci52cz49MD8nKyc6JycpK3IudnMudG9GaXhlZCgyKSsnJTwvdGQ+JwogICAgKyc8dGQ+JytyLnJzLnRvRml4ZWQoMSkrJzwvdGQ+PHRkPicrKHIubW8+PTA/J1VwJzonRG93bicpKyc8L3RkPicKICAgICsnPHRkIHN0eWxlPSJjb2xvcjonK3Iuc2lnLmNvbG9yKyc7Zm9udC13ZWlnaHQ6Ym9sZCI+JytyLnNpZy5sYWJlbCsnPC90ZD4nCiAgICArJzx0ZD4nK3IuYnorJzwvdGQ+PHRkPicrci5zeisnPC90ZD4nCiAgICArJzx0ZD48YnV0dG9uIGNsYXNzPSJfY2J0biIgZGF0YS10PSInK3IudGsrJyIgc3R5bGU9ImJhY2tncm91bmQ6IzFhM2E2YTtjb2xvcjojYzhkOGYwO2JvcmRlcjoxcHggc29saWQgIzJhNGE4YTtwYWRkaW5nOjNweCA4cHg7Ym9yZGVyLXJhZGl1czozcHg7Y3Vyc29yOnBvaW50ZXI7Zm9udC1zaXplOjExcHgiPkNoYXJ0PC9idXR0b24+PC90ZD4nCiAgICArJzwvdHI+JzsKfQp2YXIgX2J1c3k9ZmFsc2UsX3Jlc3VsdHM9W107CndpbmRvdy5yZW5kZXJJbnRyYWRheVRhYmxlPWFzeW5jIGZ1bmN0aW9uKCl7CiAgaWYoX2J1c3kpcmV0dXJuO19idXN5PXRydWU7CiAgdmFyIHRib2R5PWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdpbnRyYWRheUJvZHknKSxjbnQ9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2ludHJhZGF5Q291bnQnKTsKICBpZih0Ym9keSl0Ym9keS5pbm5lckhUTUw9Jzx0cj48dGQgY29sc3Bhbj0iMTIiIHN0eWxlPSJ0ZXh0LWFsaWduOmNlbnRlcjtwYWRkaW5nOjIwcHg7Y29sb3I6Izg4OCI+TG9hZGluZyBsaXZlIGRhdGEuLi48L3RkPjwvdHI+JzsKICB2YXIgdGtzPUFycmF5LmZyb20oZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnI2NhcmRzR3JpZCAuc3RvY2stY2FyZFtkYXRhLXRpY2tlcl0nKSkubWFwKGZ1bmN0aW9uKGMpe3JldHVybiBjLmdldEF0dHJpYnV0ZSgnZGF0YS10aWNrZXInKTt9KS5maWx0ZXIoQm9vbGVhbik7CiAgaWYoIXRrcy5sZW5ndGgpe2lmKHRib2R5KXRib2R5LmlubmVySFRNTD0nPHRyPjx0ZCBjb2xzcGFuPSIxMiIgc3R5bGU9ImNvbG9yOiM4ODg7cGFkZGluZzoxMnB4Ij5ObyB0aWNrZXJzIGZvdW5kLjwvdGQ+PC90cj4nO19idXN5PWZhbHNlO3JldHVybjt9CiAgX3Jlc3VsdHM9W107CiAgZm9yKHZhciBpPTA7aTx0a3MubGVuZ3RoO2krKyl7CiAgICB0cnl7X3Jlc3VsdHMucHVzaChhd2FpdCBmZXRjaFRpY2tlcih0a3NbaV0pKTt9Y2F0Y2goZSl7Y29uc29sZS53YXJuKCdza2lwJyx0a3NbaV0sZS5tZXNzYWdlKTt9CiAgICBpZihjbnQpY250LnRleHRDb250ZW50PShpKzEpKycgb2YgJyt0a3MubGVuZ3RoKycgdGlja2Vycyc7CiAgICBhd2FpdCBuZXcgUHJvbWlzZShmdW5jdGlvbihyKXtzZXRUaW1lb3V0KHIsMjAwKTt9KTsKICB9CiAgYXBwbHlGaWx0ZXJzKCk7X2J1c3k9ZmFsc2U7CiAgZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgnLl9jYnRuJykuZm9yRWFjaChmdW5jdGlvbihiKXtiLmFkZEV2ZW50TGlzdGVuZXIoJ2NsaWNrJyxmdW5jdGlvbigpe2lmKHR5cGVvZiBzaG93Q2hhcnQ9PT0nZnVuY3Rpb24nKXNob3dDaGFydCh0aGlzLmdldEF0dHJpYnV0ZSgnZGF0YS10JykpO30pO30pOwp9OwpmdW5jdGlvbiBhcHBseUZpbHRlcnMoKXsKICB2YXIgc3Y9KChkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnaW50cmFkYXlTaWdGaWx0ZXInKXx8e30pLnZhbHVlfHwnJyksc2g9KChkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnaW50cmFkYXlTZWFyY2gnKXx8e30pLnZhbHVlfHwnJykudG9Mb3dlckNhc2UoKTsKICB2YXIgZj1fcmVzdWx0cy5maWx0ZXIoZnVuY3Rpb24ocil7cmV0dXJuKCFzdnx8c3YudG9VcHBlckNhc2UoKT09PSdBTEwnfHxyLnNpZy5zPT09c3YpJiYoIXNofHxyLnRrLnRvTG93ZXJDYXNlKCkuaW5kZXhPZihzaCkhPT0tMSk7fSk7CiAgdmFyIHRib2R5PWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdpbnRyYWRheUJvZHknKSxjbnQ9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2ludHJhZGF5Q291bnQnKTsKICBpZighZi5sZW5ndGgpe2lmKHRib2R5KXRib2R5LmlubmVySFRNTD0nPHRyPjx0ZCBjb2xzcGFuPSIxMiIgc3R5bGU9ImNvbG9yOiM4ODg7cGFkZGluZzoxMnB4Ij5ObyBtYXRjaGVzPC90ZD48L3RyPic7aWYoY250KWNudC50ZXh0Q29udGVudD0nMCBvZiAnK19yZXN1bHRzLmxlbmd0aCsnIHRpY2tlcnMnO3JldHVybjt9CiAgaWYodGJvZHkpdGJvZHkuaW5uZXJIVE1MPWYubWFwKG1ha2VSb3cpLmpvaW4oJycpOwogIGlmKGNudCljbnQudGV4dENvbnRlbnQ9Zi5sZW5ndGgrJyBvZiAnK19yZXN1bHRzLmxlbmd0aCsnIHRpY2tlcnMnOwp9CnNldFRpbWVvdXQoZnVuY3Rpb24oKXsKICB2YXIgc2Y9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2ludHJhZGF5U2lnRmlsdGVyJyksc3Q9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2ludHJhZGF5U2VhcmNoJyk7CiAgaWYoc2Ypc2YuYWRkRXZlbnRMaXN0ZW5lcignY2hhbmdlJyxhcHBseUZpbHRlcnMpO2lmKHN0KXN0LmFkZEV2ZW50TGlzdGVuZXIoJ2lucHV0JyxhcHBseUZpbHRlcnMpOwp9LDEwMDApOwp9KSgpOwo8L3NjcmlwdD4K'
    ).decode('utf-8')

    # _COUNTDOWN_APPENDED — do not remove
    JS += _b64_sp.b64decode(
        b'CjxzY3JpcHQ+Ci8qIEFnZW50IFRyYWRlciBjb3VudGRvd24g4oCUIHBhdGNoX2ZpeDQgKi8KKGZ1bmN0aW9uKCl7CmZ1bmN0aW9uIGdldFN5ZCgpe3JldHVybiBuZXcgRGF0ZShuZXcgRGF0ZSgpLnRvTG9jYWxlU3RyaW5nKCdlbi1VUycse3RpbWVab25lOidBdXN0cmFsaWEvU3lkbmV5J30pKTt9CmZ1bmN0aW9uIGlzT3Blbih0KXt2YXIgZD10LmdldERheSgpLGg9dC5nZXRIb3VycygpLG09dC5nZXRNaW51dGVzKCksdG90PWgqNjArbTtyZXR1cm4gZD49MSYmZDw9NSYmdG90Pj02MDAmJnRvdDw5NjA7fQpmdW5jdGlvbiBzZWNzVG9OZXh0KHQpe3ZhciBzPXQuZ2V0U2Vjb25kcygpLG09dC5nZXRNaW51dGVzKCklNTtyZXR1cm4oNC1tKSo2MCsoNjAtcyk7fQpmdW5jdGlvbiBmbXQocyl7dmFyIG09TWF0aC5mbG9vcihzLzYwKTtyZXR1cm4gbSsnOicrKHMlNjA8MTA/JzAnOicnKStzJTYwO30KZnVuY3Rpb24gZ2V0RWwoKXsKICB2YXIgZWw9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ19hZ2VudENkJyk7aWYoZWwpcmV0dXJuIGVsOwogIHZhciB0YWI9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ3RhYi1hZ2VudCcpO2lmKCF0YWIpcmV0dXJuIG51bGw7CiAgdmFyIGJ0bj10YWIucXVlcnlTZWxlY3RvcignYnV0dG9uJyk7aWYoIWJ0bnx8IWJ0bi5wYXJlbnROb2RlKXJldHVybiBudWxsOwogIGVsPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoJ3NwYW4nKTsKICBlbC5pZD0nX2FnZW50Q2QnOwogIGVsLnN0eWxlLmNzc1RleHQ9J2ZvbnQtc2l6ZToxM3B4O21hcmdpbi1sZWZ0OjE2cHg7Zm9udC13ZWlnaHQ6NjAwO2ZvbnQtZmFtaWx5Om1vbm9zcGFjZSc7CiAgYnRuLnBhcmVudE5vZGUuaW5zZXJ0QmVmb3JlKGVsLGJ0bi5uZXh0U2libGluZyk7CiAgcmV0dXJuIGVsOwp9CmZ1bmN0aW9uIHRpY2soKXsKICB2YXIgZWw9Z2V0RWwoKTtpZighZWwpcmV0dXJuOwogIHZhciB0PWdldFN5ZCgpOwogIGlmKGlzT3Blbih0KSl7CiAgICB2YXIgcz1zZWNzVG9OZXh0KHQpOwogICAgZWwuc3R5bGUuY29sb3I9czwzMD8nI2ZmOTkwMCc6JyM0YTkwZDknOwogICAgZWwudGV4dENvbnRlbnQ9J05leHQgc2NhbjogJytmbXQocyk7CiAgfWVsc2V7CiAgICBlbC5zdHlsZS5jb2xvcj0nIzY2Nic7CiAgICB2YXIgZD10LmdldERheSgpOwogICAgZWwudGV4dENvbnRlbnQ9KGQ9PT01fHxkPT09Nnx8ZD09PTApPydDbG9zZWQg4oCUIG9wZW5zIE1vbiAxMGFtJzonQ2xvc2VkIOKAlCBvcGVucyAxMGFtJzsKICB9Cn0Kc2V0SW50ZXJ2YWwodGljaywxMDAwKTt0aWNrKCk7Cn0pKCk7Cjwvc2NyaXB0Pg=='
    ).decode('utf-8')

    JS=JS.replace("__ACCURACY__", accuracy_json)

    macro_js_data = json.dumps(macro) if macro else "{}"
    HTML=f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Analyser 2.0</title>
{CSS}
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
<header>
  <div><h1>Trading Analyser 2.0</h1><p>DJRTrading Hurst Cycle Method</p></div>
  <div style="display:flex;align-items:center;gap:20px">
    <div style="text-align:center">
      <button id="nightlyBtn" onclick="triggerNightlyRun()" style="background:linear-gradient(135deg,#1a6b3c,#0d4a2a);color:white;border:none;padding:9px 20px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:bold">Run Nightly Now</button>
      <div id="nightlyStatus" style="font-size:11px;color:#aaa;margin-top:4px;max-width:200px"></div>
    </div>
    <div style="text-align:right"><p style="color:#aaa;font-size:12px">Last updated: {today}</p>
  <p style="color:#aaa;font-size:12px">Signal Accuracy: <span style="color:{'#44bb44' if overall_acc>=60 else '#ff9900' if overall_acc>=50 else '#cc0000'}">{overall_acc:.1f}%</span></p></div>
</header>

<nav class="tab-nav">
  <div class="nav-group" id="navgroup-overview">
    <button class="nav-group-btn active" onclick="toggleNavGroup('overview')">Overview <span class="caret">&#9662;</span></button>
    <div class="nav-dropdown">
      <button class="tab-btn active" onclick="showTab('market')">Market Analysis</button>
      <button class="tab-btn" onclick="showTab('market_status')">Market Status</button>
    </div>
  </div>
  <div class="nav-group" id="navgroup-portfolio">
    <button class="nav-group-btn" onclick="toggleNavGroup('portfolio')">Portfolio <span class="caret">&#9662;</span></button>
    <div class="nav-dropdown">
      <button class="tab-btn" onclick="showTab('portfolio')">Portfolio</button>
      <button class="tab-btn" onclick="showTab('addholder')">Add Holding</button>
      <button class="tab-btn" onclick="showTab('paper')">Paper Trading</button>
    </div>
  </div>
  <div class="nav-group" id="navgroup-strategies">
    <button class="nav-group-btn" onclick="toggleNavGroup('strategies')">Strategies <span class="caret">&#9662;</span></button>
    <div class="nav-dropdown">
      <button class="tab-btn" onclick="showTab('agent')">Agent Trader</button>
      <button class="tab-btn" onclick="showTab('cycle')">Cycle Trading</button>
      <button class="tab-btn" onclick="showTab('suggestions')">Trade Ideas</button>
      <button class="tab-btn" onclick="showTab('intraday')">Day Trading</button>
    </div>
  </div>
  <div class="nav-group" id="navgroup-research">
    <button class="nav-group-btn" onclick="toggleNavGroup('research')">Research <span class="caret">&#9662;</span></button>
    <div class="nav-dropdown">
      <button class="tab-btn" onclick="showTab('asx')">ASX Scanner</button>
      <button class="tab-btn" onclick="showTab('watchlist')">Watchlist</button>
      <button class="tab-btn" onclick="showTab('history')">Signal History</button>
      <button class="tab-btn" onclick="showTab('backtest')">Backtest</button>
      <button class="tab-btn" onclick="showTab('quantitative')">Quantitative</button>
    </div>
  </div>
  <button class="tab-btn" onclick="showTab('token')" style="margin-left:auto">Settings</button>
</nav>

<!-- TAB 1: Market Analysis -->
<div id="tab-market" class="tab-content active">
<div class="section">
  <div class="stats-grid">
    <div class="stat-card" style="cursor:pointer" onclick="showTab('portfolio');document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));document.querySelector('[onclick=\'showTab(\'portfolio\')\'  ]')?.classList.add('active')"><div class="stat-label">Portfolio Value</div><div class="stat-value">${port_value:,.2f}<span style="font-size:13px;margin-left:6px;color:{port_pnl_color}">{port_pnl_arrow}{port_pnl_prefix}{port_pnl_pct:.1f}%</span></div></div>
    <div class="stat-card"><div class="stat-label">Stocks Scanned</div><div class="stat-value">{total}</div></div>
    <div class="stat-card"><div class="stat-label">Buy Signals</div><div class="stat-value" style="color:#44bb44">{buys}</div></div>
    <div class="stat-card"><div class="stat-label">Hold</div><div class="stat-value" style="color:#ff9900">{holds}</div></div>
    <div class="stat-card"><div class="stat-label">Avoid</div><div class="stat-value" style="color:#cc0000">{avoids}</div></div>
    <div class="stat-card"><div class="stat-label">Signal Accuracy</div><div class="stat-value" style="color:{'#44bb44' if overall_acc>=60 else '#ff9900' if overall_acc>=50 else '#cc0000'}">{overall_acc:.1f}%</div></div>
    <div class="stat-card" style="cursor:pointer" onclick="showTab('market_status');document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));document.querySelector('[onclick=\'showTab(\'market_status\')\'  ]')?.classList.add('active')"><div class="stat-label">Market Score</div><div class="stat-value" style="color:{macro_zone_color}">{macro_composite:.0f}<span style="font-size:13px;margin-left:6px">{macro_zone}</span></div></div>
  </div>
</div>
<div class="filter-bar">
  <button class="filter-btn active" onclick="filterCards('ALL')">All</button>
  <button class="filter-btn" onclick="filterCards('BUY')">Buy</button>
  <button class="filter-btn" onclick="filterCards('HOLD')">Hold</button>
  <button class="filter-btn" onclick="filterCards('AVOID')">Avoid</button>
  <input type="text" id="searchBox" placeholder="Search ticker..." oninput="searchCards()" style="margin-left:auto">
  <button class="filter-btn" onclick="sortCards('score')">Sort: Score</button>
  <button class="filter-btn" onclick="sortCards('ticker')">Sort: A-Z</button>
</div>
<div class="cards-grid" id="cardsGrid">{cards_html}</div>
</div>

<!-- TAB 2: Portfolio -->
<div id="tab-portfolio" class="tab-content">
{portfolio_html}
</div>

<!-- TAB 3: Add Holding -->
<div id="tab-addholder" class="tab-content">
<div class="section">
<h2>Add Real Holding or Paper Trade</h2>
<div class="token-section" style="margin-bottom:25px">
  <p style="color:#888;font-size:13px">A GitHub token is required to save. Enter it in the <b>Token</b> tab first.</p>
</div>
<h3 style="color:#ccc;margin-bottom:15px">Real Holding</h3>
<div class="form-grid">
  <div class="form-group"><label>Ticker (e.g. EOS.AX)</label><input id="h_ticker" type="text" placeholder="EOS.AX"></div>
  <div class="form-group"><label>Shares</label><input id="h_shares" type="number" placeholder="1000"></div>
  <div class="form-group"><label>Buy Price ($)</label><input id="h_price" type="number" step="0.001" placeholder="1.250"></div>
  <div class="form-group"><label>Buy Date</label><input id="h_date" type="date"></div>
  <div class="form-group"><label>Type</label>
    <select id="h_type"><option value="ASX">ASX Stock</option><option value="NASDAQ">NASDAQ</option><option value="ETF">ETF</option></select>
  </div>
</div>
<button class="btn-primary" onclick="addHolding()">Add Holding</button>

<h3 style="color:#ccc;margin:30px 0 15px">Paper Trade</h3>
<div class="form-grid">
  <div class="form-group"><label>Ticker</label><input id="pt_ticker" type="text" placeholder="EOS.AX"></div>
  <div class="form-group"><label>Direction</label>
    <select id="pt_direction"><option value="LONG">LONG (Buy)</option><option value="SHORT">SHORT (Sell)</option></select>
  </div>
  <div class="form-group"><label>Entry Price ($)</label><input id="pt_entry" type="number" step="0.001"></div>
  <div class="form-group"><label>Quantity</label><input id="pt_qty" type="number"></div>
  <div class="form-group"><label>Stop Loss ($)</label><input id="pt_stop" type="number" step="0.001"></div>
  <div class="form-group"><label>Take Profit ($)</label><input id="pt_target" type="number" step="0.001"></div>
</div>
<button class="btn-primary" onclick="addPaperTrade()">Add Paper Trade</button>
</div>
</div>

<!-- TAB 4: Paper Trading -->
<div id="tab-paper" class="tab-content">
<div class="section">
<h2>Paper Trading — All Sources</h2>
<p style="color:#888;font-size:13px;margin-bottom:15px">
  Every simulated trade across all strategies in one place, tagged by where it came from.
  Cycle Trading, Agent Trader and Trade Ideas each run their own $10,000 book (a $30,000
  combined total); manual entries added via Add Holding draw from the Cycle Trading cash pool.
</p>
<div class="stats-grid" id="paperOverviewGrid"></div>

<h3 style="color:#ccc;margin:25px 0 12px">By Source</h3>
<div class="stats-grid" id="paperSourceGrid"></div>

<h3 style="color:#ccc;margin:25px 0 12px">AI Assessment <span style="font-size:11px;color:#666;font-weight:normal">— advisory only, nothing here executes a trade</span></h3>
<div id="aiAssessmentPanel" style="background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid #2a2a4a;margin-bottom:25px">
  <p style="color:#888;margin:0">Loading...</p>
</div>

<h3 style="color:#ccc;margin:25px 0 12px">Open Positions</h3>
<div class="asx-table-wrap"><table class="asx-table"><thead><tr>
  <th>Source</th><th>Ticker</th><th>Bought</th><th>Current</th><th>Position ($)</th><th>Stop</th><th>Target</th><th>% at Target</th><th>Opened</th><th></th>
</tr></thead><tbody id="paperOpenBody">
<tr><td colspan="10" style="color:#888;text-align:center;padding:20px">Loading...</td></tr>
</tbody></table></div>

<h3 style="color:#ccc;margin:25px 0 12px">Closed Trades</h3>
<div class="asx-table-wrap"><table class="asx-table"><thead><tr>
  <th>Source</th><th>Ticker</th><th>Entry</th><th>Exit</th><th>Position ($)</th><th>Opened</th><th>Closed</th><th>Reason</th><th>P&amp;L $</th><th>P&amp;L %</th>
</tr></thead><tbody id="paperClosedBody">
<tr><td colspan="10" style="color:#888;text-align:center;padding:20px">Loading...</td></tr>
</tbody></table></div>
</div>
</div>

<!-- TAB 5: ASX Scanner -->
<div id="tab-asx" class="tab-content">
<div class="section">
<h2>ASX Full Scanner</h2>
<p style="color:#888;font-size:13px;margin-bottom:15px">
  Deep scan of {asx_scan.get('total_scanned', 0)} ASX stocks.
  Last run: <b>{asx_scan.get('scanned_at','Not yet run')[:19]}</b>.
  Run weekly via GitHub Actions → <b>ASX Deep Scan</b>.
</p>
<div style="display:flex;gap:20px;align-items:center;flex-wrap:wrap;margin-bottom:15px">
  <div>
    <label style="color:#aaa;font-size:12px">Min Score: <span id="asxScoreLabel">0%+</span></label><br>
    <input type="range" id="asxMinScore" min="0" max="90" step="5" value="0" oninput="updateScoreLabel()">
  </div>
  <div>
    <label style="color:#aaa;font-size:12px">Search</label><br>
    <input type="text" id="asxSearch" placeholder="Ticker or name..." oninput="renderASXTable()">
  </div>
  <div style="margin-top:16px">
    <span id="asxCount" style="color:#aaa;font-size:13px">Loading...</span>
  </div>
</div>
<div class="asx-table-wrap">
<table class="asx-table"><thead><tr>
  <th>Ticker</th><th>Name</th><th>Score</th><th>Signal</th><th>Price</th>
  <th>1D%</th><th>RSI</th><th>Entry</th><th>Stop</th><th>Target</th><th>Watch</th>
</tr></thead><tbody id="asxBody">
<tr><td colspan="11" style="color:#888;text-align:center;padding:20px">Loading scan results...</td></tr>
</tbody></table>
</div>
</div>
</div>

<!-- TAB 6: Watchlist Manager -->
<div id="tab-watchlist" class="tab-content">
<div class="section">
<h2>Watchlist Manager</h2>
<p style="color:#888;font-size:13px;margin-bottom:20px">Add or remove stocks from the nightly scan. Click Save to push changes to GitHub.</p>
<h3 style="color:#ccc;margin-bottom:10px">ASX Stocks</h3>
<div class="watchlist-chips" id="wl_asx"></div>
<h3 style="color:#ccc;margin:20px 0 10px">NASDAQ Stocks</h3>
<div class="watchlist-chips" id="wl_nasdaq"></div>
<h3 style="color:#ccc;margin:20px 0 10px">ETFs</h3>
<div class="watchlist-chips" id="wl_etf"></div>
<div style="display:flex;gap:10px;margin-top:20px;flex-wrap:wrap;align-items:flex-end">
  <div class="form-group">
    <label>Add Ticker</label>
    <input id="wl_new_ticker" type="text" placeholder="e.g. BHP.AX" style="width:160px">
  </div>
  <div class="form-group">
    <label>Category</label>
    <select id="wl_new_cat">
      <option value="asx">ASX</option><option value="nasdaq">NASDAQ</option><option value="etf">ETF</option>
    </select>
  </div>
  <button class="btn-secondary" onclick="addToWatchlistLocal()">+ Add</button>
  <button class="btn-primary" onclick="saveWatchlist()">Save to GitHub</button>
</div>
<p style="color:#666;font-size:12px;margin-top:12px">Changes take effect on the next nightly run.</p>
</div>
</div>

<!-- TAB 7: Signal History -->
<div id="tab-history" class="tab-content">
<div class="section">
<h2>Signal History — 30 Day Log</h2>
<p style="color:#888;font-size:13px;margin-bottom:15px">Each night's recommendation vs the next day's actual move. Builds accuracy over time.</p>
{signal_history_html}
</div>
</div>

<!-- TAB 8: Backtest -->
<div id="tab-backtest" class="tab-content">
<div class="section">
<h2>Signal Backtest</h2>
<p style="color:#888;font-size:13px;margin-bottom:15px">Review historical signal accuracy for any tracked stock. The system compares each night's recommendation against the following day's actual price move.</p>
<div style="display:flex;gap:15px;align-items:flex-end;margin-bottom:20px;flex-wrap:wrap">
  <div class="form-group">
    <label>Select Stock</label>
    <select id="btStockSelect" style="width:200px"><option value="">Select a stock...</option></select>
  </div>
  <button class="btn-primary" onclick="runBacktest()">Run Backtest</button>
</div>
<div id="btResults"><p style="color:#888">Select a stock and click Run Backtest.</p></div>
</div>
</div>


<!-- TAB: Market Status -->
<div id="tab-market_status" class="tab-content">
<div class="section">
<h2>Macro Deployment Gate</h2>
<p style="color:#888;font-size:13px;margin-bottom:20px">6 macro signals scored 0–100, blended into a composite deployment score. Answers: <em>"Should I be deploying capital right now?"</em></p>
<div class="macro-zone-card" id="macroZoneCard">
  <div style="font-size:12px;color:#888;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px">Composite Deployment Score</div>
  <div id="macroComposite" style="font-size:72px;font-weight:bold;color:#888">—</div>
  <div id="macroZone" style="font-size:22px;font-weight:bold;margin:8px 0">—</div>
  <div id="macroZoneDesc" style="font-size:13px;color:#888">Click Run Nightly Now to load macro data</div>
  <div style="margin-top:16px;height:12px;background:#0f0f1a;border-radius:6px;max-width:400px;margin:16px auto 0">
    <div id="macroCompositeBar" style="height:12px;border-radius:6px;width:0%;background:#888;transition:width 0.8s"></div>
  </div>
</div>
<div class="macro-grid" id="macroSignalsGrid">
  <p style="color:#888">Loading signals...</p>
</div>
</div>
</div>


<!-- TAB: Quantitative Analysis -->
<div id="tab-quantitative" class="tab-content">
<div class="section">
<h2>Quantitative Analysis</h2>
<div class="quant-subnav">
  <button id="qbtn-earnings"     class="quant-btn active"  onclick="renderQuantTab('earnings')">Earnings Reports</button>
  <button id="qbtn-momentum"     class="quant-btn"         onclick="renderQuantTab('momentum')">12-1 Momentum</button>
  <button id="qbtn-rsi"          class="quant-btn"         onclick="renderQuantTab('rsi')">RSI Strategy</button>
  <button id="qbtn-macd"         class="quant-btn"         onclick="renderQuantTab('macd')">MACD</button>
  <button id="qbtn-stochastic"   class="quant-btn"         onclick="renderQuantTab('stochastic')">Stochastic</button>
  <button id="qbtn-ema"          class="quant-btn"         onclick="renderQuantTab('ema')">EMA</button>
  <button id="qbtn-vwap"         class="quant-btn"         onclick="renderQuantTab('vwap')">VWAP</button>
  <button id="qbtn-ma"           class="quant-btn"         onclick="renderQuantTab('ma')">MA Crossover</button>
  <button id="qbtn-walkforward"  class="quant-btn"         onclick="renderQuantTab('walkforward')">Walk Forward</button>
  <button id="qbtn-montecarlo"   class="quant-btn"         onclick="renderQuantTab('montecarlo')">Monte Carlo</button>
  <button id="qbtn-sensitivity"  class="quant-btn"         onclick="renderQuantTab('sensitivity')">Sensitivity</button>
  <button id="qbtn-top5" class="quant-btn" onclick="renderQuantTab('top5')">⭐ Top 5</button>
</div>
<div id="quantContent">
  <p style="color:#888">Click Run Nightly Now to generate quantitative data, then come back to this tab.</p>
</div>
</div>
</div>


<!-- TAB: Day Trading -->
<div id="tab-intraday" class="tab-content">
<div class="section">
<h2>Intraday Day Trading Analysis</h2>
<p style="color:#888;font-size:13px;margin-bottom:15px">15-min bar analysis with VWAP, gap detection and intraday signals. Run "Run Nightly Now" during market hours for live data.</p>
<div style="display:flex;gap:15px;align-items:center;flex-wrap:wrap;margin-bottom:15px">
  <div><label style="color:#aaa;font-size:12px">Signal</label><br>
    <select id="intradaySigFilter" onchange="renderIntradayTable()" style="background:#1e1e3a;color:#ccc;border:1px solid #444;padding:6px;border-radius:6px">
      <option value="ALL">All</option>
      <option value="DAY BUY">Day Buy</option>
      <option value="WATCH">Watch</option>
      <option value="NEUTRAL">Neutral</option>
      <option value="AVOID">Avoid</option>
    </select>
  </div>
  <div><label style="color:#aaa;font-size:12px">Search</label><br>
    <input type="text" id="intradaySearch" placeholder="Ticker..." oninput="renderIntradayTable()">
  </div>
  <div style="margin-top:16px"><span id="intradayCount" style="color:#aaa;font-size:13px"></span></div>
</div>
<div style="overflow-x:auto">
<table class="asx-table"><thead><tr>
  <th>Ticker</th><th>Price</th><th>Gap %</th><th>Gap Type</th><th>VWAP</th><th>vs VWAP</th><th>RSI 15m</th><th>Momentum</th><th>Signal</th><th>Buy Zone</th><th>Sell Zone</th><th>Chart</th>
</tr></thead><tbody id="intradayBody">
<tr><td colspan="10" style="color:#888;text-align:center;padding:20px">Click Run Nightly Now during market hours to load intraday data.</td></tr>
</tbody></table>
</div>
</div>
</div>

<!-- Intraday Chart Modal -->
<div id="intradayChartModal" onclick="if(event.target===this)closeIntradayModal()" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:1001;align-items:center;justify-content:center">
  <div style="background:#0f0f1a;border:1px solid #2a2a4a;border-radius:12px;width:90%;max-width:900px;padding:20px">
    <div style="display:flex;justify-content:space-between;margin-bottom:12px">
      <h3 id="intradayChartTitle" style="color:white"></h3>
      <button class="close-modal" onclick="closeIntradayModal()">&#215;</button>
    </div>
    <div id="intradayChartBox2" style="height:350px"></div>
  </div>
</div>

<!-- TAB: Agent Trader -->
<div id="tab-agent" class="tab-content">
<div class="section">
<h2>Agent Trader — 100-Trade Strategy Test</h2>
<p style="color:#888;font-size:13px;margin-bottom:20px">
  Autonomous agent running ORB + VWAP breakout strategy. Scans every 5 min during ASX market hours (10am–4pm AEST) via GitHub Actions.
  Reviews entry/exit signals independently and records simulated trades. After 100 trades, strategy goes to paper trading.
</p>

<!-- Progress -->
<div style="background:#1a1a2e;border-radius:12px;padding:20px;margin-bottom:20px;border:1px solid #2a2a4a">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <span style="color:#ccc;font-weight:bold">Test Progress</span>
    <span id="agentProgress" style="color:#4a90d9;font-weight:bold">Loading...</span>
  </div>
  <div class="progress-bar-wrap"><div class="progress-bar" id="agentProgressBar" style="width:0%"></div></div>
  <div style="display:flex;justify-content:space-between;font-size:11px;color:#666">
    <span>0 trades</span><span id="agentStatus" style="color:#ff9900">Loading...</span><span id="agentTargetLabel">100 trades</span>
  </div>
</div>

<!-- Stats grid -->
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:20px" id="agentStatsGrid">
  <div class="agent-stat"><div class="stat-label">Win Rate</div><div class="stat-value" id="agentWinRate">—</div></div>
  <div class="agent-stat"><div class="stat-label">Avg Gain</div><div class="stat-value" id="agentAvgGain">—</div></div>
  <div class="agent-stat"><div class="stat-label">Wins / Losses</div><div class="stat-value" id="agentWL">—</div></div>
  <div class="agent-stat"><div class="stat-label">Capital</div><div class="stat-value" id="agentCapital">—</div></div>
  <div class="agent-stat"><div class="stat-label">Growth</div><div class="stat-value" id="agentGrowth">—</div></div>
  <div class="agent-stat"><div class="stat-label">Open Trades</div><div class="stat-value" id="agentOpen">—</div></div>
</div>

<div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap">
  <button class="btn-primary" onclick="loadAgentTrades()" style="padding:8px 20px;font-size:13px">↻ Refresh</button>
  <span style="color:#666;font-size:12px;align-self:center">Auto-updates every 5 min during ASX hours (10am–4pm AEST)</span>
</div>

<p style="color:#888;font-size:13px;margin-bottom:20px">
  Full trade log (with entry/exit/target/stop/conditions) now lives on the
  <a href="#" onclick="showTab('paper');return false" style="color:#4a90d9">Paper Trading</a>
  tab, merged with Cycle Trading's trades and tagged by source.
</p>

<!-- Scan log -->
<h3 style="color:#ccc;margin:25px 0 12px">Recent Scan Log <span style="font-size:12px;color:#666">(last 30 scans)</span></h3>
<div class="asx-table-wrap" style="max-height:300px">
<table class="asx-table"><thead><tr>
  <th>Time</th><th>Ticker</th><th>Decision</th><th>Price</th><th>Notes</th>
</tr></thead><tbody id="agentScanBody">
<tr><td colspan="5" style="color:#888;text-align:center;padding:20px">Loading scan log...</td></tr>
</tbody></table>
</div>
</div>
</div>


<!-- TAB: Cycle Trading -->
<div id="tab-cycle" class="tab-content">
<div class="section">
<h2>Cycle Trading — DJRTrading Daily/Intermediate Cycle Analysis</h2>
<p style="color:#888;font-size:13px;margin-bottom:20px">
  Nightly screen of the watchlist for Daily/Intermediate Cycle setups. Ranks candidates by
  cycle score and entry-zone risk, flags failed cycles and high-risk Daily-Cycle-3/4 zones,
  and manages up to 5 concurrent risk-sized paper positions (capped at $2,000 each) with
  phase-based exits plus a hard stop-loss backstop.
</p>
<div id="combinedRiskPanel" style="margin-bottom:20px"></div>

<h3 style="color:#ccc;margin:0 0 12px">Best Candidates</h3>
<div id="cycleCandidatesGrid" style="display:grid;gap:12px"></div>

<h3 style="color:#ccc;margin:25px 0 12px">Alerts</h3>
<div id="cycleFailedAlerts"></div>
<div id="cycleHighRiskAlerts"></div>

<p style="color:#888;font-size:13px;margin:25px 0">
  Open and closed Cycle Trading positions now live on the
  <a href="#" onclick="showTab('paper');return false" style="color:#4a90d9">Paper Trading</a>
  tab, merged with Agent Trader's trades and tagged by source. Charts for open positions and
  candidates are still available above.
</p>
</div>
</div>


<!-- TAB: Trade Ideas -->
<div id="tab-suggestions" class="tab-content">
<div class="section">
<h2>Trade Ideas — Suggested Entries (Manual)</h2>
<p style="color:#888;font-size:13px;margin-bottom:20px">
  BUY-rated tickers from tonight's signal engine, for you to act on or ignore — nothing here
  executes automatically. A separate $10,000 test budget, tracked independently of Cycle
  Trading and Agent Trader. Buy/Sell write directly to <code>portfolio.json</code> via your
  GitHub token (set one on the <a href="#" onclick="showTab('token');return false" style="color:#4a90d9">Token</a> tab first).
</p>
<div class="stats-grid" id="ideasOverviewGrid"></div>

<h3 style="color:#ccc;margin:25px 0 12px">Add Your Own Trade</h3>
<p style="color:#888;font-size:13px;margin-bottom:12px">
  Not from a suggestion — enter any ticker yourself with your own buy price, stop, and sale
  (target) price. Counts toward the same $10,000 Trade Ideas budget. Enter a ticker and click
  Look Up to check its current price and get suggested entry/stop/target to start from.
</p>
<div class="form-grid">
  <div class="form-group"><label>Ticker</label><input id="mt_ticker" type="text" placeholder="EOS.AX"></div>
  <div class="form-group"><label>Buy Price ($)</label><input id="mt_price" type="number" step="0.001" placeholder="8.500"></div>
  <div class="form-group"><label>Dollar Amount</label><input id="mt_amount" type="number" step="1" placeholder="1000"></div>
  <div class="form-group"><label>Stop Price ($)</label><input id="mt_stop" type="number" step="0.001" placeholder="optional"></div>
  <div class="form-group"><label>Sale / Target Price ($)</label><input id="mt_target" type="number" step="0.001" placeholder="optional"></div>
</div>
<div style="margin-top:10px">
  <button class="btn-secondary" onclick="lookUpManualTicker()">🔍 Look Up</button>
  <button class="btn-primary" style="margin-left:8px" onclick="addManualTrade()">Buy</button>
</div>
<p id="mt_lookup_result" style="color:#888;font-size:12px;margin-top:10px"></p>

<h3 style="color:#ccc;margin:25px 0 12px">Open Positions</h3>
<div class="asx-table-wrap"><table class="asx-table"><thead><tr>
  <th>Ticker</th><th>Bought</th><th>Current</th><th>Shares</th><th>Cost</th><th>Stop</th><th>Target</th><th>% at Target</th><th>Opened</th><th></th>
</tr></thead><tbody id="ideasOpenBody">
<tr><td colspan="10" style="color:#888;text-align:center;padding:20px">Set your GitHub token to view live positions.</td></tr>
</tbody></table></div>

<h3 style="color:#ccc;margin:25px 0 12px">Suggested Entries Tonight</h3>
<div id="ideasCandidatesGrid" style="display:grid;gap:12px">
  <p style="color:#888;padding:20px">No BUY-rated candidates tonight.</p>
</div>

<h3 style="color:#ccc;margin:25px 0 12px">From Cycle Trading</h3>
<p style="color:#888;font-size:13px;margin-bottom:12px">
  Tonight's Cycle Trading candidates (DJRTrading Daily/Intermediate Cycle screen), for
  reference here too. Buying one here opens a Trade Ideas position — separate from Cycle
  Trading's own automated $10,000 book.
</p>
<div id="ideasCycleGrid" style="display:grid;gap:12px">
  <p style="color:#888;padding:20px">No Cycle Trading candidates tonight.</p>
</div>

<h3 style="color:#ccc;margin:25px 0 12px">Live Intraday Scan</h3>
<p style="color:#888;font-size:13px;margin-bottom:12px">
  Covers your watchlist plus the top 40 scored names from the weekly ASX Deep Scan, using
  the same VWAP/RSI "Day Buy" definition as the Day Trading tab's live scanner. Computed
  server-side every ~30 min during ASX/NASDAQ market hours (no live browser fetch —
  Yahoo Finance blocks that for third-party sites, and the free proxy this used to
  route through is no longer usable). Click below to load the latest snapshot.
</p>
<div style="margin-bottom:15px">
  <button class="btn-primary" onclick="scanMarketForIdeas()">🔍 Load Latest Scan</button>
  <span id="ideasScanStatus" style="color:#888;font-size:12px;margin-left:10px"></span>
</div>
<div id="ideasLiveGrid" style="display:grid;gap:12px">
  <p style="color:#888;padding:20px">Click "Load Latest Scan" to see the latest Day Buy signals.</p>
</div>
</div>
</div>


<!-- TAB 9: GitHub Token -->
<div id="tab-token" class="tab-content">
<div class="section">
<h2>GitHub API Token</h2>
<div class="token-section">
  <h3>Setup (one time only)</h3>
  <p style="color:#888;font-size:13px;margin-bottom:15px">Required to save portfolio changes, watchlist updates, and paper trades back to GitHub.</p>
  <ol style="color:#aaa;font-size:13px;line-height:2;margin-left:20px">
    <li>Go to <b>github.com → Settings → Developer Settings → Personal Access Tokens → Tokens (classic)</b></li>
    <li>Click <b>Generate new token (classic)</b></li>
    <li>Tick the <b>repo</b> scope checkbox</li>
    <li>Copy the token and paste it below</li>
  </ol>
  <div style="display:flex;gap:10px;margin-top:15px">
    <input id="ghToken" type="password" placeholder="ghp_xxxxxxxxxxxx" style="flex:1" onkeydown="if(event.key==='Enter')saveToken()">
    <button class="btn-primary" onclick="saveToken()">Save Token</button>
    <button class="btn-secondary" onclick="testToken()">Test Token</button>
  </div>
  <p id="tokenStatus" style="color:#888;font-size:12px;margin-top:10px">Checking saved token...</p>
  <p style="color:#555;font-size:11px;margin-top:8px">Token is stored in your browser only (localStorage). Never shared or uploaded. Pressing Enter in the box also saves it.</p>
</div>
</div>
</div>

<!-- Chart Modal -->
<div id="chartModal" onclick="if(event.target===this)closeChartModal()">
  <div id="chartBox">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h3 id="chartTitle" style="color:white"></h3>
      <button class="close-modal" onclick="closeChartModal()">×</button>
    </div>
    <div id="chartContainer"></div>
    <div style="color:#888;font-size:11px;margin-top:4px">RSI</div>
    <div id="rsiContainer"></div>
  </div>
</div>

<!-- Buy Confirmation Modal -- one shared confirm step for every buy path (Trade Ideas,
     Cycle Trading, Live Scan, Add Your Own Trade) instead of each one committing straight
     off a chain of prompt() dialogs. Nothing executes until "Confirm Buy" is clicked. -->
<div id="buyConfirmModal" onclick="if(event.target===this)closeBuyConfirmModal()" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.85);z-index:1002;align-items:center;justify-content:center">
  <div style="background:#0f0f1a;border:1px solid #2a2a4a;border-radius:12px;width:92%;max-width:420px;padding:24px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
      <h3 style="color:white;margin:0">Confirm Buy — <span id="bc_ticker" style="color:#4a90d9"></span></h3>
      <button class="close-modal" onclick="closeBuyConfirmModal()">×</button>
    </div>
    <p style="color:#888;font-size:12px;margin-bottom:18px">Current price: <b id="bc_price" style="color:#ccc"></b></p>
    <div class="form-grid">
      <div class="form-group"><label>Dollar Amount</label><input id="bc_amount" type="number" step="1" oninput="updateBuyConfirmShares()"></div>
      <div class="form-group"><label>Stop Price ($)</label><input id="bc_stop" type="number" step="0.001" placeholder="optional"></div>
      <div class="form-group"><label>Sale / Target Price ($)</label><input id="bc_target" type="number" step="0.001" placeholder="optional"></div>
    </div>
    <p style="color:#aaa;font-size:13px;margin:14px 0 20px">This buys <b id="bc_shares" style="color:#4a90d9">—</b> of <span id="bc_ticker2"></span>.</p>
    <div style="display:flex;gap:10px;justify-content:flex-end">
      <button class="btn-secondary" onclick="closeBuyConfirmModal()">Cancel</button>
      <button class="btn-primary" onclick="confirmBuyFromModal()">Confirm Buy</button>
    </div>
  </div>
</div>

{JS}
</body>
</html>"""

    HTML = HTML.replace('__MACRO_DATA__', json.dumps(macro or {}))
    HTML = HTML.replace('__QUANT_DATA__', json.dumps(quant or {}))
    HTML = HTML.replace('__CYCLE_DATA__', json.dumps(cycle or {}))
    HTML = HTML.replace('__PAPER_DATA__', json.dumps(portfolio.get('paper', {})))
    HTML = HTML.replace('__SUGGESTIONS_DATA__', suggestions_json)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(HTML)
    print(f"Dashboard written: {output_path}")
