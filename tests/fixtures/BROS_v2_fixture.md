# Dutch Bros (BROS) — Stock Model v2
**Data as of:** 2026-07-28 · **Sources:** FY2025 10-K; Q1 FY2026 release · **NYSE** · figures in USD m · price in USD
Up-C: EPS on total NI ÷ total economic shares (Class A + LLC units).

Source tags: **G** guidance · **F** filing · **A** assumption. Live price → PE computed by the app.

## 1. Revenue
| Segment | FY2025A | FY2026 growth | FY2026 | FY2027 growth | FY2027 | FY2028 growth | FY2028 |
|---|---|---|---|---|---|---|---|
| Company-operated | 1,509 | +27.1% G | 1,918 | +25.7% A | 2,411 | +23.7% A | 2,982 |
| Franchise / other | 129 | +5.4% A | 136 | +6.6% A | 145 | +5.5% A | 153 |
| **Total** | **1,638** | **+25.4%** | **2,054** | **+24.4%** | **2,556** | **+22.7%** | **3,135** |

| Ref | Basis |
|---|---|
| Company-operated base | FY2025 10-K segment note |
| Company-operated FY2026 | G: FY26 rev guide $2.05–2.08bn; ≥185 openings + 4–6% comps |
| Company-operated FY2027 | A: ~210 openings + 4.5% comps |
| Company-operated FY2028 | A: ~235 openings + 4.5% comps |
| Franchise / other base | FY2025 10-K segment note |
| Franchise / other FY2026 | A: Few franchise openings; royalty on comps |
| Franchise / other FY2027 | A: As prior year |
| Franchise / other FY2028 | A: As prior year |

## 2. Operating margin → net income → EPS (BAU)
| Line | FY2026 | FY2027 | FY2028 |
|---|---|---|---|
| Revenue | 2,054 | 2,556 | 3,135 |
| Operating margin | 12.8% G | 14.2% A | 15.5% A |
| Operating income | 263 | 363 | 486 |
| Net interest | -37 A | -53 A | -69 A |
| Tax rate | 16.0% F | 16.0% A | 16.0% A |
| **Net income** | **190** | **260** | **350** |
| Diluted shares (m) | 187.7 | 187.7 | 187.7 |
| **EPS** | **1.01** | **1.39** | **1.87** |

| Ref | Basis |
|---|---|
| Margin FY2026 | G: Implied by $370–380m adj. EBITDA guide less ~$112m D&A |
| Margin FY2027 | A: SG&A 13.5%→12.5% of revenue |
| Margin FY2028 | A: SG&A →11.5% of revenue |
| Interest FY2026 | A: Debt-funded capex at 6.5% |
| Interest FY2027 | A: As above |
| Interest FY2028 | A: As above |
| Tax FY2026 | F: FY2025 effective rate (Up-C) |
| Tax FY2027 | A: Held |
| Tax FY2028 | A: Held |

## 3. Shares
Base diluted: **187.7m** — Q1 FY2026 10-Q: Class A + Class B/D economic units

| Year | Change | Basis |
|---|---|---|
| FY2026 | +0.0% | none |
| FY2027 | +0.0% | none |
| FY2028 | +0.0% | none |

## 4. Scenarios (deltas vs BAU, every forecast year)
| | Growth Δ (pp) | Margin Δ (pp) | Basis |
|---|---|---|---|
| LOW | -8.0 | -3.0 | Openings slow to ~160/yr, comps +2%, no SG&A leverage |
| HIGH | +4.0 | +1.5 | Openings 200→270, comps +6.5%, CAVA-style margin path |

| EPS | FY2026 | FY2027 | FY2028 |
|---|---|---|---|
| LOW | 0.68 | 0.89 | 1.13 |
| BAU | 1.01 | 1.39 | 1.87 |
| HIGH | 1.19 | 1.68 | 2.31 |

Forward PE at reference price 64.67 USD (2026-07-28; snapshot only — app uses live):

| PE | FY2026 | FY2027 | FY2028 |
|---|---|---|---|
| LOW | 95.4x | 73.1x | 57.3x |
| BAU | 64.0x | 46.6x | 34.7x |
| HIGH | 54.3x | 38.6x | 27.9x |

## 5. Calendar
| Date | Event | Type | Confirmed | Source |
|---|---|---|---|---|
| 2026-08-05 | Q2 FY2026 results | earnings | yes | IR site |
| 2026-11-04 | Q3 FY2026 results | earnings | est. | Prior-year pattern |

## 6. Macro
| Factor | Channel | Direction | Strength | Speed | Why |
|---|---|---|---|---|---|
| us_gasoline_retail | demand | bear | medium | near | Drive-thru traffic; +$1/gal ≈ −1.5pp comps |
| oil | cost | bear | mild | near | Packaging + freight ≈ +0.6pp CoS |
| labour | cost | bear | strong | immediate | Shop labour inside 74% CoS |
| rates_10y | valuation | bear | strong | immediate | ~100x long-duration equity |
| rates_policy | earnings | bear | mild | near | Interest ~2% of revenue |

**Suggested backtests** (run by app against daily returns)

| Factor | Series | Provider | Frequency | Lookback | Hypothesis |
|---|---|---|---|---|---|
| us_gasoline_retail | GASREGW | FRED | weekly | 4y | Negative beta to US retail gasoline via traffic |
| rates_10y | DGS10 | FRED | weekly | 4y | Strong negative beta — multiple compression |

**Proposed new macro factors** (not on fixed list — approve before tracking)

| Code | Name | Series | Provider | Scope | Other names affected | Why |
|---|---|---|---|---|---|---|
| us_gasoline_retail | US retail gasoline price | GASREGW | FRED | company | — | Pump price, not crude, drives drive-thru traffic; crude lags and misses refining margin |

## 7. Lever register
| Base | Lever | Exposure | Speed | Rising = | Factor | Watch metric | Current | Pushes LOW | Pushes HIGH |
|---|---|---|---|---|---|---|---|---|---|
| cost | Shop labour | partial (30%) | immediate | bear | labour | State minimum-wage changes | CA/OR/WA rises Jan 2026 | Wage inflation >5% | Labour scheduling gains |

## 8. Scorecard — suggested starting point (yours to overwrite in the app)
| Dimension | Score (1–5) | Basis |
|---|---|---|
| Growth | 5 | BAU revenue CAGR ~24% FY25–28; ≥185 openings/yr guided |
| Value | 1 | ~65x FY26 BAU EPS; above all peers except CAVA |
| Income | 1 | No dividend, no buyback; all cash into openings |

**Bull catalysts**
- Q2 comps ≥ +6% with positive transactions (2026-08-05)
- Raised FY26 opening guidance

**Bear catalysts**
- US gasoline > $4/gal sustained
- SG&A % of revenue fails to fall in H2

## 9. Bottom line
ILLUSTRATIVE FIXTURE built from the July 2026 BROS file — not a refreshed analysis.

## Model (parsed by webapp — do not edit by hand; regenerate with model.py)
```json stock-model
{
 "meta": {
  "ticker": "BROS",
  "company": "Dutch Bros",
  "exchange": "NYSE",
  "reporting_currency": "USD",
  "price_currency": "USD",
  "units": "m",
  "fiscal_year_end": "12-31",
  "base_year": "FY2025",
  "forecast_years": [
   "FY2026",
   "FY2027",
   "FY2028"
  ],
  "data_as_of": "2026-07-28",
  "data_sources": [
   "FY2025 10-K",
   "Q1 FY2026 release"
  ],
  "structure_note": "Up-C: EPS on total NI \u00f7 total economic shares (Class A + LLC units).",
  "reference_price": {
   "value": 64.67,
   "date": "2026-07-28"
  }
 },
 "revenue": {
  "segments": [
   {
    "name": "Company-operated",
    "base": 1509,
    "base_ref": "FY2025 10-K segment note",
    "growth": [
     {
      "pct": 27.1,
      "source": "guidance",
      "ref": "FY26 rev guide $2.05\u20132.08bn; \u2265185 openings + 4\u20136% comps"
     },
     {
      "pct": 25.7,
      "source": "assumption",
      "ref": "~210 openings + 4.5% comps"
     },
     {
      "pct": 23.7,
      "source": "assumption",
      "ref": "~235 openings + 4.5% comps"
     }
    ]
   },
   {
    "name": "Franchise / other",
    "base": 129,
    "base_ref": "FY2025 10-K segment note",
    "growth": [
     {
      "pct": 5.4,
      "source": "assumption",
      "ref": "Few franchise openings; royalty on comps"
     },
     {
      "pct": 6.6,
      "source": "assumption",
      "ref": "As prior year"
     },
     {
      "pct": 5.5,
      "source": "assumption",
      "ref": "As prior year"
     }
    ]
   }
  ]
 },
 "operating_margin": [
  {
   "pct": 12.8,
   "source": "guidance",
   "ref": "Implied by $370\u2013380m adj. EBITDA guide less ~$112m D&A"
  },
  {
   "pct": 14.2,
   "source": "assumption",
   "ref": "SG&A 13.5%\u219212.5% of revenue"
  },
  {
   "pct": 15.5,
   "source": "assumption",
   "ref": "SG&A \u219211.5% of revenue"
  }
 ],
 "net_interest": [
  {
   "value": -37,
   "source": "assumption",
   "ref": "Debt-funded capex at 6.5%"
  },
  {
   "value": -53,
   "source": "assumption",
   "ref": "As above"
  },
  {
   "value": -69,
   "source": "assumption",
   "ref": "As above"
  }
 ],
 "tax_rate": [
  {
   "pct": 16,
   "source": "filing",
   "ref": "FY2025 effective rate (Up-C)"
  },
  {
   "pct": 16,
   "source": "assumption",
   "ref": "Held"
  },
  {
   "pct": 16,
   "source": "assumption",
   "ref": "Held"
  }
 ],
 "shares": {
  "base_diluted": 187.7,
  "base_ref": "Q1 FY2026 10-Q: Class A + Class B/D economic units",
  "annual_change": [
   {
    "pct": 0,
    "source": "none"
   },
   {
    "pct": 0,
    "source": "none"
   },
   {
    "pct": 0,
    "source": "none"
   }
  ]
 },
 "scenarios": {
  "low": {
   "growth_pp": -8,
   "margin_pp": -3,
   "ref": "Openings slow to ~160/yr, comps +2%, no SG&A leverage"
  },
  "high": {
   "growth_pp": 4,
   "margin_pp": 1.5,
   "ref": "Openings 200\u2192270, comps +6.5%, CAVA-style margin path"
  }
 },
 "calendar": [
  {
   "date": "2026-08-05",
   "event": "Q2 FY2026 results",
   "type": "earnings",
   "confirmed": true,
   "source": "IR site"
  },
  {
   "date": "2026-11-04",
   "event": "Q3 FY2026 results",
   "type": "earnings",
   "confirmed": false,
   "source": "Prior-year pattern"
  }
 ],
 "macro": [
  {
   "factor": "us_gasoline_retail",
   "channel": "demand",
   "direction": "bear",
   "strength": "medium",
   "speed": "near",
   "ref": "Drive-thru traffic; +$1/gal \u2248 \u22121.5pp comps"
  },
  {
   "factor": "oil",
   "channel": "cost",
   "direction": "bear",
   "strength": "mild",
   "speed": "near",
   "ref": "Packaging + freight \u2248 +0.6pp CoS"
  },
  {
   "factor": "labour",
   "channel": "cost",
   "direction": "bear",
   "strength": "strong",
   "speed": "immediate",
   "ref": "Shop labour inside 74% CoS"
  },
  {
   "factor": "rates_10y",
   "channel": "valuation",
   "direction": "bear",
   "strength": "strong",
   "speed": "immediate",
   "ref": "~100x long-duration equity"
  },
  {
   "factor": "rates_policy",
   "channel": "earnings",
   "direction": "bear",
   "strength": "mild",
   "speed": "near",
   "ref": "Interest ~2% of revenue"
  }
 ],
 "backtests": [
  {
   "factor": "us_gasoline_retail",
   "series": "GASREGW",
   "provider": "FRED",
   "frequency": "weekly",
   "lookback": "4y",
   "hypothesis": "Negative beta to US retail gasoline via traffic"
  },
  {
   "factor": "rates_10y",
   "series": "DGS10",
   "provider": "FRED",
   "frequency": "weekly",
   "lookback": "4y",
   "hypothesis": "Strong negative beta \u2014 multiple compression"
  }
 ],
 "levers": [
  {
   "base": "cost",
   "lever_name": "Shop labour",
   "exposure": "partial",
   "exposure_pct": 30,
   "speed": "immediate",
   "direction": "bear",
   "macro_factor_code": "labour",
   "watch_metric": "State minimum-wage changes",
   "current_reading": "CA/OR/WA rises Jan 2026",
   "pushes_low": "Wage inflation >5%",
   "pushes_high": "Labour scheduling gains"
  }
 ],
 "bottom_line": "ILLUSTRATIVE FIXTURE built from the July 2026 BROS file \u2014 not a refreshed analysis.",
 "proposed_factors": [
  {
   "code": "us_gasoline_retail",
   "name": "US retail gasoline price",
   "series": "GASREGW",
   "provider": "FRED",
   "scope": "company",
   "other_names": [],
   "rationale": "Pump price, not crude, drives drive-thru traffic; crude lags and misses refining margin"
  }
 ],
 "scorecard_suggested": {
  "growth": {
   "score": 5,
   "ref": "BAU revenue CAGR ~24% FY25\u201328; \u2265185 openings/yr guided"
  },
  "value": {
   "score": 1,
   "ref": "~65x FY26 BAU EPS; above all peers except CAVA"
  },
  "income": {
   "score": 1,
   "ref": "No dividend, no buyback; all cash into openings"
  },
  "bull_catalysts": [
   {
    "text": "Q2 comps \u2265 +6% with positive transactions",
    "date": "2026-08-05"
   },
   {
    "text": "Raised FY26 opening guidance"
   }
  ],
  "bear_catalysts": [
   {
    "text": "US gasoline > $4/gal sustained"
   },
   {
    "text": "SG&A % of revenue fails to fall in H2"
   }
  ]
 },
 "schema_version": 2,
 "outputs": {
  "base_revenue": 1638,
  "scenarios": {
   "bau": [
    {
     "year": "FY2026",
     "segments": {
      "Company-operated": {
       "growth_pct": 27.1,
       "revenue": 1917.9
      },
      "Franchise / other": {
       "growth_pct": 5.4,
       "revenue": 136.0
      }
     },
     "revenue": 2053.9,
     "revenue_growth_pct": 25.39,
     "operating_margin_pct": 12.8,
     "operating_income": 262.9,
     "pretax": 225.9,
     "tax": 36.1,
     "net_income": 189.8,
     "shares_diluted": 187.7,
     "eps": 1.011
    },
    {
     "year": "FY2027",
     "segments": {
      "Company-operated": {
       "growth_pct": 25.7,
       "revenue": 2410.8
      },
      "Franchise / other": {
       "growth_pct": 6.6,
       "revenue": 144.9
      }
     },
     "revenue": 2555.8,
     "revenue_growth_pct": 24.44,
     "operating_margin_pct": 14.2,
     "operating_income": 362.9,
     "pretax": 309.9,
     "tax": 49.6,
     "net_income": 260.3,
     "shares_diluted": 187.7,
     "eps": 1.387
    },
    {
     "year": "FY2028",
     "segments": {
      "Company-operated": {
       "growth_pct": 23.7,
       "revenue": 2982.2
      },
      "Franchise / other": {
       "growth_pct": 5.5,
       "revenue": 152.9
      }
     },
     "revenue": 3135.1,
     "revenue_growth_pct": 22.67,
     "operating_margin_pct": 15.5,
     "operating_income": 485.9,
     "pretax": 416.9,
     "tax": 66.7,
     "net_income": 350.2,
     "shares_diluted": 187.7,
     "eps": 1.8659
    }
   ],
   "low": [
    {
     "year": "FY2026",
     "segments": {
      "Company-operated": {
       "growth_pct": 19.1,
       "revenue": 1797.2
      },
      "Franchise / other": {
       "growth_pct": -2.6,
       "revenue": 125.6
      }
     },
     "revenue": 1922.9,
     "revenue_growth_pct": 17.39,
     "operating_margin_pct": 9.8,
     "operating_income": 188.4,
     "pretax": 151.4,
     "tax": 24.2,
     "net_income": 127.2,
     "shares_diluted": 187.7,
     "eps": 0.6777
    },
    {
     "year": "FY2027",
     "segments": {
      "Company-operated": {
       "growth_pct": 17.7,
       "revenue": 2115.3
      },
      "Franchise / other": {
       "growth_pct": -1.4,
       "revenue": 123.9
      }
     },
     "revenue": 2239.2,
     "revenue_growth_pct": 16.45,
     "operating_margin_pct": 11.2,
     "operating_income": 250.8,
     "pretax": 197.8,
     "tax": 31.6,
     "net_income": 166.1,
     "shares_diluted": 187.7,
     "eps": 0.8852
    },
    {
     "year": "FY2028",
     "segments": {
      "Company-operated": {
       "growth_pct": 15.7,
       "revenue": 2447.4
      },
      "Franchise / other": {
       "growth_pct": -2.5,
       "revenue": 120.8
      }
     },
     "revenue": 2568.2,
     "revenue_growth_pct": 14.69,
     "operating_margin_pct": 12.5,
     "operating_income": 321.0,
     "pretax": 252.0,
     "tax": 40.3,
     "net_income": 211.7,
     "shares_diluted": 187.7,
     "eps": 1.1279
    }
   ],
   "high": [
    {
     "year": "FY2026",
     "segments": {
      "Company-operated": {
       "growth_pct": 31.1,
       "revenue": 1978.3
      },
      "Franchise / other": {
       "growth_pct": 9.4,
       "revenue": 141.1
      }
     },
     "revenue": 2119.4,
     "revenue_growth_pct": 29.39,
     "operating_margin_pct": 14.3,
     "operating_income": 303.1,
     "pretax": 266.1,
     "tax": 42.6,
     "net_income": 223.5,
     "shares_diluted": 187.7,
     "eps": 1.1908
    },
    {
     "year": "FY2027",
     "segments": {
      "Company-operated": {
       "growth_pct": 29.7,
       "revenue": 2565.9
      },
      "Franchise / other": {
       "growth_pct": 10.6,
       "revenue": 156.1
      }
     },
     "revenue": 2721.9,
     "revenue_growth_pct": 28.43,
     "operating_margin_pct": 15.7,
     "operating_income": 427.3,
     "pretax": 374.3,
     "tax": 59.9,
     "net_income": 314.4,
     "shares_diluted": 187.7,
     "eps": 1.6753
    },
    {
     "year": "FY2028",
     "segments": {
      "Company-operated": {
       "growth_pct": 27.7,
       "revenue": 3276.6
      },
      "Franchise / other": {
       "growth_pct": 9.5,
       "revenue": 170.9
      }
     },
     "revenue": 3447.5,
     "revenue_growth_pct": 26.66,
     "operating_margin_pct": 17.0,
     "operating_income": 586.1,
     "pretax": 517.1,
     "tax": 82.7,
     "net_income": 434.3,
     "shares_diluted": 187.7,
     "eps": 2.314
    }
   ]
  }
 }
}
```

*Model figures; verify against primary sources. No buy/sell call.*
