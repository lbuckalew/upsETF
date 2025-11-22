export interface Holding {
    ticker: string;
    description: string;
    weight: number;
}

export interface Sector {
    sector: string;
    weight: number;
}

export interface Etf {
  ticker: string;
  last_fetched: string;
  net_assets: number;
  net_expense_ratio: number;
  portfolio_turnover: number;
  dividend_yield: number;
  inception_date: string;
  leveraged: string;
  sectors: Sector[];
  holdings: Holding[];
}