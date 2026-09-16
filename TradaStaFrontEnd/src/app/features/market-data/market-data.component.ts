import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MarketPriceResponse, TechnicalAnalysisResponse, RiskDecisionResponse } from '../../core/models/trading.models';

@Component({
  selector: 'app-market-data',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './market-data.component.html',
  styleUrl: './market-data.component.scss',
})
export class MarketDataComponent {
  @Input() symbol = 'BTCUSDT';
  @Input() timeframe = '1h';
  @Input() price: MarketPriceResponse | null = null;
  @Input() analysis: TechnicalAnalysisResponse | null = null;
  @Input() risk: RiskDecisionResponse | null = null;

  get marketCards() {
    const trend = (this.analysis?.trend ?? 'NEUTRAL').toUpperCase();
    const tone = trend === 'BULLISH' ? 'up' : trend === 'BEARISH' ? 'down' : 'neutral';
    const price = this.price?.price ? this.formatPrice(this.price.price) : 'N/A';
    const volume = this.analysis?.indicators?.volume ? `${this.analysis.indicators.volume.current_volume}` : '$0';

    return [
      { label: 'Current Price', value: price, tone },
      { label: 'Trend', value: trend, tone },
      { label: 'Volume', value: volume, tone: 'neutral' },
      { label: 'Risk Status', value: this.risk?.approved ? 'APPROVED' : 'REVIEW', tone: this.risk?.approved ? 'up' : 'neutral' },
    ];
  }

  get marketRows() {
    const priceValue = this.price?.price ? this.formatPrice(this.price.price) : 'N/A';
    const signal = (this.analysis?.trend ?? 'NEUTRAL').toUpperCase();

    return [{ pair: `${this.symbol}/USD`, price: priceValue, change: this.risk?.risk_reward_ratio ?? '—', signal }];
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
