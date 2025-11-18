import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class AlphavantageService {
  private apiUrl = '/api-key';

  constructor(private http: HttpClient) {}

  saveApiKey(key: string): Observable<any> {
    return this.http.post(this.apiUrl, { apiKey: key });
  }
}
