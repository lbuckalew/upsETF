import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Holding, Sector, Etf} from '../intersections/intersections.service'

export interface AlphavantageEtfPayload {
  net_assets: string;
  net_expense_ratio: string;
  portfolio_turnover: string;
  dividend_yield: string;
  inception_date: string;
  leveraged: string;
  sectors: Sector[];
  holdings: Holding[];
}

export interface EtfPayload {
  ticker: string;
  last_fetched: string;
  data: AlphavantageEtfPayload;
}

export interface EtfResponse {
  source: 'cache' | 'api';
  usedDemoKey: boolean;
  payload: EtfPayload;
}

function castAsEtf(input : AlphavantageEtfPayload) : Etf {
  const etf : Etf = {
    net_assets: Number(input.net_assets),
    net_expense_ratio: Number(input.net_expense_ratio),
    portfolio_turnover: Number(input.portfolio_turnover),
    dividend_yield: Number(input.dividend_yield),
    inception_date: input.inception_date,
    leveraged: input.leveraged,
    sectors: [],
    holdings: []
  };

  for (const s of input.sectors) {
    let cleanSector : Sector = {
      sector: s.sector,
      weight: Number(s.weight)
    };
    etf.sectors.push(cleanSector);
  }

  for (const h of input.holdings) {
    let cleanHolding : Holding = {
      ticker: h.ticker,
      description: h.description,
      weight: Number(h.weight)
    };
    etf.holdings.push(cleanHolding);
  }

  return etf;
}

@Injectable({
  providedIn: 'root',
})
export class AlphavantageService {
  private readonly apiUrl = '/api-key';
  private readonly etfUrl = '/etf';

  constructor(private http: HttpClient) {}

  saveApiKey(key: string): Observable<any> {
    return this.http.post(this.apiUrl, { apiKey: key });
  }

  getEtfHoldings(ticker: string): Observable<EtfResponse> {
    const symbol = ticker.trim().toUpperCase();
    return this.http.get<EtfResponse>(`${this.etfUrl}/${symbol}`);
  }
}
