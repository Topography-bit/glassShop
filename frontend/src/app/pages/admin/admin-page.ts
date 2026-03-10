import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AdminService } from '../../core/admin.service';
import { AuthService } from '../../core/auth.service';
import { asNumber, formatPrice, getApiErrorMessage } from '../../core/formatters';
import { EdgeOption, FacetOption, TemperingOption } from '../../core/models';

type AdminTab = 'import' | 'edges' | 'facets' | 'temperings';

@Component({
  selector: 'app-admin-page',
  imports: [FormsModule],
  templateUrl: './admin-page.html',
  styleUrl: './admin-page.css'
})
export class AdminPageComponent {
  private readonly adminService = inject(AdminService);

  protected readonly user = inject(AuthService).user;
  protected readonly formatPrice = formatPrice;
  protected selectedTab: AdminTab = 'import';
  protected loading = false;
  protected error = '';
  protected success = '';
  protected uploadFile: File | null = null;

  protected edges: EdgeOption[] = [];
  protected facets: FacetOption[] = [];
  protected temperings: TemperingOption[] = [];

  protected selectedEdgeId: number | null = null;
  protected selectedFacetId: number | null = null;
  protected selectedTemperingId: number | null = null;

  protected edgeForm: Omit<EdgeOption, 'id'> = {
    edge_shape: 'straight',
    edge_type: 'transparent',
    thickness_mm: 4,
    price: 0,
    is_active: true
  };

  protected facetForm: Omit<FacetOption, 'id'> = {
    shape: 'straight',
    facet_width_mm: 10,
    price: 0,
    is_active: true
  };

  protected temperingForm: Omit<TemperingOption, 'id'> = {
    thickness_mm: 4,
    price: 0,
    is_active: true
  };

  constructor() {
    void this.loadAll();
  }

  protected setTab(tab: AdminTab): void {
    this.selectedTab = tab;
    this.error = '';
    this.success = '';
  }

  protected onFileChange(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    this.uploadFile = input?.files?.[0] ?? null;
  }

  protected clearUploadFile(input?: HTMLInputElement): void {
    this.uploadFile = null;

    if (input != null) {
      input.value = '';
    }
  }

  protected formatUploadFileSize(size: number): string {
    if (size < 1024) {
      return `${size} B`;
    }

    if (size < 1024 * 1024) {
      return `${(size / 1024).toFixed(1)} KB`;
    }

    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }

  protected async uploadProducts(input?: HTMLInputElement): Promise<void> {
    if (!this.uploadFile || this.loading) {
      return;
    }

    this.loading = true;
    this.error = '';
    this.success = '';

    try {
      const response = await this.adminService.uploadProducts(this.uploadFile);
      this.success = response.message;
      this.clearUploadFile(input);
    } catch (error) {
      this.error = getApiErrorMessage(error);
    } finally {
      this.loading = false;
    }
  }

  protected editEdge(edge: EdgeOption): void {
    this.selectedEdgeId = edge.id;
    this.edgeForm = {
      edge_shape: edge.edge_shape,
      edge_type: edge.edge_type,
      thickness_mm: edge.thickness_mm,
      price: asNumber(edge.price),
      is_active: edge.is_active
    };
    this.selectedTab = 'edges';
  }

  protected resetEdgeForm(): void {
    this.selectedEdgeId = null;
    this.edgeForm = {
      edge_shape: 'straight',
      edge_type: 'transparent',
      thickness_mm: 4,
      price: 0,
      is_active: true
    };
  }

  protected async saveEdge(): Promise<void> {
    if (this.loading) {
      return;
    }

    this.loading = true;
    this.error = '';
    this.success = '';

    try {
      if (this.selectedEdgeId) {
        await this.adminService.updateEdge(this.selectedEdgeId, this.edgeForm);
        this.success = 'Кромка обновлена.';
      } else {
        await this.adminService.createEdge(this.edgeForm);
        this.success = 'Кромка добавлена.';
      }

      this.resetEdgeForm();
      this.edges = await this.adminService.listEdges();
    } catch (error) {
      this.error = getApiErrorMessage(error);
    } finally {
      this.loading = false;
    }
  }

  protected async deleteEdge(edgeId: number): Promise<void> {
    if (!confirm('Удалить эту кромку?')) {
      return;
    }

    try {
      await this.adminService.deleteEdge(edgeId);
      this.edges = await this.adminService.listEdges();
      this.success = 'Кромка удалена.';
      if (this.selectedEdgeId === edgeId) {
        this.resetEdgeForm();
      }
    } catch (error) {
      this.error = getApiErrorMessage(error);
    }
  }

  protected editFacet(facet: FacetOption): void {
    this.selectedFacetId = facet.id;
    this.facetForm = {
      shape: facet.shape,
      facet_width_mm: facet.facet_width_mm,
      price: asNumber(facet.price),
      is_active: facet.is_active
    };
    this.selectedTab = 'facets';
  }

  protected resetFacetForm(): void {
    this.selectedFacetId = null;
    this.facetForm = {
      shape: 'straight',
      facet_width_mm: 10,
      price: 0,
      is_active: true
    };
  }

  protected async saveFacet(): Promise<void> {
    if (this.loading) {
      return;
    }

    this.loading = true;
    this.error = '';
    this.success = '';

    try {
      if (this.selectedFacetId) {
        await this.adminService.updateFacet(this.selectedFacetId, this.facetForm);
        this.success = 'Фацет обновлен.';
      } else {
        await this.adminService.createFacet(this.facetForm);
        this.success = 'Фацет добавлен.';
      }

      this.resetFacetForm();
      this.facets = await this.adminService.listFacets();
    } catch (error) {
      this.error = getApiErrorMessage(error);
    } finally {
      this.loading = false;
    }
  }

  protected async deleteFacet(facetId: number): Promise<void> {
    if (!confirm('Удалить этот фацет?')) {
      return;
    }

    try {
      await this.adminService.deleteFacet(facetId);
      this.facets = await this.adminService.listFacets();
      this.success = 'Фацет удален.';
      if (this.selectedFacetId === facetId) {
        this.resetFacetForm();
      }
    } catch (error) {
      this.error = getApiErrorMessage(error);
    }
  }

  protected editTempering(tempering: TemperingOption): void {
    this.selectedTemperingId = tempering.id;
    this.temperingForm = {
      thickness_mm: tempering.thickness_mm,
      price: asNumber(tempering.price),
      is_active: tempering.is_active
    };
    this.selectedTab = 'temperings';
  }

  protected resetTemperingForm(): void {
    this.selectedTemperingId = null;
    this.temperingForm = {
      thickness_mm: 4,
      price: 0,
      is_active: true
    };
  }

  protected async saveTempering(): Promise<void> {
    if (this.loading) {
      return;
    }

    this.loading = true;
    this.error = '';
    this.success = '';

    try {
      if (this.selectedTemperingId) {
        await this.adminService.updateTempering(this.selectedTemperingId, this.temperingForm);
        this.success = 'Закалка обновлена.';
      } else {
        await this.adminService.createTempering(this.temperingForm);
        this.success = 'Закалка добавлена.';
      }

      this.resetTemperingForm();
      this.temperings = await this.adminService.listTemperings();
    } catch (error) {
      this.error = getApiErrorMessage(error);
    } finally {
      this.loading = false;
    }
  }

  protected async deleteTempering(temperingId: number): Promise<void> {
    if (!confirm('Удалить эту закалку?')) {
      return;
    }

    try {
      await this.adminService.deleteTempering(temperingId);
      this.temperings = await this.adminService.listTemperings();
      this.success = 'Закалка удалена.';
      if (this.selectedTemperingId === temperingId) {
        this.resetTemperingForm();
      }
    } catch (error) {
      this.error = getApiErrorMessage(error);
    }
  }

  private async loadAll(): Promise<void> {
    try {
      const [edges, facets, temperings] = await Promise.all([
        this.adminService.listEdges(),
        this.adminService.listFacets(),
        this.adminService.listTemperings()
      ]);

      this.edges = edges;
      this.facets = facets;
      this.temperings = temperings;
    } catch (error) {
      this.error = getApiErrorMessage(error);
    }
  }
}
