import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MarketPriceResponse, RiskDecisionResponse, TechnicalAnalysisResponse } from '../../core/models/trading.models';

@Component({
  selector: 'app-risk-management',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './risk-management.component.html',
  styleUrl: './risk-management.component.scss',
})
export class RiskManagementComponent {
  @Input() symbol = 'BTCUSDT';
  @Input() timeframe = '1h';
  @Input() price: MarketPriceResponse | null = null;
  @Input() analysis: TechnicalAnalysisResponse | null = null;
  @Input() risk: RiskDecisionResponse | null = null;

  get metrics() {
    return [
      { label: 'Risk / Reward', value: this.risk?.risk_reward_ratio ?? 'N/A', tone: 'good' },
      { label: 'Position Size', value: this.risk?.position_size ?? 'N/A', tone: 'neutral' },
      { label: 'Max Drawdown', value: this.risk?.warnings?.length ? 'Watch' : 'Low', tone: 'warning' },
      { label: 'Exposure', value: this.risk?.portfolio_exposure ?? 'N/A', tone: this.risk?.approved ? 'good' : 'warning' },
    ];
  }

  get checks() {
    return [
      `${this.symbol} risk per trade within limits`,
      'Position sizing aligns with portfolio risk',
      this.risk?.approved ? 'Stop loss is configured' : 'Risk evaluation requires review',
      'Diversification has not been exceeded',
    ];
  }

  get tradeParameters() {
    return [
      { label: 'Entry Price', value: this.price?.price ? this.formatPrice(this.price.price) : 'N/A' },
      { label: 'Stop Loss', value: 'N/A' },
      { label: 'Take Profit', value: 'N/A' },
      { label: 'Max Loss', value: this.risk?.risk_amount ?? 'N/A' },
    ];
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
