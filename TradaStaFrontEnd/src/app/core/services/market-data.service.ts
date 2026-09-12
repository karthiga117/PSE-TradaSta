import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { MarketPriceResponse, OhlcvResponse } from '../models/trading.models';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root',
})
export class MarketDataService {
  private readonly api = inject(ApiService);

  getPrice(symbol: string): Observable<MarketPriceResponse> {
    const normalizedSymbol = this.normalizeSymbol(symbol);
    return this.api.get<MarketPriceResponse>(`/api/v1/market-data/${normalizedSymbol}/price`);
  }

  getOhlcv(symbol: string, timeframe = '1h', limit = 24): Observable<OhlcvResponse> {
    const normalizedSymbol = this.normalizeSymbol(symbol);
    return this.api.get<OhlcvResponse>(`/api/v1/market-data/${normalizedSymbol}/ohlcv`, {
      timeframe,
      limit,
    });
  }

  private normalizeSymbol(symbol: string): string {
    const cleaned = symbol.trim().toUpperCase().replace(/[-_]/g, '').replace(/USDT$/, '').replace(/USD$/, '');
    return cleaned || 'BTC';
  }
}
