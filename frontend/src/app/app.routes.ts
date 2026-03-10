import { Routes } from '@angular/router';

import { adminGuard, authGuard } from './core/auth.guard';
import { AccountPageComponent } from './pages/account/account-page';
import { AdminPageComponent } from './pages/admin/admin-page';
import { CartPageComponent } from './pages/cart/cart-page';
import { HomePageComponent } from './pages/home/home-page';
import { LoginPageComponent } from './pages/login/login-page';
import { RegisterPageComponent } from './pages/register/register-page';
import { VerifyPageComponent } from './pages/verify/verify-page';

export const routes: Routes = [
  {
    path: '',
    component: HomePageComponent
  },
  {
    path: 'login',
    component: LoginPageComponent
  },
  {
    path: 'register',
    component: RegisterPageComponent
  },
  {
    path: 'verify',
    component: VerifyPageComponent
  },
  {
    path: 'catalog',
    component: HomePageComponent
  },
  {
    path: 'basket',
    component: CartPageComponent
  },
  {
    path: 'account',
    component: AccountPageComponent,
    canActivate: [authGuard]
  },
  {
    path: 'control',
    component: AdminPageComponent,
    canActivate: [adminGuard]
  },
  {
    path: '**',
    redirectTo: ''
  }
];
