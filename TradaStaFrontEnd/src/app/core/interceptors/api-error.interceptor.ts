import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

export const apiErrorInterceptor: HttpInterceptorFn = (req, next) => {
  const requestId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  const clonedRequest = req.clone({
    setHeaders: {
      'X-Request-ID': requestId,
    },
  });

  return next(clonedRequest).pipe(
    catchError((error: HttpErrorResponse) => {
      const message = error.status === 0
        ? 'Unable to reach the backend service. Please check that the API is running.'
        : error.status === 404
          ? 'The requested backend resource was not found.'
          : error.status === 422
            ? 'The backend rejected the request. Please review the selected values.'
            : error.status >= 500
              ? 'The backend is currently unavailable. Please try again shortly.'
              : 'The request could not be completed. Please try again.';

      return throwError(() => new Error(message));
    }),
  );
};
