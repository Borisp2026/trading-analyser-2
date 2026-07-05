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
        f'<span style="color:{change_color}">{change_prefix}{change_1d:.1f}%</span>'
        f'<span class="rsi-badge">RSI {rsi:.0f}</span></div>'
        f'<div class="score-breakdown">Tech:{tech_score:.0f} | Cycle:{cycle_score:.0f} | Blended:{score:.0f}</div>'
        f'<div class="trade-grid">'
        f"<div><label>Entry</label><strong>{entry_str}</strong></div>"
        f'<div><label>Stop</label><strong style="color:red">{stop_str}</strong></div>'
        f'<div><label>Target</label><strong style="color:green">{target_str}</strong></div>'
        f"<div><label>Confidence</label><strong>{confidence}</strong></div></div>"
        f'<div class="timing">{timing}</div>'
        f"{cycle_html}{corr_html}"
        f'{chart_btn}'
        f'<details><summary>Full Analysis</summary><ul class="reasons">{reasons_html}</ul></details>'
        f"</div></div>")

def build_portfolio_html(portfolio, stock_advice=None):
    real=portfolio.get("real",{}); paper=portfolio.get("paper",{})
    holdings=real.get("holdings",[]); pnl=real.get("total_pnl",0)
    pnl_color="green" if pnl>=0 else "red"; pnl_prefix="+" if pnl>=0 else ""
    rows=""
    for h in holdings:
        hp=h.get("pnl",0); hc="green" if hp>=0 else "red"; hpfx="+" if hp>=0 else ""
        rows+=(f'<tr><td><b>{h["ticker"]}</b></td><td>{h["shares"]}</td>'
            f'<td>${h["buy_price"]:.3f}</td><td>${h["current_price"]:.3f}</td>'
            f'<td>${h["value"]:,.2f}</td><td style="color:{hc}">{hpfx}${hp:,.2f} ({h.get("pnl_pct",0):+.1f}%)</td>'
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
        f'<div class="stat-card"><div class="stat-label">P&L</div><div class="stat-value" style="color:{pnl_color}">{pnl_prefix}${pnl:,.2f} ({real.get("total_pnl_pct",0):+.1f}%)</div></div>'
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
    rows_data.sort(key=lambda x: x[0], reverse=True)
    current_date=None
    for rd in rows_data:
        if rd[0]!=current_date:
            current_date=rd[0]
            html+=f'<tr><td colspan="10" style="background:#0a0a15;color:#4a90d9;font-weight:bold;padding:6px 12px;font-size:12px;letter-spacing:1px">{current_date}</td></tr>'
        html+=f'<tr data-ticker="{rd[1]}">'+''.join(f'<td>{v}</td>' for v in rd)+'</tr>'
    html+='</tbody></table>'
    return html

def build_dashboard(results, portfolio, output_path, signal_history=None, accuracy=None, intraday=None, quant=None, macro=None):
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
    overall_acc=(accuracy or {}).get("overall_accuracy",0)

    # Chart data — per ticker JSON blob
    chart_data_map={r["ticker"]: r.get("chart_data",{}) for r in results if r.get("chart_data")}
    chart_data_json=json.dumps(chart_data_map)

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
        _m=json.loads(macro_json)
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
.tab-nav{display:flex;background:#13132a;border-bottom:2px solid #2a2a4a;padding:0 20px;flex-wrap:wrap}
.tab-btn{padding:12px 18px;cursor:pointer;font-size:13px;color:#888;border:none;background:none;border-bottom:3px solid transparent;margin-bottom:-2px;transition:all 0.2s}
.tab-btn:hover{color:#ccc}.tab-btn.active{color:#4a90d9;border-bottom-color:#4a90d9;font-weight:bold}
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
function showTab(id) {
    document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    document.getElementById('tab-'+id).classList.add('active');
    document.querySelector(`[onclick="showTab('${id}')"]`).classList.add('active');
    if(id==='agent') loadAgentTrades();
    if(id==='market_status') renderMacroGate();
    if(id==='asx') renderASXTable();
    if(id==='watchlist') renderWatchlist();
    if(id==='backtest') populateBacktestSelect();
    if(id==='history') { /* already rendered server-side */ }
    if(id==='intraday') renderIntradayTable();
    if(id==='quantitative') renderQuantTab('earnings');
    if(id==='intraday') renderIntradayTable();
    if(id==='quantitative') renderQuantTab('earnings');
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
function saveToken(){
    const t=document.getElementById('ghToken').value.trim();
    if(t){localStorage.setItem('gh_token',t);alert('Token saved.');}
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
    const resolved=entries.filter(e=>e.outcome&&e.outcome!=='PENDING');
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
function showChart(ticker){
    const data=CHART_DATA[ticker];
    if(!data||!data.candles||!data.candles.length){alert('No chart data for '+ticker);return;}
    document.getElementById('chartTitle').textContent=ticker+' — 90 Day Chart';
    document.getElementById('chartModal').classList.add('open');
    setTimeout(()=>renderChart(data),50);
}
function closeChartModal(){
    document.getElementById('chartModal').classList.remove('open');
    if(_chart){_chart.remove();_chart=null;}
    if(_rsiChart){_rsiChart.remove();_rsiChart=null;}
}
function renderChart(data){
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
}



// ── Agent Trader tab ─────────────────────────────────────────────────────────
const AGENT_RAW_URL = 'https://raw.githubusercontent.com/Borisp2026/trading-analyser-2/main/data/agent_trades.json';

async function loadAgentTrades() {
    document.getElementById('agentProgress').textContent = 'Loading...';
    try {
        const r = await fetch(AGENT_RAW_URL + '?t=' + Date.now());
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const d = await r.json();
        renderAgentDashboard(d);
    } catch(e) {
        document.getElementById('agentTradeBody').innerHTML =
            '<tr><td colspan="11" style="color:#cc0000;text-align:center;padding:20px">Error: ' + e.message + '</td></tr>';
        document.getElementById('agentProgress').textContent = 'Error loading data';
    }
}

function renderAgentDashboard(d) {
    const s = d.stats || {};
    const trades = d.trades || [];
    const closed = trades.filter(t=>t.status==='CLOSED').length;
    const pct = Math.min(100, (closed/30)*100);

    document.getElementById('agentProgress').textContent = closed + ' / 30 trades';
    document.getElementById('agentProgressBar').style.width = pct + '%';
    const statusEl = document.getElementById('agentStatus');
    statusEl.textContent = d.status==='COMPLETED' ? '✓ COMPLETE — Ready for paper trading'
                         : d.status==='RUNNING'   ? '● Running' : (d.status||'—');
    statusEl.style.color = d.status==='COMPLETED'?'#44bb44':d.status==='RUNNING'?'#ff9900':'#888';

    const wr = s.win_rate || 0;
    document.getElementById('agentWinRate').innerHTML = '<span style="color:'+(wr>=60?'#44bb44':wr>=50?'#ff9900':'#cc0000')+'">'+wr+'%</span>';
    const ag = s.avg_pnl_pct || 0;
    document.getElementById('agentAvgGain').innerHTML = '<span style="color:'+(ag>=0?'#44bb44':'#cc0000')+'">'+(ag>=0?'+':'')+ag.toFixed(1)+'%</span>';
    document.getElementById('agentWL').innerHTML = '<span class="trade-win">'+(s.wins||0)+'W</span> / <span class="trade-loss">'+(s.losses||0)+'L</span>';
    document.getElementById('agentCapital').textContent = '$'+(s.current_capital||1000).toFixed(2);
    const gr = s.capital_growth || 0;
    document.getElementById('agentGrowth').innerHTML = '<span style="color:'+(gr>=0?'#44bb44':'#cc0000')+'">'+(gr>=0?'+':'')+gr.toFixed(1)+'%</span>';
    document.getElementById('agentOpen').textContent = Object.keys(d.open_positions||{}).length;

    const tbody = document.getElementById('agentTradeBody');
    if (!trades.length) {
        tbody.innerHTML = '<tr><td colspan="11" style="color:#888;text-align:center;padding:20px">No trades yet — agent scans at next ASX open (10am AEST weekdays)</td></tr>';
    } else {
        tbody.innerHTML = [...trades].reverse().map(t => {
            const oc = t.outcome==='WIN'?'#44bb44':t.outcome==='LOSS'?'#cc0000':'#ff9900';
            const pc = (t.pnl_pct||0)>=0?'#44bb44':'#cc0000';
            return '<tr><td>'+t.id+'</td><td><b>'+t.ticker+'</b></td>'
                +'<td>$'+(t.entry_price||0).toFixed(3)+'</td>'
                +'<td style="font-size:11px;color:#888">'+(t.entry_time||'').substring(0,16).replace('T',' ')+'</td>'
                +'<td style="color:#44bb44">$'+(t.target||0).toFixed(3)+'</td>'
                +'<td style="color:#cc0000">$'+(t.stop||0).toFixed(3)+'</td>'
                +'<td>'+(t.exit_price?'$'+t.exit_price.toFixed(3):'—')+'</td>'
                +'<td style="font-size:11px">'+(t.exit_reason||'OPEN')+'</td>'
                +'<td style="color:'+pc+';font-weight:bold">'+(t.pnl_pct!=null?(t.pnl_pct>=0?'+':'')+t.pnl_pct.toFixed(1)+'%':'—')+'</td>'
                +'<td style="color:'+oc+';font-weight:bold">'+(t.outcome||'OPEN')+'</td>'
                +'<td style="font-size:11px;color:#666">'+(t.conditions_met||0)+'/5 ✓</td></tr>';
        }).join('');
    }

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
    grid.innerHTML=d.signals.map(s=>{
        const sc=s.score||0;
        const bc=sc>=70?'#44bb44':sc>=50?'#ff9900':sc>=30?'#ff6600':'#cc0000';
        const ic=s.interpretation==='CALM'||s.interpretation==='TIGHT'||s.interpretation==='BROAD'||s.interpretation==='UPTREND'||s.interpretation==='CONTANGO'||s.interpretation==='GREEDY'?'#44bb44':
                 s.interpretation==='NEUTRAL'||s.interpretation==='NARROW'||s.interpretation==='NORMAL'||s.interpretation==='MIXED'?'#ff9900':'#cc0000';
        return `<div class="macro-signal-card">
            <div class="macro-signal-name">${s.name}</div>
            <div class="macro-signal-value" style="color:${bc}">${s.value_label||'—'}</div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                <span style="font-size:11px;color:#666">Score</span>
                <span style="font-size:16px;font-weight:bold;color:${bc}">${sc.toFixed(0)}/100</span>
            </div>
            <div class="macro-score-bar-wrap">
                <div class="macro-score-bar" style="width:${sc}%;background:${bc}"></div>
            </div>
            <div style="display:flex;justify-content:flex-end">
                <span style="font-size:11px;padding:2px 8px;border-radius:10px;background:${ic}22;color:${ic}">${s.interpretation||'?'}</span>
            </div>
            <div class="macro-signal-detail">${s.detail||''}</div>
        </div>`;
    }).join('');
}

// ── Quantitative Analysis tab ─────────────────────────────────────────────────
function renderQuantTab(section){
    document.querySelectorAll('.quant-btn').forEach(b=>b.classList.remove('active'));
    const btn=document.getElementById('qbtn-'+section);
    if(btn)btn.classList.add('active');
    const results=QUANT_DATA.results||{};
    const tickers=Object.keys(results);
    if(!tickers.length){
        document.getElementById('quantContent').innerHTML='<p style="color:#888;padding:20px">No quantitative data yet — click "Run Nightly Now" to generate.</p>';return;
    }
    if(section==='earnings')     renderEarnings(results,tickers);
    else if(section==='momentum')    renderMomentum(results,tickers);
    else if(section==='rsi')         renderRSIStrategy(results,tickers);
    else if(section==='ma')          renderMAStrategy(results,tickers);
    else if(section==='walkforward') renderWalkForward(results,tickers);
    else if(section==='montecarlo')  renderMonteCarlo(results,tickers);
    else if(section==='sensitivity') renderSensitivity(results,tickers);
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
    const s=(QUANT_DATA.results||{})[t]?.sensitivity||{};
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
  <button class="tab-btn active" onclick="showTab('market')">Market Analysis</button>
  <button class="tab-btn" onclick="showTab('market_status')">Market Status</button>
  <button class="tab-btn" onclick="showTab('portfolio')">Portfolio</button>
  <button class="tab-btn" onclick="showTab('addholder')">Add Holding</button>
  <button class="tab-btn" onclick="showTab('paper')">Paper Trades</button>
  <button class="tab-btn" onclick="showTab('asx')">ASX Scanner</button>
  <button class="tab-btn" onclick="showTab('watchlist')">Watchlist</button>
  <button class="tab-btn" onclick="showTab('history')">Signal History</button>
  <button class="tab-btn" onclick="showTab('backtest')">Backtest</button>
  <button class="tab-btn" onclick="showTab('quantitative')">Quantitative</button>
  <button class="tab-btn" onclick="showTab('intraday')">Day Trading</button>
  <button class="tab-btn" onclick="showTab('agent')">Agent Trader</button>
  <button class="tab-btn" onclick="showTab('token')">Token</button>
</nav>

<!-- TAB 1: Market Analysis -->
<div id="tab-market" class="tab-content active">
<div class="section">
  <div class="stats-grid">
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

<!-- TAB 4: Paper Trades -->
<div id="tab-paper" class="tab-content">
<div class="section">
<h2>Paper Trades</h2>
<p style="color:#888;font-size:13px;margin-bottom:15px">Simulated trades to test strategies before using real money.</p>
<table class="holdings-table"><thead><tr>
  <th>Ticker</th><th>Direction</th><th>Entry</th><th>Qty</th><th>Stop</th><th>Target</th><th>Opened</th><th>Status</th><th></th>
</tr></thead><tbody id="paperBody">
<tr><td colspan="9" style="color:#888;text-align:center;padding:20px">Use Add Holding tab to add paper trades.</td></tr>
</tbody></table>
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
  <button id="qbtn-ma"           class="quant-btn"         onclick="renderQuantTab('ma')">MA Crossover</button>
  <button id="qbtn-walkforward"  class="quant-btn"         onclick="renderQuantTab('walkforward')">Walk Forward</button>
  <button id="qbtn-montecarlo"   class="quant-btn"         onclick="renderQuantTab('montecarlo')">Monte Carlo</button>
  <button id="qbtn-sensitivity"  class="quant-btn"         onclick="renderQuantTab('sensitivity')">Sensitivity</button>
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


<!-- TAB: Market Status -->

<!-- TAB: Quantitative Analysis -->
<div id="tab-quantitative" class="tab-content">
<div class="section">
<h2>Quantitative Analysis</h2>
<div class="quant-subnav">
  <button id="qbtn-earnings"     class="quant-btn active"  onclick="renderQuantTab('earnings')">Earnings Reports</button>
  <button id="qbtn-momentum"     class="quant-btn"         onclick="renderQuantTab('momentum')">12-1 Momentum</button>
  <button id="qbtn-rsi"          class="quant-btn"         onclick="renderQuantTab('rsi')">RSI Strategy</button>
  <button id="qbtn-ma"           class="quant-btn"         onclick="renderQuantTab('ma')">MA Crossover</button>
  <button id="qbtn-walkforward"  class="quant-btn"         onclick="renderQuantTab('walkforward')">Walk Forward</button>
  <button id="qbtn-montecarlo"   class="quant-btn"         onclick="renderQuantTab('montecarlo')">Monte Carlo</button>
  <button id="qbtn-sensitivity"  class="quant-btn"         onclick="renderQuantTab('sensitivity')">Sensitivity</button>
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
<h2>Agent Trader — 30-Trade Strategy Test</h2>
<p style="color:#888;font-size:13px;margin-bottom:20px">
  Autonomous agent running ORB + VWAP breakout strategy. Scans every 5 min during ASX market hours (10am–4pm AEST) via GitHub Actions.
  Reviews entry/exit signals independently and records simulated trades. After 30 trades, strategy goes to paper trading.
</p>

<!-- Progress -->
<div style="background:#1a1a2e;border-radius:12px;padding:20px;margin-bottom:20px;border:1px solid #2a2a4a">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <span style="color:#ccc;font-weight:bold">Test Progress</span>
    <span id="agentProgress" style="color:#4a90d9;font-weight:bold">Loading...</span>
  </div>
  <div class="progress-bar-wrap"><div class="progress-bar" id="agentProgressBar" style="width:0%"></div></div>
  <div style="display:flex;justify-content:space-between;font-size:11px;color:#666">
    <span>0 trades</span><span id="agentStatus" style="color:#ff9900">Loading...</span><span>30 trades</span>
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

<!-- Trade log -->
<h3 style="color:#ccc;margin-bottom:12px">Trade Log</h3>
<div class="asx-table-wrap">
<table class="asx-table"><thead><tr>
  <th>#</th><th>Ticker</th><th>Entry</th><th>Entry Time</th>
  <th>Target</th><th>Stop</th><th>Exit</th><th>Exit Reason</th>
  <th>P&amp;L %</th><th>Outcome</th><th>Conditions</th>
</tr></thead><tbody id="agentTradeBody">
<tr><td colspan="11" style="color:#888;text-align:center;padding:20px">Loading trade history...</td></tr>
</tbody></table>
</div>

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
    <input id="ghToken" type="password" placeholder="ghp_xxxxxxxxxxxx" style="flex:1">
    <button class="btn-primary" onclick="saveToken()">Save Token</button>
  </div>
  <p style="color:#555;font-size:11px;margin-top:8px">Token is stored in your browser only (localStorage). Never shared or uploaded.</p>
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

{JS}
</body>
</html>"""

    HTML = HTML.replace('__MACRO_DATA__', json.dumps(macro or {}))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(HTML)
    print(f"Dashboard written: {output_path}")
