import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MarketPriceResponse, TechnicalAnalysisResponse } from '../../core/models/trading.models';

@Component({
  selector: 'app-technical-analysis',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './technical-analysis.component.html',
  styleUrl: './technical-analysis.component.scss',
})
export class TechnicalAnalysisComponent {
  @Input() symbol = 'BTCUSDT';
  @Input() timeframe = '1h';
  @Input() price: MarketPriceResponse | null = null;
  @Input() analysis: TechnicalAnalysisResponse | null = null;

  get indicators() {
    const indicators = this.analysis?.indicators ?? {};
    const trend = (this.analysis?.trend ?? 'NEUTRAL').toUpperCase();

    return [
      {
        name: 'RSI (14)',
        value: indicators.rsi?.value ?? 'N/A',
        signal: this.getSignalLabel(Number(indicators.rsi?.value ?? 50), 'rsi'),
      },
      {
        name: 'MACD',
        value: indicators.macd?.macd ?? 'N/A',
        signal: Number(indicators.macd?.macd ?? 0) >= 0 ? 'Bullish' : 'Bearish',
      },
      {
        name: 'EMA (20)',
        value: indicators.ema?.value ?? 'N/A',
        signal: trend === 'BULLISH' ? 'Bullish' : trend === 'BEARISH' ? 'Bearish' : 'Neutral',
      },
      {
        name: 'SMA (200)',
        value: indicators.sma?.value ?? 'N/A',
        signal: trend === 'BULLISH' ? 'Bullish' : trend === 'BEARISH' ? 'Bearish' : 'Neutral',
      },
    ];
  }

  get summary() {
    const trend = (this.analysis?.trend ?? 'NEUTRAL').toUpperCase();
    return [
      { label: 'Trend Bias', value: trend },
      { label: 'Momentum', value: trend === 'BULLISH' ? 'Strong' : trend === 'BEARISH' ? 'Weak' : 'Balanced' },
      { label: 'Symbol', value: this.symbol },
      { label: 'Timeframe', value: this.timeframe },
    ];
  }

  private getSignalLabel(value: number, field: 'rsi'): string {
    if (field === 'rsi') {
      if (value > 70) return 'Overbought';
      if (value < 30) return 'Oversold';
      return 'Neutral';
    }

    return 'Neutral';
  }
}
