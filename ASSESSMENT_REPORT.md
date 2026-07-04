# Trader Performance vs Bitcoin Market Sentiment

## Executive summary

This assessment joins **211,218 Hyperliquid fill rows** with the daily Bitcoin Fear & Greed dataset using the calendar date from `Timestamp IST`. The joined sample covers **2023-05-01 to 2025-05-01**, **32 accounts**, **246 symbols**, and **479 active trading days**. The join rate is **99.997%**.

Across the matched sample, traders generated **$10,254,487 closed PnL** on **$1.191B volume**. Fees were **$245,849**, leaving **$10,008,638 after fees**. Win rate is calculated only on the **104,402 rows with non-zero `Closed PnL`**, and equals **83.2%**.

The most important conclusion is that **sentiment does not explain absolute daily PnL by itself**, but it does affect **how efficiently traders convert volume into PnL and which directional strategies work best**.

## Key findings

### 1. Extreme Greed had the strongest PnL efficiency

Extreme Greed produced **218.1 bps of closed PnL per dollar of volume**, compared with **69.5 bps in Fear** and **64.6 bps in Extreme Fear**. It also had the highest realized-fill win rate at **89.2%**.

This is more informative than comparing total PnL because each sentiment state contains a different number of active days and a different amount of trading volume.

### 2. Sentiment level has almost no relationship with raw daily PnL

The Spearman correlation between sentiment value and daily closed PnL is **ρ = 0.040** with **p = 0.384**, which is effectively no monotonic relationship.

However, sentiment has a **small positive relationship with daily PnL efficiency**: **ρ = 0.135, p = 0.0032**. Higher sentiment is associated with slightly better PnL per unit of traded volume, even though it does not reliably increase total daily profit.

### 3. Market sentiment matters much more after separating long and short exits

For `Close Short` fills, PnL per realized fill was:

- **Fear:** $207.9
- **Extreme Fear:** $123.4
- **Greed:** $55.2
- **Extreme Greed:** $29.0

This is the strongest actionable pattern in the data: **short-position exits were much more profitable during fearful markets than greedy markets**.

`Close Long` results were much more stable across sentiment states, so a single global “fear is good/bad” conclusion would hide the real relationship.

### 4. Non-crossed execution strongly outperformed crossed execution

Rows with `Crossed = FALSE` generated **$139.6 PnL per realized fill** and **154.7 bps PnL efficiency**. `Crossed = TRUE` generated **$71.8** and **55.5 bps**, respectively.

Fees were **$228,044** on crossed fills versus only **$17,805** on non-crossed fills. This suggests execution style and fee drag are at least as important as sentiment.

### 5. Trader-level results are heterogeneous

**29 of 32 accounts** were profitable overall, but the top five accounts generated **62.0% of total closed PnL**. Therefore, aggregate sentiment results are influenced by a relatively small group of high-PnL traders.

Among **28 accounts** with at least 20 realized fills in both Fear and Greed buckets, **20** had higher PnL per realized fill in Greed. The median Greed-minus-Fear improvement was **$42.3**, but the paired one-sided Wilcoxon test gives **p = 0.109**, so this account-level advantage is not statistically decisive at the 5% level.

## Recommended trading rules to test

1. **Use sentiment as a strategy selector, not as a standalone entry signal.** The overall sentiment score has weak explanatory power for absolute PnL.
2. **Allow more short-side opportunity during Fear, but reduce short exposure during Greed/Extreme Greed.** The close-short results show the largest sentiment regime difference.
3. **Track PnL per unit of volume and PnL after fees, not only total PnL.** Extreme Greed looks much stronger after normalizing by volume.
4. **Prefer non-crossed/passive execution when the strategy can tolerate it.** The dataset shows higher realized-fill PnL, higher PnL efficiency, and much lower fees for `Crossed = FALSE`.
5. **Build account-specific sentiment profiles.** The same sentiment regime does not affect every trader equally.

## Methodology

- Parsed `Timestamp IST` and joined each fill to the daily sentiment record by calendar date.
- Used the actual available columns only. The supplied trade file does **not** contain a leverage column, so leverage analysis was excluded.
- Treated the Hyperliquid file as **fill-level data**.
- Calculated win rate only on rows where `Closed PnL != 0`.
- Used PnL/volume in basis points as an efficiency metric: `(Closed PnL / Size USD) × 10,000`.
- Used daily Spearman rank correlation because the distributions are highly skewed and the relationship may not be linear.
- Used a paired account-level Fear-versus-Greed comparison only for accounts with at least 20 realized fills in both buckets.

## Data quality checks and limitations

- **6 of 211,224 trade rows** could not be matched to sentiment; all unmatched rows fall on **2024-10-26**.
- The exported `Trade ID` column is in scientific notation and collapses to only **2,810 distinct text values**, so it should **not** be used as a unique key.
- Many `Order ID` and transaction values repeat because the source is fill-level data; deduplicating these rows would destroy valid partial-fill information.
- `Closed PnL = 0` often corresponds to opening or non-realizing fills, not necessarily a losing trade.
- The sample contains only 32 accounts, so aggregate results should not be generalized to all Hyperliquid users.
- This is observational analysis. Sentiment and performance can both be influenced by volatility, market trend, trader selection, symbol mix, and time-period effects.

## Final conclusion

The strongest evidence is **not** that traders always perform better in Fear or Greed. The stronger conclusion is:

> **Market sentiment changes which trading behaviors work best.**

Fear strongly favors short-position exits in this sample, while Extreme Greed delivers the highest PnL efficiency overall. At the same time, execution quality and fee control have a very large relationship with realized performance. A smarter strategy would combine **sentiment regime + direction + execution style**, rather than using the Fear & Greed score alone.
