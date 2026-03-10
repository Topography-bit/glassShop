import { HttpContextToken, HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';

import { AuthService } from './auth.service';

export const SKIP_AUTH_REFRESH = new HttpContextToken<boolean>(() => false);

const bypassRefresh = [
  '/auth/login',
  '/auth/registration',
  '/auth/registration/confirm',
  '/auth/registration/resend_verify_code',
  '/auth/refresh',
  '/auth/logout'
];

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const authService = inject(AuthService);
  const requestWithCredentials = request.clone({ withCredentials: true });

  return next(requestWithCredentials).pipe(
    catchError((error: HttpErrorResponse) => {
      const shouldSkipRefresh =
        request.context.get(SKIP_AUTH_REFRESH) ||
        bypassRefresh.some((endpoint) => request.url.includes(endpoint));

      if (error.status !== 401 || shouldSkipRefresh) {
        return throwError(() => error);
      }

      return authService.refreshSession().pipe(
        switchMap(() => next(requestWithCredentials)),
        catchError((refreshError: HttpErrorResponse) => {
          authService.clearSession();
          return throwError(() => (refreshError.status ? error : refreshError));
        })
      );
    })
  );
};
