export type MoneyValue = number | string;

export interface User {
  id: number;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  is_verified: boolean;
}

export interface AuthCredentials {
  email: string;
  password: string;
}

export interface AuthMessage {
  message: string;
  email?: string;
}

export interface Category {
  id: number;
  category_name: string;
}

export interface Product {
  id: number;
  name: string;
  image_url?: string | null;
  price_per_m2: MoneyValue;
  thickness_mm: number | null;
  min_width: number | null;
  min_length: number | null;
  max_width: number | null;
  max_length: number | null;
  category_id?: number;
  is_active?: boolean;
}

export interface EdgeOption {
  id: number;
  edge_shape: 'straight' | 'curved';
  edge_type: 'matte' | 'transparent';
  thickness_mm: number | null;
  price: MoneyValue;
  is_active: boolean;
}

export interface FacetOption {
  id: number;
  shape: 'straight' | 'curved';
  facet_width_mm: number;
  price: MoneyValue;
  is_active: boolean;
}

export interface TemperingOption {
  id: number;
  thickness_mm: number | null;
  price: MoneyValue;
  is_active: boolean;
}

export interface ProductConfig {
  product: Product;
  edges: EdgeOption[];
  facets: FacetOption[];
  temperings: TemperingOption[];
}

export interface ConfiguratorFormValue {
  widthMm: number | null;
  lengthMm: number | null;
  qty: number;
  edgeId: number | null;
  facetId: number | null;
  temperingId: number | null;
}

export interface CartAddPayload {
  product_id: number;
  width_mm: number | null;
  length_mm: number | null;
  qty: number;
  edge_id: number | null;
  facet_id: number | null;
  tempering_id: number | null;
}

export interface CartItem {
  id: number;
  product_id: number;
  width_mm: number | null;
  length_mm: number | null;
  quantity: number;
  edge_id: number | null;
  facet_id: number | null;
  tempering_id: number | null;
  start_price: MoneyValue;
  current_price: MoneyValue;
  is_available: boolean;
  price_changed: boolean;
  error_message: string | null;
}

export interface CartResponse {
  items: CartItem[];
  total_price: MoneyValue;
  can_order: boolean;
}

export interface DeliveryQuote {
  address: string;
  normalized_address: string | null;
  distance_km: MoneyValue;
  delivery_price: MoneyValue;
  subtotal_price: MoneyValue;
  total_price: MoneyValue;
  within_radius: boolean;
  can_order: boolean;
  message: string | null;
}

export interface DeliverySuggestion {
  title: string;
  subtitle: string | null;
  full_address: string;
  distance_km: MoneyValue;
  within_radius: boolean;
  lat: number;
  lon: number;
}
