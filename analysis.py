#!/usr/bin/env python3
"""
Trader Performance vs Bitcoin Market Sentiment

Reproducible assessment script.
Dependencies: numpy, scipy, matplotlib
No pandas is required.

Usage:
    python analysis.py \
        --trades historical_trader_data.csv \
        --sentiment bitcoin_sentiment.csv \
        --outdir output
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

SENTIMENT_ORDER = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]


def number(value: str) -> float:
    value = str(value).strip()
    return float(value) if value else 0.0


def load_sentiment(path: Path) -> dict[dt.date, tuple[float, str]]:
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            result[dt.date.fromisoformat(row["date"])] = (
                float(row["value"]),
                row["classification"].strip(),
            )
    return result


def summary_row(label: str, values: dict) -> dict:
    realized = values.get("realized", 0)
    volume = values.get("volume", 0)
    pnl = values.get("pnl", 0)
    fees = values.get("fees", 0)
    return {
        "label": label,
        "trades": int(values.get("trades", 0)),
        "volume_usd": volume,
        "closed_pnl": pnl,
        "fees": fees,
        "net_after_fees": pnl - fees,
        "realized_fills": int(realized),
        "win_rate": values.get("wins", 0) / realized if realized else None,
        "pnl_per_realized_fill": pnl / realized if realized else None,
        "pnl_margin_bps": pnl / volume * 10000 if volume else None,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def analyze(trades_path: Path, sentiment_path: Path, outdir: Path) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    sentiment_by_date = load_sentiment(sentiment_path)

    overall = defaultdict(float)
    by_sentiment = defaultdict(lambda: defaultdict(float))
    sentiment_accounts = defaultdict(set)
    daily = defaultdict(lambda: defaultdict(float))
    daily_accounts = defaultdict(set)
    by_account = defaultdict(lambda: defaultdict(float))
    account_days = defaultdict(set)
    account_sentiment = defaultdict(lambda: defaultdict(float))
    direction_sentiment = defaultdict(lambda: defaultdict(float))
    execution_sentiment = defaultdict(lambda: defaultdict(float))
    realized_pnls = defaultdict(list)
    coins = set()
    trade_id_text_values = set()
    unmatched_dates = Counter()
    date_min = date_max = None

    with trades_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            overall["rows"] += 1
            coins.add(row["Coin"].strip())
            trade_id_text_values.add(row["Trade ID"].strip())

            stamp = dt.datetime.strptime(row["Timestamp IST"].strip(), "%d-%m-%Y %H:%M")
            day = stamp.date()
            date_min = day if date_min is None or day < date_min else date_min
            date_max = day if date_max is None or day > date_max else date_max

            sentiment = sentiment_by_date.get(day)
            if sentiment is None:
                unmatched_dates[day] += 1
                continue

            sentiment_value, sentiment_class = sentiment
            account = row["Account"].strip()
            direction = row["Direction"].strip()
            crossed = row["Crossed"].strip().upper()
            volume = number(row["Size USD"])
            pnl = number(row["Closed PnL"])
            fee = number(row["Fee"])

            realized = int(pnl != 0)
            win = int(pnl > 0)
            loss = int(pnl < 0)
            metrics = {
                "trades": 1,
                "volume": volume,
                "pnl": pnl,
                "fees": fee,
                "realized": realized,
                "wins": win,
                "losses": loss,
            }

            overall["matched_rows"] += 1
            for key, value in metrics.items():
                overall[key] += value
                by_sentiment[sentiment_class][key] += value
                daily[day][key] += value
                by_account[account][key] += value
                account_sentiment[(account, sentiment_class)][key] += value
                direction_sentiment[(direction, sentiment_class)][key] += value
                execution_sentiment[(crossed, sentiment_class)][key] += value

            daily[day]["sentiment_value"] = sentiment_value
            daily[day]["class"] = sentiment_class
            daily_accounts[day].add(account)
            sentiment_accounts[sentiment_class].add(account)
            account_days[account].add(day)
            if realized:
                realized_pnls[sentiment_class].append(pnl)

    # Sentiment summary
    sentiment_rows = []
    for sentiment_class in SENTIMENT_ORDER:
        values = by_sentiment[sentiment_class]
        days = [d for d, v in daily.items() if v["class"] == sentiment_class]
        row = summary_row(sentiment_class, values)
        row.update({
            "sentiment_class": sentiment_class,
            "active_days": len(days),
            "active_accounts": len(sentiment_accounts[sentiment_class]),
            "avg_daily_pnl": float(np.mean([daily[d]["pnl"] for d in days])),
            "median_daily_pnl": float(np.median([daily[d]["pnl"] for d in days])),
            "median_realized_pnl": float(np.median(realized_pnls[sentiment_class])),
        })
        sentiment_rows.append(row)

    # Daily table
    daily_rows = []
    for day, values in sorted(daily.items()):
        realized = values["realized"]
        daily_rows.append({
            "date": day.isoformat(),
            "sentiment_value": values["sentiment_value"],
            "sentiment_class": values["class"],
            "trades": int(values["trades"]),
            "active_accounts": len(daily_accounts[day]),
            "volume_usd": values["volume"],
            "closed_pnl": values["pnl"],
            "fees": values["fees"],
            "net_after_fees": values["pnl"] - values["fees"],
            "realized_fills": int(realized),
            "win_rate": values["wins"] / realized if realized else None,
            "pnl_per_realized_fill": values["pnl"] / realized if realized else None,
            "pnl_margin_bps": values["pnl"] / values["volume"] * 10000 if values["volume"] else None,
        })

    # Account table
    account_rows = []
    for account, values in by_account.items():
        row = summary_row(account, values)
        row.update({
            "account": account,
            "active_days": len(account_days[account]),
            "avg_trade_size_usd": values["volume"] / values["trades"],
        })
        account_rows.append(row)
    account_rows.sort(key=lambda row: row["closed_pnl"], reverse=True)

    # Direction and execution tables
    direction_rows = []
    for (direction, sentiment_class), values in direction_sentiment.items():
        row = summary_row(f"{direction} | {sentiment_class}", values)
        row.update({"direction": direction, "sentiment_class": sentiment_class})
        direction_rows.append(row)

    execution_rows = []
    for (crossed, sentiment_class), values in execution_sentiment.items():
        row = summary_row(f"{crossed} | {sentiment_class}", values)
        row.update({"crossed": crossed, "sentiment_class": sentiment_class})
        execution_rows.append(row)

    # Daily Spearman relationships
    correlation_rows = []
    for metric in [
        "closed_pnl", "net_after_fees", "volume_usd", "trades",
        "win_rate", "pnl_per_realized_fill", "pnl_margin_bps", "active_accounts"
    ]:
        x = [row["sentiment_value"] for row in daily_rows if row[metric] is not None]
        y = [row[metric] for row in daily_rows if row[metric] is not None]
        test = stats.spearmanr(x, y)
        correlation_rows.append({
            "metric": metric,
            "rho": float(test.statistic),
            "p_value": float(test.pvalue),
        })

    # Export tables
    write_csv(outdir / "sentiment_summary.csv", sentiment_rows)
    write_csv(outdir / "daily_performance.csv", daily_rows)
    write_csv(outdir / "account_summary.csv", account_rows)
    write_csv(outdir / "direction_sentiment.csv", direction_rows)
    write_csv(outdir / "execution_sentiment.csv", execution_rows)
    write_csv(outdir / "correlations.csv", correlation_rows)

    # Results JSON
    result = {
        "rows": int(overall["rows"]),
        "matched_rows": int(overall["matched_rows"]),
        "match_rate": overall["matched_rows"] / overall["rows"],
        "date_min": date_min.isoformat(),
        "date_max": date_max.isoformat(),
        "accounts": len(by_account),
        "coins": len(coins),
        "volume_usd": overall["volume"],
        "closed_pnl": overall["pnl"],
        "fees": overall["fees"],
        "net_after_fees": overall["pnl"] - overall["fees"],
        "realized_fills": int(overall["realized"]),
        "win_rate": overall["wins"] / overall["realized"],
        "unmatched_rows": int(sum(unmatched_dates.values())),
        "unmatched_dates": [d.isoformat() for d in unmatched_dates],
        "distinct_trade_id_text_values": len(trade_id_text_values),
    }
    (outdir / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    # Charts
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(
        [row["sentiment_class"] for row in sentiment_rows],
        [row["pnl_margin_bps"] for row in sentiment_rows],
    )
    ax.set_title("PnL Efficiency by Market Sentiment")
    ax.set_ylabel("Closed PnL / Volume (basis points)")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(outdir / "sentiment_efficiency.png", dpi=180)
    plt.close(fig)

    return {
        "overall": result,
        "sentiment_summary": sentiment_rows,
        "daily_summary": daily_rows,
        "account_summary": account_rows,
        "direction_summary": direction_rows,
        "execution_summary": execution_rows,
        "correlations": correlation_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades", required=True, type=Path)
    parser.add_argument("--sentiment", required=True, type=Path)
    parser.add_argument("--outdir", default=Path("analysis_output"), type=Path)
    args = parser.parse_args()

    output = analyze(args.trades, args.sentiment, args.outdir)
    overall = output["overall"]
    print(json.dumps({
        "matched_rows": overall["matched_rows"],
        "closed_pnl": round(overall["closed_pnl"], 2),
        "net_after_fees": round(overall["net_after_fees"], 2),
        "win_rate": round(overall["win_rate"], 4),
    }, indent=2))


if __name__ == "__main__":
    main()
