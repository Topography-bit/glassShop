import { Component, computed, effect, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { formatPrice } from '../../core/formatters';
import { ShopStore } from '../../core/shop.store';

@Component({
  selector: 'app-account-page',
  imports: [RouterLink],
  templateUrl: './account-page.html',
  styleUrl: './account-page.css'
})
export class AccountPageComponent {
  private readonly authService = inject(AuthService);

  protected readonly shop = inject(ShopStore);
  protected readonly user = this.authService.user;
  protected readonly formatPrice = formatPrice;
  protected readonly cartPreview = computed(() => this.shop.cart()?.items.slice(0, 3) ?? []);

  constructor() {
    effect(() => {
      if (this.authService.user()) {
        void this.shop.loadCart();
      }
    });
  }

  protected productName(productId: number): string {
    return this.shop.getProduct(productId)?.name ?? `Материал #${productId}`;
  }
}
