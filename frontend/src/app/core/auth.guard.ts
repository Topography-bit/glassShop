import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = async (_, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const user = await authService.ensureProfile();

  if (user) {
    return true;
  }

  return router.createUrlTree(['/login'], {
    queryParams: {
      next: state.url
    }
  });
};

export const adminGuard: CanActivateFn = async (_, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const user = await authService.ensureProfile();

  if (!user) {
    return router.createUrlTree(['/login'], {
      queryParams: {
        next: state.url
      }
    });
  }

  if (user.is_admin) {
    return true;
  }

  return router.createUrlTree(['/account']);
};
