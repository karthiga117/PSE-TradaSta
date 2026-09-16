import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { catchError, finalize, forkJoin, map, of, switchMap } from 'rxjs';

import {
  ContextRetrievalRequest,
  ContextRetrievalResponse,
  DashboardState,
  HealthResponse,
  RiskEvaluationRequest,
} from '../../core/models/trading.models';
import { ApiService } from '../../core/services/api.service';
import { MarketDataService } from '../../core/services/market-data.service';
import { RiskManagementService } from '../../core/services/risk-management.service';
import { TechnicalAnalysisService } from '../../core/services/technical-analysis.service';
import { AiExplanationComponent } from '../ai-explanation/ai-explanation.component';
import { KnowledgeBaseComponent } from '../knowledge-base/knowledge-base.component';
import { MarketDataComponent } from '../market-data/market-data.component';
import { RiskManagementComponent } from '../risk-management/risk-management.component';
import { TechnicalAnalysisComponent } from '../technical-analysis/technical-analysis.component';
import { TradingSignalsComponent } from '../trading-signals/trading-signals.component';

type BackendStatus = 'CHECKING' | 'CONNECTED' | 'DISCONNECTED';
type ViewMode = 'dashboard' | 'market-data' | 'technical-analysis' | 'trading-signals' | 'risk-management' | 'ai-explanation' | 'knowledge-base';

type SessionSignal = {
  symbol: string;
  timeframe: string;
  direction: string;
  strategy: string;
  time: string;
};

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MarketDataComponent,
    TechnicalAnalysisComponent,
    TradingSignalsComponent,
    RiskManagementComponent,
    AiExplanationComponent,
    KnowledgeBaseComponent,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  readonly symbolControl = new FormControl('BTCUSDT');
  readonly timeframeControl = new FormControl('1h');

  readonly state = signal<DashboardState>({
    price: null,
    ohlcv: null,
    analysis: null,
    signal: null,
    risk: null,
    explanation: null,
    knowledge: null,
  });

  readonly isLoading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly backendStatus = signal<BackendStatus>('CHECKING');
  readonly recentSignals = signal<SessionSignal[]>([]);
  readonly selectedView = signal<ViewMode>('dashboard');

  readonly chartPath = computed(() => this.buildChartPath());
  readonly technicalIndicators = computed(() => {
    const analysis = this.state().analysis;
    if (!analysis) {
      return [];
    }

    const indicators = analysis.indicators;
    return [
      {
        label: 'RSI (14)',
        value: indicators.rsi ? indicators.rsi.value : 'N/A',
        direction: indicators.rsi ? 'Neutral' : 'N/A',
        directionClass: 'neutral',
      },
      {
        label: 'MACD',
        value: indicators.macd ? indicators.macd.macd : 'N/A',
        direction: indicators.macd ? (Number(indicators.macd.macd) >= 0 ? 'Bullish' : 'Bearish') : 'N/A',
        directionClass: Number(indicators.macd?.macd ?? 0) >= 0 ? 'bullish' : 'bearish',
      },
      {
        label: 'EMA (20)',
        value: indicators.ema ? indicators.ema.value : 'N/A',
        direction: indicators.ema ? 'Trend-based' : 'N/A',
        directionClass: 'bullish',
      },
      {
        label: 'SMA (200)',
        value: indicators.sma ? indicators.sma.value : 'N/A',
        direction: indicators.sma ? (analysis.trend === 'BULLISH' ? 'Bullish' : analysis.trend === 'BEARISH' ? 'Bearish' : 'Neutral') : 'N/A',
        directionClass: analysis.trend === 'BULLISH' ? 'bullish' : analysis.trend === 'BEARISH' ? 'bearish' : 'neutral',
      },
      {
        label: 'ATR (14)',
        value: indicators.atr ? indicators.atr.value : 'N/A',
        direction: 'N/A',
        directionClass: 'muted',
      },
    ];
  });

  private readonly api = inject(ApiService);
  private readonly marketDataService = inject(MarketDataService);
  private readonly technicalAnalysisService = inject(TechnicalAnalysisService);
  private readonly riskManagementService = inject(RiskManagementService);

  ngOnInit(): void {
    this.checkBackend();
    this.loadDashboard();
  }

  selectView(view: ViewMode): void {
    this.selectedView.set(view);
  }

  applySelection(): void {
    const normalizedSymbol = (this.symbolControl.value ?? '').trim().toUpperCase();
    if (!normalizedSymbol) {
      return;
    }

    this.symbolControl.setValue(normalizedSymbol, { emitEvent: false });
    this.refresh();
  }

  selectTimeframe(value: string): void {
    this.timeframeControl.setValue(value, { emitEvent: false });
    this.refresh();
  }

  refresh(): void {
    this.checkBackend();
    this.loadDashboard();
  }

  formatPrice(value: string | number | null | undefined): string {
    if (value === null || value === undefined || value === '') {
      return 'N/A';
    }

    const numericValue = Number(value);
    if (Number.isNaN(numericValue)) {
      return String(value);
    }

    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(numericValue);
  }

  displayedSymbol(): string {
    return (this.symbolControl.value ?? 'BTCUSDT').trim().toUpperCase() || 'BTCUSDT';
  }

  primaryTrend(): string {
    const trend = this.state().analysis?.trend;
    return trend ? trend.toUpperCase() : 'N/A';
  }

  primaryStrategy(): string {
    return this.state().analysis?.strategies[0]?.strategy_name ?? 'technical_analysis';
  }

  currentPriceValue(): string {
    const price = this.state().price?.price;
    return price === null || price === undefined || price === '' ? 'Loading...' : this.formatPrice(price);
  }

  riskStatusText(): string {
    const risk = this.state().risk;
    if (!risk) {
      return 'Awaiting risk evaluation';
    }
    return risk.approved ? 'APPROVED' : 'REJECTED';
  }

  signalToneClass(): string {
    const trend = this.primaryTrend();
    if (trend === 'BULLISH') {
      return 'buy';
    }
    if (trend === 'BEARISH') {
      return 'sell';
    }
    return 'hold';
  }

  private checkBackend(): void {
    this.backendStatus.set('CHECKING');
    this.api.get<HealthResponse>('/api/v1/health').subscribe({
      next: () => this.backendStatus.set('CONNECTED'),
      error: () => this.backendStatus.set('DISCONNECTED'),
    });
  }

  private loadDashboard(): void {
    const rawSymbol = (this.symbolControl.value ?? 'BTCUSDT').trim().toUpperCase();
    const symbol = rawSymbol || 'BTCUSDT';
    const timeframe = this.timeframeControl.value ?? '1h';

    this.isLoading.set(true);
    this.errorMessage.set(null);

    forkJoin({
      price: this.marketDataService.getPrice(symbol),
      ohlcv: this.marketDataService.getOhlcv(symbol, timeframe, 24),
      analysis: this.technicalAnalysisService.getAnalysis(symbol, timeframe, 200),
    })
      .pipe(
        switchMap(({ price, ohlcv, analysis }) => {
          const entryPrice = Number(price.price) || 0;
          const trend = (analysis.trend ?? 'NEUTRAL').toUpperCase();
          const isShort = trend === 'BEARISH';

          const riskRequest: RiskEvaluationRequest = {
            symbol: symbol.replace(/USDT$/i, ''),
            side: isShort ? 'SHORT' : 'LONG',
            entry_price: entryPrice,
            stop_loss: entryPrice ? (isShort ? entryPrice * 1.03 : entryPrice * 0.97) : null,
            take_profit: entryPrice ? (isShort ? entryPrice * 0.92 : entryPrice * 1.08) : null,
            account_equity: 10000,
            current_exposure: 2000,
            daily_loss: 100,
            peak_equity: 10000,
            current_equity: 9800,
            open_positions: 2,
          };

          const contextRequest: ContextRetrievalRequest = {
            symbol,
            timeframe,
            trend: trend as 'BULLISH' | 'BEARISH' | 'NEUTRAL',
            risk_profile: 'balanced',
            intent: 'evaluate_trade',
            query: `${symbol} ${trend.toLowerCase()} trading context and risk-adjusted market regime`,
            limit: 3,
          };

          return this.riskManagementService.evaluate(riskRequest).pipe(
            switchMap((risk) =>
              this.api
                .post<ContextRetrievalRequest, ContextRetrievalResponse>(
                  '/api/v1/context/retrieve',
                  contextRequest,
                )
                .pipe(
                  catchError(() => of(null)),
                  map((knowledge) => ({ price, ohlcv, analysis, risk, knowledge })),
                ),
            ),
          );
        }),
        finalize(() => this.isLoading.set(false)),
      )
      .subscribe({
        next: ({ price, ohlcv, analysis, risk, knowledge }) => {
          this.state.set({
            price,
            ohlcv,
            analysis,
            signal: null,
            risk,
            explanation: null,
            knowledge: knowledge ?? null,
          });

          this.recentSignals.set([
            {
              symbol,
              timeframe,
              direction: analysis.trend,
              strategy: this.primaryStrategy(),
              time: 'just now',
            },
          ]);
        },
        error: (error: HttpErrorResponse) => {
          const message = error?.error?.detail ?? error?.message ?? 'Unable to load dashboard data';
          this.errorMessage.set(message);
          this.state.set({
            price: null,
            ohlcv: null,
            analysis: null,
            signal: null,
            risk: null,
            explanation: null,
            knowledge: null,
          });
          this.recentSignals.set([]);
        },
      });
  }

  private buildChartPath(): string {
    const candles = this.state().ohlcv?.candles ?? [];
    if (candles.length === 0) {
      return '';
    }

    const closes = candles.map((entry) => Number(entry.close));
    const minValue = Math.min(...closes);
    const maxValue = Math.max(...closes);
    const range = maxValue - minValue || 1;

    return candles
      .map((entry, index) => {
        const x = 32 + (index * 700) / (candles.length - 1 || 1);
        const normalized = (Number(entry.close) - minValue) / range;
        const y = 210 - normalized * 160;
        return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
      })
      .join(' ');
  }
}
