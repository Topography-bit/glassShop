import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from './core/auth.service';
import { ShopStore } from './core/shop.store';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly shop = inject(ShopStore);
  protected readonly user = this.authService.user;
  protected readonly isMenuOpen = signal(false);
  protected readonly cartCount = this.shop.cartItemCount;

  constructor() {
    this.authService.bootstrap();
  }

  protected closeMenu(): void {
    this.isMenuOpen.set(false);
  }

  protected toggleMenu(): void {
    this.isMenuOpen.update((value) => !value);
  }

  protected async logout(): Promise<void> {
    await this.authService.logout();
    this.shop.clearLocalCart();
    this.closeMenu();
    await this.router.navigateByUrl('/');
  }
}
