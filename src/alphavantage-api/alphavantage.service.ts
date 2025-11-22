import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { Holding, Sector, Etf} from '../app/etf.interface'
import {genericApiInfo, apiResponseInfo, GenericApi} from '../api-base/api-base.interface'

interface AlphavantageEtfResponse {
  net_assets: string;
  net_expense_ratio: string;
  portfolio_turnover: string;
  dividend_yield: string;
  inception_date: string;
  leveraged: string;
  sectors: Sector[];
  holdings: Holding[];
}

export class AlphavantageApi extends GenericApi {
  info: genericApiInfo = {
    apiName: 'Alphavantage',
    baseUrl: 'https://www.alphavantage.co/',
    etfInfoEndpoint: 'query?function=ETF_PROFILE',
    apiKey: 'demo'
  };

  constructor (private http: HttpClient) {
    super();
  }

  responseToEtf(input: AlphavantageEtfResponse): Etf {
    let etf : Etf;
    etf.net_assets = Number(input.net_assets);
    etf.net_expense_ratio = Number(input.net_expense_ratio);
    etf.portfolio_turnover = Number(input.portfolio_turnover);
    etf.dividend_yield = Number(input.dividend_yield);
    etf.inception_date = input.inception_date;
    etf.leveraged = input.leveraged;
    etf.sectors = [];
    etf.holdings = [];

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

  getEtfInfo(ticker: string): Observable<[apiResponseInfo, Etf]> {
    ticker = ticker.toUpperCase();

    const params: HttpParams = new HttpParams();
    params.set('symbol', ticker);
    params.set('apikey', this.info.apiKey);

    return this.http.post<AlphavantageEtfResponse>(this.info.baseUrl, {params: params}).pipe(
      map(resp => {
        console.log('Updated response');
        let etf: Etf = this.responseToEtf(resp);
        etf.ticker = ticker;
        etf.last_fetched = new Date().toISOString();

        const responseInfo: apiResponseInfo = {
          usedCache: false,
          usedDemoKey: false,
          httpResult: '200'
        };
        return [responseInfo, etf];
      })
    );
  }
}