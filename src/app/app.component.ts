import {Component, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import * as UpSetJS from '@upsetjs/bundle';
import { AlphavantageService, EtfResponse } from '../alphavantage/alphavantage.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent {
  isDark = true;
  hasPlot = false;
  showApiModal = false;

  @ViewChild('etfCard') etfCard!: ElementRef<HTMLElement>;
  @ViewChild('logCard') logCard!: ElementRef<HTMLElement>;
  @ViewChild('plotContainer', { static: true })
  plotContainer!: ElementRef<HTMLDivElement>;

  logs: string[] = [];
  etf_inputs: string[] = [];
  etf_data: EtfResponse[] = [];
  selectedEtfIndex: number | null = 0;
  apiKeyInput = '';

  constructor(private AlphavantageService: AlphavantageService) {}

  // ---- Header actions ----
  openApiKeyModal(): void {
    this.showApiModal = true;
  }

  closeApiKeyModal(): void {
    this.showApiModal = false;
    this.apiKeyInput = '';
  }

  saveApiKey(): void {
    const trimmed = this.apiKeyInput.trim();
    if (!trimmed) {
      this.log('API key is empty. Not saving.');
      this.closeApiKeyModal();
      return;
    }

    this.AlphavantageService.saveApiKey(trimmed).subscribe({
      next: () => {
        this.log('API key saved to api-key.json.');
        this.closeApiKeyModal();
      },
      error: (err) => {
        console.error(err);
        this.log('Failed to save API key (see console for details).');
      },
    });
  }

  fetchEtfHoldings(ticker: string): void {
    const trimmed = ticker.trim();
    if (!trimmed) {
      this.log('Skipping empty ETF ticker.');
      return;
    }

    this.log(`Requesting holdings for ${trimmed}...`);

    this.AlphavantageService.getEtfHoldings(trimmed).subscribe({
      next: (resp: EtfResponse) => {
        const { source, usedDemoKey, payload } = resp;
        this.log(`[${source}] ${payload.ticker} last fetched on ${payload.last_fetched}`);

        if (usedDemoKey) {
          this.log(
            `No API key saved; using Alpha Vantage 'demo' key for ${payload.ticker}.`
          );
        }

        this.etf_data.push(resp);

        // TODO: later you can use payload.holdings to build the real UpSet plot
      },
      error: (err) => {
        console.error(err);
        this.log(`Error fetching holdings for ${trimmed}.`);
      },
    });
  }

  onPlotOverlap(): void {
    this.log(`ETF inputs: ${this.etf_inputs.toString()}`);

    if (this.etf_inputs.length < 2){
      this.log("[ERR] Must input at least 2 ETFs to compare.");
      return;
    }

    const sorted_tickers: string[] = this.etf_inputs;
    sorted_tickers.sort();
    this.log(sorted_tickers.toString());

    for (const ticker of this.etf_inputs){
      this.fetchEtfHoldings(ticker);
    }
  }

  plotOverlap(): void {
    const container = this.plotContainer?.nativeElement;
    if (!container) {
      this.log('Plot container not available.');
      return;
    }

    // ----- Dummy 3-way intersection example -----
    // Think of these as ETF holdings
    const data = [
      { name: 'ETF A', elems: ['NVDA', 'AAPL', 'MSFT', 'AMZN'] },
      { name: 'ETF B', elems: ['MSFT', 'AMZN', 'GOOGL', 'META'] },
      { name: 'ETF C', elems: ['AAPL', 'AMZN', 'TSLA', 'NFLX'] },
    ];

    const sets = UpSetJS.asSets(data);

    // Clear any previous plot
    container.innerHTML = '';

    const width = container.clientWidth || 600;
    const height = container.clientHeight || 320;

    const props: any = {
      sets,
      width,
      height,
      theme: this.isDark ? 'dark' : 'light',
    };

    UpSetJS.render(container, props);

    this.hasPlot = true;
  }

  toggleTheme(): void {
    this.isDark = !this.isDark;
    this.log(`Theme changed to ${this.isDark ? 'Dark' : 'Light'} mode.`);

    // Optional: re-render current plot with new theme
    if (this.hasPlot) {
      this.onPlotOverlap();
    }
  }

  // ---- Logging ----
  log(msg: string): void {
    const ts = new Date().toLocaleTimeString();
    this.logs.unshift(`[${ts}] ${msg}`);
  }
}
