import { HttpErrorResponse } from '@angular/common/http';

import { EdgeOption, FacetOption, MoneyValue, TemperingOption } from './models';

const priceFormatter = new Intl.NumberFormat('ru-RU', {
  style: 'currency',
  currency: 'RUB',
  maximumFractionDigits: 2
});

const areaFormatter = new Intl.NumberFormat('ru-RU', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
});

const dimensionFormatter = new Intl.NumberFormat('ru-RU');

export function asNumber(value: MoneyValue | null | undefined): number {
  if (typeof value === 'number') {
    return value;
  }

  if (typeof value === 'string') {
    const normalized = value.replace(',', '.');
    const parsed = Number.parseFloat(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  return 0;
}

export function formatPrice(value: MoneyValue | null | undefined): string {
  return priceFormatter.format(asNumber(value));
}

export function formatArea(value: number | null | undefined): string {
  return `${areaFormatter.format(value ?? 0)} м²`;
}

export function formatDimension(value: number | null | undefined): string {
  if (value == null) {
    return 'по запросу';
  }

  return `${dimensionFormatter.format(value)} мм`;
}

export function formatEdgeLabel(edge: EdgeOption): string {
  const shape = edge.edge_shape === 'curved' ? 'Криволинейная' : 'Прямая';
  const type = edge.edge_type === 'transparent' ? 'полировка' : 'матовая шлифовка';
  return `${shape} ${type}`;
}

export function formatFacetLabel(facet: FacetOption): string {
  const shape = facet.shape === 'curved' ? 'криволинейный' : 'прямой';
  return `Фацет ${facet.facet_width_mm} мм, ${shape}`;
}

export function formatTemperingLabel(tempering: TemperingOption): string {
  if (tempering.thickness_mm == null) {
    return 'Закалка';
  }

  return `Закалка ${tempering.thickness_mm} мм`;
}

export function getApiErrorMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    const detail = error.error?.detail;

    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }

    if (Array.isArray(detail) && detail.length) {
      return detail
        .map((item) => item?.msg ?? item?.message ?? 'Некорректные данные')
        .join('. ');
    }

    const message = error.error?.message;

    if (typeof message === 'string' && message.trim()) {
      return message;
    }
  }

  return 'Не получилось завершить действие. Попробуй еще раз.';
}
