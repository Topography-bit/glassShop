import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import {
  AuthMessage,
  EdgeOption,
  FacetOption,
  TemperingOption
} from './models';

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  private readonly http = inject(HttpClient);

  listEdges(): Promise<EdgeOption[]> {
    return firstValueFrom(this.http.get<EdgeOption[]>('/admin/edges'));
  }

  createEdge(payload: Omit<EdgeOption, 'id'>): Promise<EdgeOption> {
    return firstValueFrom(this.http.post<EdgeOption>('/admin/edges', payload));
  }

  updateEdge(edgeId: number, payload: Omit<EdgeOption, 'id'>): Promise<EdgeOption> {
    return firstValueFrom(this.http.put<EdgeOption>(`/admin/edges/${edgeId}`, payload));
  }

  deleteEdge(edgeId: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/admin/edges/${edgeId}`));
  }

  listFacets(): Promise<FacetOption[]> {
    return firstValueFrom(this.http.get<FacetOption[]>('/admin/facets'));
  }

  createFacet(payload: Omit<FacetOption, 'id'>): Promise<FacetOption> {
    return firstValueFrom(this.http.post<FacetOption>('/admin/facets', payload));
  }

  updateFacet(facetId: number, payload: Omit<FacetOption, 'id'>): Promise<FacetOption> {
    return firstValueFrom(this.http.put<FacetOption>(`/admin/facets/${facetId}`, payload));
  }

  deleteFacet(facetId: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/admin/facets/${facetId}`));
  }

  listTemperings(): Promise<TemperingOption[]> {
    return firstValueFrom(this.http.get<TemperingOption[]>('/admin/temperings'));
  }

  createTempering(payload: Omit<TemperingOption, 'id'>): Promise<TemperingOption> {
    return firstValueFrom(this.http.post<TemperingOption>('/admin/temperings', payload));
  }

  updateTempering(
    temperingId: number,
    payload: Omit<TemperingOption, 'id'>
  ): Promise<TemperingOption> {
    return firstValueFrom(this.http.put<TemperingOption>(`/admin/temperings/${temperingId}`, payload));
  }

  deleteTempering(temperingId: number): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/admin/temperings/${temperingId}`));
  }

  uploadProducts(file: File): Promise<AuthMessage> {
    const formData = new FormData();
    formData.append('file', file);
    return firstValueFrom(this.http.post<AuthMessage>('/admin/add_all_products', formData));
  }
}
