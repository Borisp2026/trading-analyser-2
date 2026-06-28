"""
Buy/Sell Reasoning Engine for Trading Analyser 2.0
Produces human-readable analysis explaining WHY to buy/sell/hold,
suggested entry/exit prices, confidence level, and timing.
"""

import math


def generate_reasoning(ticker: str, tech: dict, cycle: dict, info: dict = None) -> dict:
    """
    Combines technical + cycle analysis into a buy/sell/hold recommendation
    with full written reasoning, entry price, stop loss, target, and confidence.

    tech   = output from technical.analyse_technicals()
    cycle  = output from cycle_analysis.analyse_cycles()
    info   = dict with company name, sector, dividend info (optional)
    """

    if not tech or tech.get("error"):
        return {"error": "Insufficient technical data"}

    price = tech.get("price", 0)
    tech_score = tech.get("tech_score", 50)
    cycle_score = cycle.get("cycle_score", 50) if cycle else 50

    # Blended score: 60% technical, 40% cycle
    blended_score = round(0.6 * tech_score + 0.4 * cycle_score, 1)

    # Overall recommendation
    if blended_score >= 70:
        recommendation = "STRONG BUY"
        rec_color = "#00aa00"
        timing = "Consider entering NOW or on next minor pullback"
    elif blended_score >= 58:
        recommendation = "BUY"
        rec_color = "#44bb44"
        timing = "Look for entry on pullback to support or confirmation signal"
    elif blended_score >= 45:
        recommendation = "HOLD / WATCH"
        rec_color = "#ff9900"
        timing = "Monitor — wait for clearer signal before entering"
    elif blended_score >= 30:
        recommendation = "WEAK / REDUCE"
        rec_color = "#ff6600"
        timing = "Reduce exposure or tighten stops on existing positions"
    else:
        recommendation = "AVOID / SELL"
        rec_color = "#cc0000"
        timing = "Avoid new entries. Exit or set tight stop-loss."

    # --- Build Reasons ---
    reasons = []

    # RSI
    rsi = tech.get("rsi", 50)
    rsi_prev = tech.get("rsi_prev", 50)
    if rsi < 30:
        reasons.append(f"RSI {rsi} is OVERSOLD — potential bounce setup")
    elif rsi < 40:
        reasons.append(f"RSI {rsi} approaching oversold — watch for reversal")
    elif rsi > 70:
        reasons.append(f"RSI {rsi} is OVERBOUGHT — caution, may pull back")
    elif rsi > 60:
        reasons.append(f"RSI {rsi} elevated — momentum strong but extended")
    else:
        reasons.append(f"RSI {rsi} neutral")
    if rsi > rsi_prev:
        reasons.append("RSI trending UP — momentum building")
    else:
        reasons.append("RSI trending DOWN — momentum weakening")

    # MACD
    if tech.get("macd_bullish_cross"):
        reasons.append("✅ MACD BULLISH CROSSOVER — strong buy signal")
    elif tech.get("macd_death_cross"):
        reasons.append("❌ MACD DEATH CROSS — bearish signal, selling pressure")
    elif tech.get("macd", 0) > tech.get("macd_signal", 0):
        reasons.append("MACD above signal line — mild bullish bias")
    else:
        reasons.append("MACD below signal line — mild bearish bias")

    # Bollinger Bands
    pct_b = tech.get("pct_b", 0.5)
    if pct_b < 0.1:
        reasons.append(f"Price near LOWER Bollinger Band (%B={pct_b}) — potential mean reversion opportunity")
    elif pct_b > 0.9:
        reasons.append(f"Price near UPPER Bollinger Band (%B={pct_b}) — extended, risk of reversal")
    else:
        reasons.append(f"Price within Bollinger Bands (%B={pct_b}) — normal range")

    # Volume
    vol = tech.get("volume_signal", {})
    if vol.get("signal") == "EXTREME_SPIKE":
        reasons.append(f"⚡ EXTREME VOLUME SPIKE ({vol.get('ratio', 0)}x average) — major institutional activity")
    elif vol.get("signal") == "HIGH_VOLUME":
        reasons.append(f"High volume ({vol.get('ratio', 0)}x average) — conviction behind the move")
    elif vol.get("signal") == "LOW_VOLUME":
        reasons.append("Low volume — move may lack conviction")

    # Trend
    if tech.get("golden_cross"):
        reasons.append("✅ GOLDEN CROSS (50D SMA > 200D SMA) — long-term uptrend")
    elif tech.get("golden_cross") is False:
        reasons.append("❌ DEATH CROSS (50D SMA < 200D SMA) — long-term downtrend")
    if tech.get("above_50sma"):
        reasons.append("Price above 50-day SMA — medium-term uptrend intact")
    elif tech.get("above_50sma") is False:
        reasons.append("Price below 50-day SMA — medium-term trend bearish")

    # Stochastic
    sk = tech.get("stoch_k", 50)
    if sk < 20:
        reasons.append(f"Stochastic K={sk} — oversold, watch for %K/%D crossover as entry trigger")
    elif sk > 80:
        reasons.append(f"Stochastic K={sk} — overbought")

    # 52-week position
    pct_52w = tech.get("pct_from_52w_high", 0)
    if pct_52w < -40:
        reasons.append(f"Stock is {abs(pct_52w)}% below 52-week high — deep discount, high risk/reward")
    elif pct_52w < -20:
        reasons.append(f"Stock is {abs(pct_52w)}% below 52-week high — discounted")
    elif pct_52w > -5:
        reasons.append(f"Near 52-week HIGH — breakout potential but extended")

    # Cycle reasons
    if cycle and cycle.get("status") == "ok":
        cycle_reasons = cycle.get("reasons", [])
        reasons.extend(cycle_reasons)

    # --- Entry / Exit Prices ---
    atr = tech.get("atr", 0)
    stop_loss = tech.get("stop_loss")
    take_profit = tech.get("take_profit")

    # Refine entry: if oversold/near support, enter at market or slight dip
    if blended_score >= 58:
        entry_price = round(price * 0.99, 4)  # slight dip entry
        entry_type = "Limit order ~1% below current price"
    elif blended_score >= 45:
        entry_price = round(price * 0.97, 4)  # wait for pullback
        entry_type = "Wait for 3% pullback before entering"
    else:
        entry_price = None
        entry_type = "Do not enter — wait for conditions to improve"

    # Stop loss refinement using cycle HCL if available
    cycle_hcl = None
    if cycle and cycle.get("current_cycle"):
        cycle_hcl = cycle["current_cycle"].get("hcl_price")

    if cycle_hcl and cycle_hcl < price:
        stop_loss = round(cycle_hcl * 0.99, 4)  # just below HCL trendline
        stop_note = f"Stop just below cycle HCL trendline (${cycle_hcl})"
    elif stop_loss:
        stop_note = f"Stop 1.5x ATR below entry (ATR=${atr})"
    else:
        stop_note = "Set stop manually"

    # Confidence
    spread = abs(blended_score - 50)
    if spread >= 20:
        confidence = "HIGH"
    elif spread >= 10:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # Dividend info
    dividend_note = None
    if info:
        div_yield = info.get("dividendYield")
        ex_date = info.get("exDividendDate")
        if div_yield:
            dividend_note = f"Dividend yield: {round(div_yield * 100, 2)}%"
            if ex_date:
                dividend_note += f" | Ex-dividend: {ex_date}"

    return {
        "ticker": ticker,
        "recommendation": recommendation,
        "rec_color": rec_color,
        "blended_score": blended_score,
        "tech_score": tech_score,
        "cycle_score": cycle_score,
        "confidence": confidence,
        "timing": timing,
        "reasons": reasons,
        "price": price,
        "entry_price": entry_price,
        "entry_type": entry_type,
        "stop_loss": stop_loss,
        "stop_note": stop_note,
        "take_profit": take_profit,
        "dividend_note": dividend_note,
        "risk_reward": round((take_profit - price) / (price - stop_loss), 2) if (take_profit and stop_loss and price > stop_loss) else None,
    }
