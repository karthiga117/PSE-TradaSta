import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { RiskDecisionResponse, RiskEvaluationRequest } from '../models/trading.models';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root',
})
export class RiskManagementService {
  private readonly api = inject(ApiService);

  evaluate(request: RiskEvaluationRequest): Observable<RiskDecisionResponse> {
    return this.api.post<RiskEvaluationRequest, RiskDecisionResponse>('/api/v1/risk/evaluate', request);
  }
}
