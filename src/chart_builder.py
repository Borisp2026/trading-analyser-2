"""
Chart Builder — Trading Analyser 2.0
- PDF: matplotlib candlestick + RSI + MACD + volume subplots (saved as PNG embedded in PDF)
- Dashboard: returns OHLCV + indicator JSON for lightweight-charts in browser
"""
import os
import json
import base64
from io import BytesIO
import pandas as pd
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.gridspec import GridSpec
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# ── PDF chart (matplotlib) ─────────────────────────────────────────────────────

def _calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=period-1, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period-1, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig, macd - sig

def build_pdf_chart(df: pd.DataFrame, ticker: str, tech: dict) -> bytes:
    """
    Build a 90-day chart with candlesticks, Bollinger Bands, RSI, MACD, volume.
    Returns PNG bytes to embed in PDF.
    """
    if not MATPLOTLIB_AVAILABLE or df is None or len(df) < 30:
        return None

    try:
        df90 = df.tail(90).copy()
        df90.index = pd.to_datetime(df90.index)
        close = df90["Close"]
        high = df90["High"]
        low = df90["Low"]
        volume = df90["Volume"]
        x = range(len(df90))

        # Indicators
        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()
        std = close.rolling(20).std()
        bb_upper = sma20 + 2 * std
        bb_lower = sma20 - 2 * std
        rsi = _calc_rsi(close)
        macd_line, signal_line, histogram = _calc_macd(close)

        # Plot setup
        fig = plt.figure(figsize=(12, 9), facecolor="#0f0f1a")
        gs = GridSpec(4, 1, figure=fig, hspace=0.05,
                      height_ratios=[3, 0.8, 0.8, 0.8])

        ax1 = fig.add_subplot(gs[0])  # Price + BB
        ax2 = fig.add_subplot(gs[1], sharex=ax1)  # Volume
        ax3 = fig.add_subplot(gs[2], sharex=ax1)  # RSI
        ax4 = fig.add_subplot(gs[3], sharex=ax1)  # MACD

        for ax in [ax1, ax2, ax3, ax4]:
            ax.set_facecolor("#13132a")
            ax.tick_params(colors="#888", labelsize=7)
            ax.spines[:].set_color("#2a2a4a")
            ax.yaxis.label.set_color("#888")

        # Candlesticks
        for i, (idx, row) in enumerate(df90.iterrows()):
            color = "#44bb44" if row["Close"] >= row["Open"] else "#cc0000"
            ax1.plot([i, i], [row["Low"], row["High"]], color=color, linewidth=0.8)
            rect = plt.Rectangle((i - 0.3, min(row["Open"], row["Close"])),
                                  0.6, abs(row["Close"] - row["Open"]),
                                  color=color, linewidth=0)
            ax1.add_patch(rect)

        # Bollinger Bands
        ax1.plot(x, bb_upper.values, color="#4a90d9", linewidth=0.6, alpha=0.6, linestyle="--")
        ax1.plot(x, sma20.values, color="#ff9900", linewidth=0.8, alpha=0.8)
        ax1.plot(x, bb_lower.values, color="#4a90d9", linewidth=0.6, alpha=0.6, linestyle="--")
        ax1.fill_between(x, bb_lower.values, bb_upper.values, alpha=0.05, color="#4a90d9")
        ax1.plot(x, sma50.values, color="#cc88ff", linewidth=0.8, alpha=0.7, linestyle="-.")

        ax1.set_ylabel("Price", color="#888", fontsize=8)
        ax1.set_title(f"{ticker} — 90 Day Chart", color="white", fontsize=11, pad=6)
        ax1.legend(
            [mpatches.Patch(color="#ff9900"), mpatches.Patch(color="#cc88ff"), mpatches.Patch(color="#4a90d9", alpha=0.4)],
            ["SMA20", "SMA50", "Bollinger Bands"],
            loc="upper left", fontsize=7, facecolor="#13132a", edgecolor="#2a2a4a", labelcolor="white"
        )

        # Volume
        vol_colors = ["#44bb44" if df90["Close"].iloc[i] >= df90["Open"].iloc[i] else "#cc0000" for i in range(len(df90))]
        ax2.bar(x, volume.values, color=vol_colors, alpha=0.7, width=0.8)
        avg_vol = volume.rolling(20).mean()
        ax2.plot(x, avg_vol.values, color="#ff9900", linewidth=0.8)
        ax2.set_ylabel("Volume", color="#888", fontsize=7)

        # RSI
        ax3.plot(x, rsi.values, color="#4a90d9", linewidth=1)
        ax3.axhline(70, color="#cc0000", linewidth=0.6, linestyle="--")
        ax3.axhline(30, color="#44bb44", linewidth=0.6, linestyle="--")
        ax3.fill_between(x, 30, rsi.values, where=(rsi.values < 30), alpha=0.2, color="#44bb44")
        ax3.fill_between(x, 70, rsi.values, where=(rsi.values > 70), alpha=0.2, color="#cc0000")
        ax3.set_ylim(0, 100)
        ax3.set_ylabel("RSI", color="#888", fontsize=7)
        ax3.tick_params(labelbottom=False)

        # MACD
        bar_colors = ["#44bb44" if v >= 0 else "#cc0000" for v in histogram.values]
        ax4.bar(x, histogram.values, color=bar_colors, alpha=0.6, width=0.8)
        ax4.plot(x, macd_line.values, color="#4a90d9", linewidth=0.9)
        ax4.plot(x, signal_line.values, color="#ff9900", linewidth=0.9)
        ax4.axhline(0, color="#444", linewidth=0.5)
        ax4.set_ylabel("MACD", color="#888", fontsize=7)

        # X-axis labels (show every ~15 bars)
        step = max(1, len(df90) // 6)
        xtick_pos = list(range(0, len(df90), step))
        xtick_labels = [df90.index[i].strftime("%d %b") for i in xtick_pos]
        ax4.set_xticks(xtick_pos)
        ax4.set_xticklabels(xtick_labels, fontsize=7, color="#888")

        plt.tight_layout()
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                    facecolor="#0f0f1a", edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except Exception as e:
        print(f"Chart error for {ticker}: {e}")
        return None


def chart_to_base64(chart_bytes: bytes) -> str:
    """Convert chart PNG bytes to base64 string for embedding."""
    if not chart_bytes:
        return ""
    return base64.b64encode(chart_bytes).decode("utf-8")


# ── Dashboard chart data (JSON for lightweight-charts) ─────────────────────────

def build_chart_data(df: pd.DataFrame, ticker: str) -> dict:
    """
    Returns OHLCV + indicator data as JSON-serialisable dict
    for rendering in the browser with lightweight-charts.
    """
    if df is None or len(df) < 30:
        return {}

    try:
        df90 = df.tail(120).copy()
        close = df90["Close"]
        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()
        std = close.rolling(20).std()
        bb_upper = sma20 + 2 * std
        bb_lower = sma20 - 2 * std
        rsi = _calc_rsi(close)

        def to_ts(idx):
            try:
                return int(pd.Timestamp(idx).timestamp())
            except Exception:
                return 0

        candles = []
        for idx, row in df90.iterrows():
            candles.append({
                "time": to_ts(idx),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
            })

        def series(s):
            return [{"time": to_ts(idx), "value": round(float(v), 4)}
                    for idx, v in s.items() if not pd.isna(v)]

        return {
            "ticker": ticker,
            "candles": candles,
            "sma20": series(sma20),
            "sma50": series(sma50),
            "bb_upper": series(bb_upper),
            "bb_lower": series(bb_lower),
            "rsi": series(rsi),
            "volume": [{"time": to_ts(idx), "value": int(row["Volume"])}
                       for idx, row in df90.iterrows()],
        }
    except Exception as e:
        print(f"Chart data error {ticker}: {e}")
        return {}
