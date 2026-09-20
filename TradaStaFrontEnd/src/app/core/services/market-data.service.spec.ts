import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { MarketDataService } from './market-data.service';

describe('MarketDataService', () => {
  let service: MarketDataService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    });

    service = TestBed.inject(MarketDataService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should request the backend price endpoint using the supported symbol format', () => {
    service.getPrice('BTCUSDT').subscribe((response) => {
      expect(response.symbol).toBe('BTC');
    });

    const request = httpMock.expectOne('http://localhost:8000/api/v1/market-data/BTC/price');
    expect(request.request.method).toBe('GET');
    request.flush({ symbol: 'BTC', price: '65000', currency: 'USD', timestamp: new Date().toISOString() });
  });
});
