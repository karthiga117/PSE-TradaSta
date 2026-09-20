import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { ContextRetrievalResponse } from '../../core/models/trading.models';

@Component({
  selector: 'app-knowledge-base',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './knowledge-base.component.html',
  styleUrl: './knowledge-base.component.scss',
})
export class KnowledgeBaseComponent {
  @Input() symbol = 'BTCUSDT';
  @Input() timeframe = '1h';
  @Input() knowledge: ContextRetrievalResponse | null = null;

  get articles() {
    const documents = this.knowledge?.documents ?? [
      { title: 'Moving Average: Complete Guide', score: 0.92, summary: 'How moving averages are used to identify momentum and trend continuity in crypto markets.' },
      { title: 'EMA vs SMA: What matters most?', score: 0.88, summary: 'A quick comparison of slow and fast moving averages for trade selection and risk timing.' },
      { title: 'Momentum interpretation in crypto', score: 0.81, summary: 'Understanding volume, volatility, and structure during trend expansion and retracement phases.' },
    ];

    return documents.map((doc) => ({
      title: doc.title,
      score: doc.score.toFixed(2),
      body: doc.summary,
    }));
  }
}
