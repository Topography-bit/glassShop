import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import {
  CartAddPayload,
  CartResponse,
  Category,
  DeliveryQuote,
  DeliverySuggestion,
  Product,
  ProductConfig
} from './models';
import { getApiErrorMessage } from './formatters';

@Injectable({
  providedIn: 'root'
})
export class ShopStore {
  private readonly http = inject(HttpClient);
  private deliverySuggestRequestId = 0;

  readonly categories = signal<Category[]>([]);
  readonly productsByCategory = signal<Record<number, Product[]>>({});
  readonly selectedCategoryId = signal<number | null>(null);
  readonly selectedConfig = signal<ProductConfig | null>(null);
  readonly catalogLoading = signal(false);
  readonly configLoading = signal(false);
  readonly cartLoading = signal(false);
  readonly deliveryLoading = signal(false);
  readonly deliverySuggestionsLoading = signal(false);
  readonly catalogError = signal('');
  readonly cartError = signal('');
  readonly deliveryError = signal('');
  readonly actionMessage = signal('');
  readonly cart = signal<CartResponse | null>(null);
  readonly deliveryQuote = signal<DeliveryQuote | null>(null);
  readonly deliverySuggestions = signal<DeliverySuggestion[]>([]);
  readonly selectedDeliverySuggestion = signal<DeliverySuggestion | null>(null);
  readonly deliveryAddress = signal('');

  private readonly configCache = signal<Record<number, ProductConfig>>({});

  private normalizeCart(cart: CartResponse): CartResponse {
    return {
      ...cart,
      items: [...cart.items].sort((left, right) => left.id - right.id)
    };
  }

  readonly currentProducts = computed(() => {
    const categoryId = this.selectedCategoryId();

    if (categoryId == null) {
      return [];
    }

    return this.productsByCategory()[categoryId] ?? [];
  });

  readonly cartItemCount = computed(() => {
    const cart = this.cart();
    return cart?.items.reduce((total, item) => total + item.quantity, 0) ?? 0;
  });

  async loadCatalog(): Promise<void> {
    if (this.catalogLoading()) {
      return;
    }

    this.catalogLoading.set(true);
    this.catalogError.set('');

    try {
      const categories = await firstValueFrom(this.http.get<Category[]>('/categories'));
      const productsByCategory: Record<number, Product[]> = {};

      for (const category of categories) {
        const products = await firstValueFrom(
          this.http.get<Product[]>(`/categories/${category.id}/products`)
        );

        productsByCategory[category.id] = products.filter((product) => product.is_active !== false);
      }

      const visibleCategories = categories.filter(
        (category) => (productsByCategory[category.id] ?? []).length > 0
      );
      const activeCategories = visibleCategories.length ? visibleCategories : categories;

      this.categories.set(activeCategories);
      this.productsByCategory.set(productsByCategory);

      const preservedCategoryId =
        this.selectedCategoryId() != null &&
        (productsByCategory[this.selectedCategoryId() as number] ?? []).length
          ? this.selectedCategoryId()
          : null;

      const nextCategoryId = preservedCategoryId ?? activeCategories[0]?.id ?? null;
      this.selectedCategoryId.set(nextCategoryId);

      if (nextCategoryId == null) {
        this.selectedConfig.set(null);
        return;
      }

      const products = productsByCategory[nextCategoryId] ?? [];
      const selectedProductId = this.selectedConfig()?.product.id;
      const canKeepSelected = products.some((product) => product.id === selectedProductId);
      const nextProductId = canKeepSelected ? selectedProductId : products[0]?.id;

      if (nextProductId != null) {
        await this.selectProduct(nextProductId);
      } else {
        this.selectedConfig.set(null);
      }
    } catch (error) {
      this.catalogError.set(getApiErrorMessage(error));
    } finally {
      this.catalogLoading.set(false);
    }
  }

  async selectCategory(categoryId: number): Promise<void> {
    this.selectedCategoryId.set(categoryId);
    const products = this.productsByCategory()[categoryId] ?? [];

    if (!products.length) {
      this.selectedConfig.set(null);
      return;
    }

    const selectedProductId = this.selectedConfig()?.product.id;

    if (selectedProductId && products.some((product) => product.id === selectedProductId)) {
      return;
    }

    await this.selectProduct(products[0].id);
  }

  async selectProduct(productId: number): Promise<void> {
    const cached = this.configCache()[productId];

    if (cached) {
      this.selectedConfig.set(cached);
      this.actionMessage.set('');
      return;
    }

    this.configLoading.set(true);
    this.actionMessage.set('');

    try {
      const config = await firstValueFrom(
        this.http.get<ProductConfig>(`/categories/products/${productId}/config`)
      );

      this.configCache.update((cache) => ({
        ...cache,
        [productId]: config
      }));
      this.selectedConfig.set(config);
    } catch (error) {
      this.actionMessage.set(getApiErrorMessage(error));
    } finally {
      this.configLoading.set(false);
    }
  }

  async loadCart(): Promise<void> {
    this.cartLoading.set(true);
    this.cartError.set('');

    try {
      const cart = await firstValueFrom(this.http.get<CartResponse>('/cart'));
      this.cart.set(this.normalizeCart(cart));
      await this.prefetchConfigs(cart.items.map((item) => item.product_id));

      if (!cart.items.length) {
        this.deliveryQuote.set(null);
        this.deliveryError.set('');
      } else if (this.deliveryAddress().trim()) {
        await this.refreshDeliveryQuote();
      }
    } catch (error) {
      this.cart.set({
        items: [],
        total_price: '0',
        can_order: true
      });
      this.deliveryQuote.set(null);
      this.deliveryError.set('');
      this.cartError.set(getApiErrorMessage(error));
    } finally {
      this.cartLoading.set(false);
    }
  }

  async addToCart(payload: CartAddPayload): Promise<boolean> {
    this.actionMessage.set('');

    try {
      await firstValueFrom(this.http.post('/cart', payload));
      await this.loadCart();
      this.actionMessage.set('Позиция добавлена в корзину.');
      return true;
    } catch (error) {
      this.actionMessage.set(getApiErrorMessage(error));
      return false;
    }
  }

  async changeQuantity(cartItemId: number, qty: number): Promise<void> {
    this.actionMessage.set('');

    try {
      await firstValueFrom(
        this.http.patch('/cart/change_qty', {
          cart_prod_id: cartItemId,
          qty
        })
      );
      await this.loadCart();
    } catch (error) {
      this.actionMessage.set(getApiErrorMessage(error));
    }
  }

  async removeFromCart(cartItemId: number): Promise<void> {
    this.actionMessage.set('');

    try {
      await firstValueFrom(this.http.delete(`/cart/${cartItemId}`));
      await this.loadCart();
    } catch (error) {
      this.actionMessage.set(getApiErrorMessage(error));
    }
  }

  async clearCart(): Promise<void> {
    this.actionMessage.set('');

    try {
      await firstValueFrom(this.http.delete('/cart'));
      this.cart.set({
        items: [],
        total_price: '0',
        can_order: true
      });
      this.clearDeliveryQuote();
      this.actionMessage.set('Корзина очищена.');
    } catch (error) {
      this.actionMessage.set(getApiErrorMessage(error));
    }
  }

  updateDeliveryAddressInput(value: string): void {
    const nextValue = value;
    const normalizedValue = nextValue.trim();
    const selectedSuggestion = this.selectedDeliverySuggestion();

    this.deliveryAddress.set(nextValue);
    this.deliveryQuote.set(null);
    this.deliveryError.set('');

    if (!normalizedValue) {
      this.clearDeliverySuggestions();
      this.selectedDeliverySuggestion.set(null);
      return;
    }

    if (selectedSuggestion?.full_address !== normalizedValue) {
      this.selectedDeliverySuggestion.set(null);
    }
  }

  async suggestDeliveryAddresses(query: string): Promise<void> {
    const normalizedQuery = query.trim();

    if (normalizedQuery.length < 3) {
      this.clearDeliverySuggestions();
      return;
    }

    const requestId = ++this.deliverySuggestRequestId;
    this.deliverySuggestionsLoading.set(true);

    try {
      const suggestions = await firstValueFrom(
        this.http.get<DeliverySuggestion[]>('/cart/delivery/suggest', {
          params: { q: normalizedQuery }
        })
      );

      if (requestId !== this.deliverySuggestRequestId) {
        return;
      }

      this.deliverySuggestions.set(suggestions);
    } catch {
      if (requestId !== this.deliverySuggestRequestId) {
        return;
      }

      this.deliverySuggestions.set([]);
    } finally {
      if (requestId === this.deliverySuggestRequestId) {
        this.deliverySuggestionsLoading.set(false);
      }
    }
  }

  applyDeliverySuggestion(suggestion: DeliverySuggestion): void {
    this.deliveryAddress.set(suggestion.full_address);
    this.selectedDeliverySuggestion.set(suggestion);
    this.deliveryQuote.set(null);
    this.deliverySuggestions.set([]);
    this.deliveryError.set('');
  }

  clearDeliverySuggestions(): void {
    this.deliverySuggestRequestId += 1;
    this.deliverySuggestions.set([]);
    this.deliverySuggestionsLoading.set(false);
  }

  async quoteDelivery(address?: string): Promise<void> {
    const nextAddress = (address ?? this.deliveryAddress()).trim();
    this.deliveryAddress.set(nextAddress);

    if (!nextAddress) {
      this.deliveryQuote.set(null);
      this.deliveryError.set('Укажи адрес доставки, чтобы рассчитать километраж от Майкопа.');
      return;
    }

    if ((this.cart()?.items.length ?? 0) === 0) {
      this.deliveryQuote.set(null);
      this.deliveryError.set('Сначала добавь товары в корзину.');
      return;
    }

    await this.refreshDeliveryQuote();
  }

  clearDeliveryQuote(): void {
    this.deliveryQuote.set(null);
    this.deliveryError.set('');
    this.deliveryAddress.set('');
    this.selectedDeliverySuggestion.set(null);
    this.clearDeliverySuggestions();
  }

  clearLocalCart(): void {
    this.cart.set(null);
    this.cartError.set('');
    this.clearDeliveryQuote();
    this.actionMessage.set('');
  }

  clearActionMessage(): void {
    this.actionMessage.set('');
  }

  getProduct(productId: number): Product | undefined {
    const cachedProduct = this.configCache()[productId]?.product;

    if (cachedProduct) {
      return cachedProduct;
    }

    return Object.values(this.productsByCategory())
      .flat()
      .find((product) => product.id === productId);
  }

  getConfig(productId: number): ProductConfig | undefined {
    return this.configCache()[productId];
  }

  private async prefetchConfigs(productIds: number[]): Promise<void> {
    const uniqueProductIds = Array.from(new Set(productIds)).filter(
      (productId) => this.configCache()[productId] == null
    );

    if (!uniqueProductIds.length) {
      return;
    }

    const loadedConfigs = await Promise.all(
      uniqueProductIds.map(async (productId) => {
        try {
          return await firstValueFrom(
            this.http.get<ProductConfig>(`/categories/products/${productId}/config`)
          );
        } catch {
          return null;
        }
      })
    );

    this.configCache.update((cache) => {
      const nextCache = { ...cache };

      for (const config of loadedConfigs) {
        if (config) {
          nextCache[config.product.id] = config;
        }
      }

      return nextCache;
    });
  }

  private async refreshDeliveryQuote(): Promise<void> {
    const address = this.deliveryAddress().trim();

    if (!address) {
      return;
    }

    this.deliveryLoading.set(true);
    this.deliveryError.set('');

    try {
      const selectedSuggestion = this.selectedDeliverySuggestion();
      const payload: {
        address: string;
        normalized_address?: string;
        lat?: number;
        lon?: number;
      } = {
        address
      };

      if (selectedSuggestion?.full_address === address) {
        payload.normalized_address = selectedSuggestion.full_address;
        payload.lat = selectedSuggestion.lat;
        payload.lon = selectedSuggestion.lon;
      }

      const quote = await firstValueFrom(this.http.post<DeliveryQuote>('/cart/delivery/quote', payload));
      this.deliveryQuote.set(quote);
    } catch (error) {
      this.deliveryQuote.set(null);
      this.deliveryError.set(getApiErrorMessage(error));
    } finally {
      this.deliveryLoading.set(false);
    }
  }
}
