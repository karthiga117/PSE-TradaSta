import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { ContextRetrievalResponse, MarketPriceResponse, RiskDecisionResponse, TechnicalAnalysisResponse } from '../../core/models/trading.models';

@Component({
  selector: 'app-ai-explanation',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ai-explanation.component.html',
  styleUrl: './ai-explanation.component.scss',
})
export class AiExplanationComponent {
  @Input() symbol = 'BTCUSDT';
  @Input() timeframe = '1h';
  @Input() price: MarketPriceResponse | null = null;
  @Input() analysis: TechnicalAnalysisResponse | null = null;
  @Input() risk: RiskDecisionResponse | null = null;
  @Input() knowledge: ContextRetrievalResponse | null = null;

  get keyPoints() {
    const trend = (this.analysis?.trend ?? 'NEUTRAL').toUpperCase();
    const entry = this.price?.price ?? 'N/A';
    const riskText = this.risk?.approved ? 'Risk remains controlled by the current policy gate.' : 'Risk is under review because the policy gate has not approved the trade.';

    return [
      `${this.symbol} is trading with a ${trend.toLowerCase()} bias on the ${this.timeframe} view.`,
      `Current price is ${entry}. The technical structure is consistent with the latest market regime.`,
      `${riskText} ${this.knowledge?.documents?.[0]?.title ?? 'Context is being retrieved for the active setup.'}`,
    ];
  }
}
