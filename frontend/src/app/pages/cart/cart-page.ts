import { Component, OnDestroy, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import {
  asNumber,
  formatEdgeLabel,
  formatFacetLabel,
  formatPrice,
  formatTemperingLabel
} from '../../core/formatters';
import { CartItem, DeliverySuggestion } from '../../core/models';
import { ShopStore } from '../../core/shop.store';

@Component({
  selector: 'app-cart-page',
  imports: [RouterLink],
  templateUrl: './cart-page.html',
  styleUrl: './cart-page.css'
})
export class CartPageComponent implements OnDestroy {
  private readonly authService = inject(AuthService);
  private suggestTimer: ReturnType<typeof setTimeout> | null = null;

  protected readonly shop = inject(ShopStore);
  protected readonly user = this.authService.user;
  protected readonly formatPrice = formatPrice;
  protected readonly showSuggestions = signal(false);

  constructor() {
    effect(() => {
      if (this.authService.user()) {
        void this.shop.loadCart();
        return;
      }

      this.shop.clearLocalCart();
      this.showSuggestions.set(false);
    });
  }

  ngOnDestroy(): void {
    if (this.suggestTimer != null) {
      clearTimeout(this.suggestTimer);
    }
  }

  protected async decreaseQty(item: CartItem): Promise<void> {
    if (item.quantity <= 1) {
      return;
    }

    await this.shop.changeQuantity(item.id, item.quantity - 1);
  }

  protected async increaseQty(item: CartItem): Promise<void> {
    await this.shop.changeQuantity(item.id, Math.min(item.quantity + 1, 99));
  }

  protected async clearCart(): Promise<void> {
    await this.shop.clearCart();
  }

  protected updateDeliveryAddress(value: string): void {
    this.shop.updateDeliveryAddressInput(value);

    if (this.suggestTimer != null) {
      clearTimeout(this.suggestTimer);
    }

    const normalizedValue = value.trim();
    this.showSuggestions.set(normalizedValue.length >= 3);

    if (normalizedValue.length < 3) {
      this.shop.clearDeliverySuggestions();
      return;
    }

    this.suggestTimer = setTimeout(() => {
      void this.shop.suggestDeliveryAddresses(normalizedValue);
    }, 220);
  }

  protected openSuggestions(): void {
    if (this.shop.deliveryAddress().trim().length >= 3) {
      this.showSuggestions.set(true);
    }
  }

  protected closeSuggestions(): void {
    window.setTimeout(() => this.showSuggestions.set(false), 120);
  }

  protected async selectDeliverySuggestion(
    suggestion: DeliverySuggestion,
    event: MouseEvent
  ): Promise<void> {
    event.preventDefault();
    if (this.suggestTimer != null) {
      clearTimeout(this.suggestTimer);
      this.suggestTimer = null;
    }
    this.shop.applyDeliverySuggestion(suggestion);
    this.showSuggestions.set(false);
    await this.shop.quoteDelivery(suggestion.full_address);
  }

  protected async calculateDelivery(): Promise<void> {
    if (this.suggestTimer != null) {
      clearTimeout(this.suggestTimer);
      this.suggestTimer = null;
    }
    this.showSuggestions.set(false);
    await this.shop.quoteDelivery();
  }

  protected clearDelivery(): void {
    if (this.suggestTimer != null) {
      clearTimeout(this.suggestTimer);
      this.suggestTimer = null;
    }
    this.showSuggestions.set(false);
    this.shop.clearDeliveryQuote();
  }

  protected showEmptySuggestionsState(): boolean {
    return (
      this.showSuggestions() &&
      this.shop.deliveryAddress().trim().length >= 3 &&
      !this.shop.deliverySuggestionsLoading() &&
      this.shop.deliverySuggestions().length === 0
    );
  }

  protected formatDistance(value: number | string | null | undefined): string {
    return `${asNumber(value).toFixed(2)} км`;
  }

  protected readyForOrder(): boolean {
    const cart = this.shop.cart();
    const quote = this.shop.deliveryQuote();
    return Boolean(cart?.can_order && quote?.within_radius);
  }

  protected productName(productId: number): string {
    return this.shop.getProduct(productId)?.name ?? `Материал #${productId}`;
  }

  protected productMeta(productId: number): string {
    const product = this.shop.getProduct(productId);

    if (product == null) {
      return 'Параметры подгружаются';
    }

    const parts: string[] = [];

    if (product.thickness_mm != null) {
      parts.push(`${product.thickness_mm} мм`);
    }

    if (product.max_width != null) {
      parts.push(`до ${product.max_width} мм по ширине`);
    }

    return parts.join(' • ');
  }

  protected cartOptions(item: CartItem): string {
    const config = this.shop.getConfig(item.product_id);

    if (config == null) {
      return 'Параметры подгружаются';
    }

    const parts: string[] = [];

    if (item.edge_id != null) {
      const edge = config.edges.find((value) => value.id === item.edge_id);

      if (edge) {
        parts.push(formatEdgeLabel(edge));
      }
    }

    if (item.facet_id != null) {
      const facet = config.facets.find((value) => value.id === item.facet_id);

      if (facet) {
        parts.push(formatFacetLabel(facet));
      }
    }

    if (item.tempering_id != null) {
      const tempering = config.temperings.find((value) => value.id === item.tempering_id);

      if (tempering) {
        parts.push(formatTemperingLabel(tempering));
      }
    }

    return parts.length ? parts.join(' • ') : 'Без дополнительной обработки';
  }
}
