import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { KnowledgeContextResponse, KnowledgeSearchResponse } from '../models/trading.models';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root',
})
export class KnowledgeService {
  private readonly api = inject(ApiService);

  searchKnowledge(query: string, topK = 5): Observable<KnowledgeSearchResponse> {
    const payload = {
      query,
      top_k: topK,
      minimum_score: 0,
    };

    return this.api.post<typeof payload, KnowledgeSearchResponse>('/api/v1/knowledge/search', payload);
  }

  buildKnowledgeContext(query: string, topK = 5): Observable<KnowledgeContextResponse> {
    return this.api.get<KnowledgeContextResponse>('/api/v1/knowledge/context', {
      query,
      top_k: topK,
    });
  }
}
