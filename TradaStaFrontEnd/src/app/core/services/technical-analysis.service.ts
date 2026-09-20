import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { TechnicalAnalysisResponse } from '../models/trading.models';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root',
})
export class TechnicalAnalysisService {
  private readonly api = inject(ApiService);

  getAnalysis(symbol: string, timeframe = '1h', limit = 200): Observable<TechnicalAnalysisResponse> {
    const normalizedSymbol = this.normalizeSymbol(symbol);
    return this.api.get<TechnicalAnalysisResponse>(`/api/v1/analysis/${normalizedSymbol}`, {
      timeframe,
      limit,
    });
  }

  private normalizeSymbol(symbol: string): string {
    const cleaned = symbol.trim().toUpperCase().replace(/[-_]/g, '').replace(/USDT$/, '').replace(/USD$/, '');
    return cleaned || 'BTC';
  }
}
