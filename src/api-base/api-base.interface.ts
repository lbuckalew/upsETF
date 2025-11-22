import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Etf } from '../app/etf.interface'

export interface genericApiInfo {
  apiName: string;
  baseUrl: string | null;
  etfInfoEndpoint: string | null;
  apiKey: string | null;
}

export interface apiResponseInfo {
  usedCache: boolean;
  usedDemoKey: boolean;
  httpResult: string;
}

@Injectable({
  providedIn: 'root',
})
export abstract class GenericApi {
  info: genericApiInfo;

  constructor() {}

  getCachedApiKey(): string {
    return 'foo';
  }

  abstract responseToEtf(input: any): Etf;
  abstract getEtfInfo(ticker: string): Observable<[apiResponseInfo, any]>;
}