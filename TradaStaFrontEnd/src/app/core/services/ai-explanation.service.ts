import { Injectable, inject } from '@angular/core';
import { Observable, map, of } from 'rxjs';

import { AiExplanationResponse, KnowledgeContextResponse, SignalResponse } from '../models/trading.models';
import { KnowledgeService } from './knowledge.service';

@Injectable({
  providedIn: 'root',
})
export class AiExplanationService {
  private readonly knowledgeService = inject(KnowledgeService);

  explainSignal(signal: SignalResponse, symbol: string, timeframe: string): Observable<AiExplanationResponse> {
    const query = `${symbol} ${timeframe} ${signal.strategy} ${signal.signal} trading context`;

    return this.knowledgeService.buildKnowledgeContext(query, 5).pipe(
      map((context: KnowledgeContextResponse) => ({
        signal: signal.signal,
        confidence: signal.confidence,
        explanation: `${signal.reasoning} The backend evaluated the ${symbol} setup using the ${signal.strategy} rule set and the current ${timeframe} context before generating the recommendation.`,
        keyFactors: [
          `Strategy: ${signal.strategy}`,
          `Signal: ${signal.signal}`,
          `Confidence: ${signal.confidence}%`,
          `Risk reward: ${signal.risk_reward_ratio ?? 'n/a'}`,
        ],
        risks: [
          signal.stop_loss ? `Stop loss ${signal.stop_loss}` : 'Stop loss not available',
          signal.take_profit ? `Take profit ${signal.take_profit}` : 'Take profit not available',
          'Risk checks remain mandatory before execution',
        ],
        entry: signal.entry,
        stopLoss: signal.stop_loss,
        takeProfit: signal.take_profit,
        riskReward: signal.risk_reward,
        riskRewardRatio: signal.risk_reward_ratio,
        knowledgeSources: context.sources ?? [],
      })),
    );
  }
}
