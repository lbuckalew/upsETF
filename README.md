# upsETF
Visualizing weighted ETF overlap with an upset plot.

upsETF takes into account the weight any holding has a given ETF. For example, if ETF1 has a 7% allocation in `META', ETF2 has a 14% allocation in `META`, and ETF3 has a 20% allocation in `META` then they only overlap by the minimum of the two values (7%). The overlap is calculated using the distinct mode such that the shared 7% between all three is shown in the three-way intersection set, the overlap between ETF2 and ETF3 shows the remaining 7% overlap, and the remaining 6% overlap is shown in the lone ETF3 intersection.

## Thanks chatGPT
GUI by chatgpt to make the interface call dummy functions. ETF weight overlap written by me.

## Alpha Vantage API
Get your AlphaVantage API key [here](https://www.alphavantage.co/support/#api-key). You are limited to 25 calls per day (each unique ETF you want to compare is one call). To help with this, upsETF caches each ETF API call.

## Test data
Test data with simple allocations are included in the data folder as if it were cached. The tickers for the fake ETFs are `ABX`, `ABY`, and `ABZ`.

```json
{
  "net_assets": "385800000000",
  "net_expense_ratio": "0.002",
  "portfolio_turnover": "0.08",
  "dividend_yield": "0.0046",
  "inception_date": "1999-03-10",
  "leveraged": "NO",
  "holdings": [
    {
      "symbol": "NVDA",
      "description": "NVIDIA CORP",
      "weight": "0.2"
    },
    {
      "symbol": "BAR",
      "description": "BAR",
      "weight": "0.6"
    },
    {
      "symbol": "BAZ",
      "description": "BAZ",
      "weight": "0.2"
    }
  ],
  "ticker": "ABX",
  "fetched_at": "2025-11-07T19:47:19.687683"
}
```

<img src="img/example.png" alt="Example" width="800"/>