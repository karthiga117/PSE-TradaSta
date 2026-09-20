import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { SignalRequestPayload, SignalResponse } from '../models/trading.models';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root',
})
export class TradingSignalService {
  private readonly api = inject(ApiService);

  generateSignal(request: SignalRequestPayload): Observable<SignalResponse> {
    return this.api.post<SignalRequestPayload, SignalResponse>('/api/v1/signals', request);
  }
}
