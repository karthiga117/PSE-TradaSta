import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MarketPriceResponse, RiskDecisionResponse, TechnicalAnalysisResponse } from '../../core/models/trading.models';

@Component({
  selector: 'app-trading-signals',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './trading-signals.component.html',
  styleUrl: './trading-signals.component.scss',
})
export class TradingSignalsComponent {
  @Input() symbol = 'BTCUSDT';
  @Input() timeframe = '1h';
  @Input() price: MarketPriceResponse | null = null;
  @Input() analysis: TechnicalAnalysisResponse | null = null;
  @Input() risk: RiskDecisionResponse | null = null;

  get signalCards() {
    const trend = (this.analysis?.trend ?? 'NEUTRAL').toUpperCase();
    const tone = trend === 'BULLISH' ? 'buy' : trend === 'BEARISH' ? 'sell' : 'neutral';
    const entry = this.price?.price ? this.formatPrice(this.price.price) : 'N/A';
    const stop = this.risk ? (this.risk.approved ? `$${this.risk.position_size ?? 'N/A'}` : 'N/A') : 'N/A';

    return [
      { title: 'Current Signal', value: trend, tone },
      { title: 'Confidence', value: this.getConfidence(trend), tone: 'neutral' },
      { title: 'Entry', value: entry, tone: 'buy' },
      { title: 'Stop', value: stop, tone: 'sell' },
    ];
  }

  get history() {
    const trend = (this.analysis?.trend ?? 'NEUTRAL').toUpperCase();
    return [
      { time: 'Now', symbol: this.symbol, signal: trend, confidence: this.getConfidence(trend) },
      { time: 'Previous', symbol: this.symbol, signal: 'Hold', confidence: '53%' },
      { time: 'Earlier', symbol: this.symbol, signal: trend === 'BULLISH' ? 'Buy' : 'Sell', confidence: '71%' },
    ];
  }

  private getConfidence(trend: string): string {
    if (trend === 'BULLISH') return '76%';
    if (trend === 'BEARISH') return '68%';
    return '54%';
  }

  private formatPrice(value: string | number): string {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return 'N/A';
    }

    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(numeric);
  }
}
