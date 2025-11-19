import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface AlphavantageEtfPayload {
  net_assets: string;
  net_expense_ration: string;
  portfolio_turnover: string;
  dividend_yield: string;
  inception_date: string;
  leveraged: string;
  sectors: string[];
  holdings: {symbol: string, description: string, weight: string}[];
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
