import {
  Component,
  ElementRef,
  ViewChild,
  AfterViewInit,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import * as UpSetJS from '@upsetjs/bundle';
import { AlphavantageService } from '../alphavantage/alphavantage.service';



@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements AfterViewInit {
  @ViewChild('plotContainer', { static: true })
  plotContainer!: ElementRef<HTMLDivElement>;

  isDark = true;
  hasPlot = false;

  etfs: string[] = [''];
  selectedEtfIndex: number | null = 0;

  @ViewChild('etfCard') etfCard!: ElementRef<HTMLElement>;
  @ViewChild('logCard') logCard!: ElementRef<HTMLElement>;

  logCardHeight: number | null = null;

  private etfResizeObserver?: ResizeObserver;

  logs: string[] = [];

  showApiModal = false;
  apiKeyInput = '';

  constructor(private AlphavantageService: AlphavantageService) {}

  ngAfterViewInit(): void {
    this.setupEtfResizeObserver();
    this.syncLogCardHeight();
    }

    private setupEtfResizeObserver(): void {
    if (typeof ResizeObserver !== 'undefined' && this.etfCard) {
        this.etfResizeObserver = new ResizeObserver(() => {
        this.syncLogCardHeight();
        });
        this.etfResizeObserver.observe(this.etfCard.nativeElement);
    } else {
        // Fallback: just sync once
        setTimeout(() => this.syncLogCardHeight());
    }
    }

    private syncLogCardHeight(): void {
    if (!this.etfCard || !this.logCard) {
        return;
    }

    const etfHeight = this.etfCard.nativeElement.offsetHeight;
    if (etfHeight && etfHeight > 0) {
        this.logCardHeight = etfHeight;
    }
    }

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

  onPlotOverlap(): void {
    this.log('Plot Overlap clicked – rendering dummy 3-way intersection.');

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

  // ---- ETF inputs ----
  addEtfField(): void {
    if (this.etfs.length < 5) {
      this.etfs.push('');
      this.selectedEtfIndex = this.etfs.length - 1;
      setTimeout(() => this.syncLogCardHeight());
    }
  }

  onEtfFocus(index: number): void {
    this.selectedEtfIndex = index;
  }

  // ---- Logging ----
  log(msg: string): void {
    const ts = new Date().toLocaleTimeString();
    this.logs.unshift(`[${ts}] ${msg}`);
    setTimeout(() => this.syncLogCardHeight());
  }
}
