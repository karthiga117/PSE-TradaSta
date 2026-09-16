import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { DashboardComponent } from './dashboard.component';

describe('DashboardComponent', () => {
  let component: DashboardComponent;
  let fixture: ComponentFixture<DashboardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should expose the dashboard default symbol from the mockup', () => {
    expect(component.symbolControl.value).toBe('BTCUSDT');
  });

  it('should normalize common asset names to a valid pair and update the badge', () => {
    component.symbolControl.setValue('eth');
    expect(component.displayedSymbol()).toBe('ETHUSDT');
    expect(component.assetBadge()).toBe('Ξ');

    component.symbolControl.setValue('sol');
    expect(component.displayedSymbol()).toBe('SOLUSDT');
    expect(component.assetBadge()).toBe('S');
  });
});
