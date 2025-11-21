import { Injectable } from '@angular/core';
import { EtfPayload } from '../alphavantage/alphavantage.service';

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
  net_assets: number;
  net_expense_ratio: number;
  portfolio_turnover: number;
  dividend_yield: number;
  inception_date: string;
  leveraged: string;
  sectors: Sector[];
  holdings: Holding[];
}

export interface Intersection {
    symbol: string;
    etfs: Holding[];
}

@Injectable({
  providedIn: 'root',
})
export class IntersectionService {
    constructor() {}

    map: Intersection[] = [];

    calculateIntersections(etfs: EtfPayload[]): Intersection[] {

        for (const e of etfs) {
            for (const h of e.data.holdings) {
                const symbol = h.symbol;
                let i = this.map.find(entry => entry.symbol === symbol);
                if (i) {
                    i.etfs.push(h)
                }
            }
        }
        return this.map;
    }
}