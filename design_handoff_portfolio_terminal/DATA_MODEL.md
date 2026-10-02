# Data model & ingestion

Companion to `README.md`. Everything here is what the UI needs to exist; nothing in the prototype's hardcoded values should be treated as real.

## Entities

**holding** — ticker, name, primary exchange, primary benchmark index code, currency, sector, active flag. Hand-maintained; 12 rows today.

**position** — ticker, quantity, average cost, as-of date. From the broker.

**daily_bar** — ticker, date, close, adjusted close, currency. One row per holding per trading day, kept permanently. This is the regression input and the only table that must never be lossy.

**factor_series** — factor code, date, value. Four series (petrol, coffee, wages, rates). Also permanent, also the regression input. Custom series cannot be backfilled cheaply, so start capturing before anything else.

**index_series** — index code, date, close. Needed both for the Dashboard Indices tile and as the regression's `r_index`.

**fx_rate** — pair, date, rate. GBP is the book currency; holdings are USD, EUR and GBP.

**model_fit** — ticker, fit date, lookback used, β per regressor, R², residual stdev, sample size. Derived and re-derivable; store it so the UI can show diagnostics and so a bad fit is diagnosable after the fact.

**expected_move** — ticker, date, expected return, actual return, residual, z, flag category (`unexplained` / `earnings` / `none`). One row per holding per day.

**attribution** — ticker, date, and the per-component contribution shown in the Book row drawer (index, sector/consumer, oil, residual). Falls out of the regression; store it rather than recomputing on read.

**factor_effect** — factor code, ticker, score, modelled flag, channel text. **Hand-authored judgement**, not derived — this is the Macro screen's entire content and the reason Macro is phased last. Score drives the band thresholds in the README; `channel` is the prose shown in the row and drawer; `modelled` distinguishes a holding with a real analysis from one on a sector prior.

**analysis** — the parsed research note per holding: strike date, EPS by scenario by fiscal year, reference multiple, sensitivities (code, label, move, % EPS impact, distance travelled, channel, aggregate flag), thesis text, what-changed diff, peers, parse warnings. Only BROS exists today; the UI already handles "no analysis" as the normal case.

**earnings_date** — ticker, date, fiscal period, confirmed flag. Drives the Dashboard calendar **and** the model's earnings-day suppression.

**dividend** — ticker, ex-date, pay date, amount, currency. Feeds the run-rate, yield-on-book and received-YTD figures.

## Ingestion jobs

| Job | Cadence | Source | Notes |
|---|---|---|---|
| Positions + cash | Daily, and on demand | Trading212 | Drives every weight in the app |
| Prices → `daily_bar` | Daily after each market close | Market data provider | Per-exchange close times; don't assume one cutoff |
| Index levels | Daily | Same provider | Five indices |
| FX | Daily | Any rate source | |
| Factor series | Daily or weekly per series | Mixed, some manual | Petrol and coffee are daily; wages is monthly and needs forward-filling |
| Model refit | Weekly | — | Betas drift slowly; daily refits add noise, not information |
| Expected moves | Daily, after prices | — | Uses the latest fit, not a same-day refit |
| Earnings dates | Weekly | — | Confirm before suppressing flags on them |
| Analysis parse | On demand | Research notes | Manual trigger; the pipeline behind the Analysis screen |

The account strip's "deposits cached 4h ago" and the header's "prices live" reflect real caching behaviour worth keeping: positions and deposits can be hours stale, prices should not be.

## Ticker → index map

One primary benchmark per holding, by primary listing. Hand-maintained. Used by both the Dashboard Indices tile and the Book weighting panel, and as `r_index` in the regression.

| Ticker | Index | Code |
|---|---|---|
| MSFT | Nasdaq 100 | NDX |
| COST | Nasdaq 100 | NDX |
| ASML | Nasdaq 100 | NDX |
| SBUX | Nasdaq 100 | NDX |
| V | S&P 500 | SPX |
| CMG | S&P 500 | SPX |
| CAVA | Russell 2000 | RUT |
| WING | Russell 2000 | RUT |
| BROS | Russell 2000 | RUT |
| TSM | Taiwan TAIEX | TWII |
| SHEL | FTSE 100 | UKX |
| RIO | FTSE 100 | UKX |

Assigned by primary listing, which is a judgement call in places — several of these names sit in more than one index, and ADRs (TSM, ASML) can reasonably be mapped to either the home market or the US listing. The map is deliberately editable in one place; expect to revise it. Cash (`GBP`) is excluded from index grouping but included in the total-book stacked bar.

Concentration limit: 40% of invested capital in one index. A constant, not a setting, unless the Settings screen grows to expose it.

## Derived figures

Specified so the same number never gets computed two different ways in two places:

- **Weight of book** — position market value in GBP ÷ total book value including cash.
- **Share of invested** — position or group market value ÷ book value **excluding** cash. The Book weighting bars and concentration flag use this; the Dashboard stacked bar uses weight of book.
- **Day P&L** — Σ (weight × daily return) × book value. The prototype computes it from weights rather than from per-position value changes; either is fine, but pick one.
- **Breadth** — count of holdings up vs down on the day, cash excluded.
- **Book tilt** — the Macro header verdict: the weight-averaged combined factor score across holdings, run through the same band thresholds.
- **CAGR** — money-weighted on net deposits since first deposit. The index comparison on the Dashboard is point-to-point index CAGR over the same period, which is not strictly comparable to a money-weighted return; label it as the rough read it is.
