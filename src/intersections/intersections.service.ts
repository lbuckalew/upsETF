import { Injectable } from '@angular/core';
import { EtfPayload } from '../alphavantage/alphavantage.service';

interface Holding {
    ticker: string;
    description: string;
    weight: number;
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
                const exists = this.map.some(intersection => intersection.symbol === symbol);
            }
        }
        return this.map;
    }
}