// import { Injectable } from '@angular/core';
// import { EtfPayload } from '../alphavantage-api/alphavantage.service';

// export interface Intersection {
//     symbol: string;
//     etfs: Holding[];
// }

// @Injectable({
//   providedIn: 'root',
// })
// export class IntersectionService {
//     constructor() {}

//     map: Intersection[] = [];

//     calculateIntersections(etfs: EtfPayload[]): Intersection[] {

//         for (const e of etfs) {
//             for (const h of e.data.holdings) {
//                 const symbol = h.symbol;
//                 let i = this.map.find(entry => entry.symbol === symbol);
//                 if (i) {
//                     i.etfs.push(h)
//                 }
//             }
//         }
//         return this.map;
//     }
// }