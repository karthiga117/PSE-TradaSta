import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { finalize, forkJoin, map, of, switchMap } from 'rxjs';

import { AiExplanationResponse, DashboardState, RiskEvaluationRequest, SignalRequestPayload } from '../../core/models/trading.models';
import { AiExplanationService } from '../../core/services/ai-explanation.service';
import { KnowledgeService } from '../../core/services/knowledge.service';
import { MarketDataService } from '../../core/services/market-data.service';
import { RiskManagementService } from '../../core/services/risk-management.service';
import { TechnicalAnalysisService } from '../../core/services/technical-analysis.service';
import { TradingSignalService } from '../../core/services/trading-signal.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
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

  private readonly marketDataService = inject(MarketDataService);
  private readonly technicalAnalysisService = inject(TechnicalAnalysisService);
  private readonly tradingSignalService = inject(TradingSignalService);
  private readonly riskManagementService = inject(RiskManagementService);
  private readonly aiExplanationService = inject(AiExplanationService);
  private readonly knowledgeService = inject(KnowledgeService);

  ngOnInit(): void {
    this.loadDashboard();
  }

  refresh(): void {
    this.loadDashboard();
  }

  private loadDashboard(): void {
    const symbol = (this.symbolControl.value ?? 'BTCUSDT').trim();
    const timeframe = this.timeframeControl.value ?? '1h';

    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.marketDataService.getPrice(symbol)
      .pipe(
        switchMap((price) =>
          forkJoin({
            price: of(price),
            ohlcv: this.marketDataService.getOhlcv(symbol, timeframe, 24),
            analysis: this.technicalAnalysisService.getAnalysis(symbol, timeframe, 200),
          }),
        ),
        switchMap(({ price, ohlcv, analysis }) => {
          const signalRequest: SignalRequestPayload = {
            symbol,
            timeframe,
            strategy: analysis.strategies[0]?.strategy_name ?? 'moving_average_trend',
            account_equity: 10000,
            current_exposure: 2000,
            daily_loss: 100,
            peak_equity: 10000,
            current_equity: 9800,
            open_positions: 2,
          };

          return this.tradingSignalService.generateSignal(signalRequest).pipe(
            switchMap((signal) => {
              const riskRequest: RiskEvaluationRequest = {
                symbol,
                side: signal.signal === 'SELL' ? 'SHORT' : 'LONG',
                entry_price: signal.entry ?? price.price,
                stop_loss: signal.stop_loss ?? null,
                take_profit: signal.take_profit ?? null,
                account_equity: 10000,
                current_exposure: 2000,
                daily_loss: 100,
                peak_equity: 10000,
                current_equity: 9800,
                open_positions: 2,
              };

              return this.riskManagementService.evaluate(riskRequest).pipe(
                switchMap((risk) =>
                  this.aiExplanationService.explainSignal(signal, symbol, timeframe).pipe(
                    map((explanation: AiExplanationResponse) => ({
                      price,
                      ohlcv,
                      analysis,
                      signal,
                      risk,
                      explanation,
                    })),
                  ),
                ),
              );
            }),
          );
        }),
        switchMap(({ price, ohlcv, analysis, signal, risk, explanation }) =>
          this.knowledgeService.searchKnowledge(`${symbol} ${timeframe} ${signal.strategy} ${signal.signal}`, 5).pipe(
            map((knowledge) => ({
              price,
              ohlcv,
              analysis,
              signal,
              risk,
              explanation,
              knowledge,
            })),
          ),
        ),
        finalize(() => this.isLoading.set(false)),
      )
      .subscribe({
        next: (payload) => this.state.set(payload),
        error: (error: Error) => this.errorMessage.set(error.message),
      });
  }
}
