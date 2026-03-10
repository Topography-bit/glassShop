import {
  AfterViewInit,
  Component,
  DestroyRef,
  ElementRef,
  HostListener,
  QueryList,
  ViewChildren,
  computed,
  effect,
  inject,
  signal
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import {
  asNumber,
  formatArea,
  formatDimension,
  formatEdgeLabel,
  formatFacetLabel,
  formatPrice,
  formatTemperingLabel
} from '../../core/formatters';
import { CartItem, ConfiguratorFormValue, Product, ProductConfig } from '../../core/models';
import { ShopStore } from '../../core/shop.store';

const CONFIG_STEPS = [
  {
    id: 1,
    eyebrow: 'Шаг 1',
    title: 'Пропорции',
    description: 'Задайте размер полотна и проверьте диапазон.'
  },
  {
    id: 2,
    eyebrow: 'Шаг 2',
    title: 'Обработка',
    description: 'Выберите характер кромки и фацет.'
  },
  {
    id: 3,
    eyebrow: 'Шаг 3',
    title: 'Финал',
    description: 'Добавьте закалку, количество и итоговую цену.'
  }
] as const;

const CATALOG_SKELETONS = Array.from({ length: 6 }, (_, index) => index);
const TAB_SKELETONS = Array.from({ length: 4 }, (_, index) => index);
const CART_SKELETONS = Array.from({ length: 3 }, (_, index) => index);

interface MaterialTheme {
  tone?: string;
  atmosphere?: string;
  previewTint: string;
  surface: string;
  accent: string;
}

const MATERIAL_THEMES = {
  silver: {
    tone: 'Серебро',
    previewTint: 'rgba(185, 199, 216, 0.34)',
    surface:
      'radial-gradient(circle at 28% 24%, rgba(255,255,255,0.94), transparent 34%), linear-gradient(145deg, #f7fafc, #d6e0eb 56%, #fefefe 100%)',
    accent: '#b9c7d8'
  },
  graphite: {
    tone: 'Графит',
    previewTint: 'rgba(118, 131, 150, 0.36)',
    surface:
      'radial-gradient(circle at 30% 18%, rgba(255,255,255,0.7), transparent 28%), linear-gradient(150deg, #dde1e6, #9099a5 52%, #f1f3f6 100%)',
    accent: '#8e99a7'
  },
  bronze: {
    tone: 'Бронза',
    previewTint: 'rgba(185, 138, 95, 0.3)',
    surface:
      'radial-gradient(circle at 30% 20%, rgba(255,255,255,0.66), transparent 30%), linear-gradient(145deg, #efe2d5, #b58f70 54%, #faf6f1 100%)',
    accent: '#b98a5f'
  },
  green: {
    tone: 'Зеленое',
    previewTint: 'rgba(116, 156, 134, 0.28)',
    surface:
      'radial-gradient(circle at 28% 22%, rgba(255,255,255,0.78), transparent 30%), linear-gradient(145deg, #e4eee8, #87a997 56%, #f5f8f5 100%)',
    accent: '#7ca18e'
  },
  tinted: {
    tone: 'Тонированное',
    previewTint: 'rgba(121, 138, 155, 0.3)',
    surface:
      'radial-gradient(circle at 28% 22%, rgba(255,255,255,0.72), transparent 30%), linear-gradient(145deg, #e6eaee, #95a0ac 56%, #f6f8fa 100%)',
    accent: '#94a1ae'
  },
  gold: {
    tone: 'Золото',
    previewTint: 'rgba(203, 176, 112, 0.3)',
    surface:
      'radial-gradient(circle at 30% 20%, rgba(255,255,255,0.78), transparent 30%), linear-gradient(145deg, #f5edd8, #d2b46d 54%, #fbf7ee 100%)',
    accent: '#cfb16a'
  },
  satinLight: {
    tone: 'Сатин светлый',
    previewTint: 'rgba(226, 232, 238, 0.34)',
    surface:
      'radial-gradient(circle at 28% 24%, rgba(255,255,255,0.88), transparent 34%), linear-gradient(150deg, #f7f8f8, #dfe4e8 58%, #f5f7f8 100%)',
    accent: '#dde4ea'
  },
  crystal: {
    tone: 'Кристалл',
    previewTint: 'rgba(141, 155, 173, 0.28)',
    surface:
      'radial-gradient(circle at 28% 24%, rgba(255,255,255,0.6), transparent 32%), linear-gradient(150deg, #ccd3db, #6e7786 56%, #f5f7fa 100%)',
    accent: '#768396'
  }
} satisfies Record<string, MaterialTheme>;

function createDefaultForm(config: ProductConfig | null): ConfiguratorFormValue {
  return {
    widthMm: config?.product.min_width ?? null,
    lengthMm: config?.product.min_length ?? null,
    qty: 1,
    edgeId: null,
    facetId: null,
    temperingId: null
  };
}

function greatestCommonDivisor(a: number, b: number): number {
  let left = Math.abs(a);
  let right = Math.abs(b);

  while (right !== 0) {
    const next = left % right;
    left = right;
    right = next;
  }

  return left || 1;
}

@Component({
  selector: 'app-home-page',
  templateUrl: './home-page.html',
  styleUrl: './home-page.css'
})
export class HomePageComponent implements AfterViewInit {
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  private gsapModulePromise: Promise<typeof import('gsap')> | null = null;
  private previewResizeObserver: ResizeObserver | null = null;

  @ViewChildren('catalogCard') private readonly catalogCards!: QueryList<ElementRef<HTMLElement>>;
  @ViewChildren('previewStage') private readonly previewStages!: QueryList<ElementRef<HTMLElement>>;

  protected readonly shop = inject(ShopStore);
  protected readonly user = this.authService.user;
  protected readonly form = signal<ConfiguratorFormValue>(createDefaultForm(null));
  protected readonly activeStep = signal(1);
  protected readonly heroScrollProgress = signal(0);
  protected readonly previewViewport = signal({ width: 0, height: 0 });
  protected readonly steps = CONFIG_STEPS;
  protected readonly catalogSkeletons = CATALOG_SKELETONS;
  protected readonly tabSkeletons = TAB_SKELETONS;
  protected readonly cartSkeletons = CART_SKELETONS;
  protected readonly formatPrice = formatPrice;
  protected readonly formatDimension = formatDimension;
  protected readonly formatEdgeLabel = formatEdgeLabel;
  protected readonly formatFacetLabel = formatFacetLabel;
  protected readonly formatTemperingLabel = formatTemperingLabel;
  protected readonly formatArea = formatArea;
  protected readonly selectedProduct = computed(() => this.shop.selectedConfig()?.product ?? null);
  protected readonly selectedEdge = computed(() => {
    const config = this.shop.selectedConfig();
    const edgeId = this.form().edgeId;
    return config?.edges.find((edge) => edge.id === edgeId) ?? null;
  });
  protected readonly selectedFacet = computed(() => {
    const config = this.shop.selectedConfig();
    const facetId = this.form().facetId;
    return config?.facets.find((facet) => facet.id === facetId) ?? null;
  });
  protected readonly selectedTempering = computed(() => {
    const config = this.shop.selectedConfig();
    const temperingId = this.form().temperingId;
    return config?.temperings.find((tempering) => tempering.id === temperingId) ?? null;
  });
  protected readonly previewArea = computed(() => {
    const values = this.form();

    if (values.widthMm == null || values.lengthMm == null) {
      return null;
    }

    return (values.widthMm * values.lengthMm) / 1_000_000;
  });
  protected readonly previewPrice = computed(() => {
    const config = this.shop.selectedConfig();
    const values = this.form();

    if (config == null || values.widthMm == null || values.lengthMm == null) {
      return null;
    }

    const basePrice =
      (values.widthMm * values.lengthMm * asNumber(config.product.price_per_m2)) / 1_000_000;
    const edgePrice = config.edges.find((edge) => edge.id === values.edgeId)?.price ?? 0;
    const facetPrice = config.facets.find((facet) => facet.id === values.facetId)?.price ?? 0;
    const temperingPrice =
      config.temperings.find((tempering) => tempering.id === values.temperingId)?.price ?? 0;

    return (basePrice + asNumber(edgePrice) + asNumber(facetPrice) + asNumber(temperingPrice)) *
      values.qty;
  });
  protected readonly pricePerPiece = computed(() => {
    const total = this.previewPrice();
    return total == null ? null : total / this.form().qty;
  });
  protected readonly previewGeometry = computed(() => {
    const product = this.selectedProduct();
    const values = this.form();
    const width = values.widthMm ?? product?.min_width ?? 1400;
    const height = values.lengthMm ?? product?.min_length ?? 900;
    const viewport = this.previewViewport();
    const stageWidth = Math.max(viewport.width || 520, 360);
    const stageHeight = Math.max(viewport.height || 320, 280);
    const horizontalPadding = Math.max(24, Math.min(stageWidth * 0.08, 54));
    const topPadding = Math.max(20, Math.min(stageHeight * 0.08, 30));
    const bottomReserve = Math.max(68, Math.min(stageHeight * 0.22, 92));
    const drawableWidth = Math.max(stageWidth - horizontalPadding * 2, 180);
    const drawableHeight = Math.max(stageHeight - topPadding - bottomReserve, 120);
    const scale = Math.min(
      drawableWidth / Math.max(width, 1),
      drawableHeight / Math.max(height, 1)
    );
    const frameWidth = Math.max(64, Number((width * scale).toFixed(2)));
    const frameHeight = Math.max(54, Number((height * scale).toFixed(2)));
    const cornerRadius =
      this.selectedEdge()?.edge_shape === 'curved' || this.selectedFacet()?.shape === 'curved'
        ? 32
        : 18;
    const facetBoost =
      this.selectedFacet() == null ? 0 : this.selectedFacet()!.shape === 'curved' ? 8 : 6;
    const edgeBoost =
      this.selectedEdge() == null ? 0 : this.selectedEdge()!.edge_type === 'matte' ? 4 : 2;
    const temperingBoost = this.selectedTempering() ? 5 : 0;

    return {
      width,
      height,
      frameWidth,
      frameHeight,
      cornerRadius,
      bevelWidth: 11 + facetBoost + edgeBoost + temperingBoost
    };
  });
  protected readonly ratioLabel = computed(() => {
    const values = this.form();

    if (values.widthMm == null || values.lengthMm == null) {
      return 'Живое превью появится после ввода размеров';
    }

    const gcd = greatestCommonDivisor(values.widthMm, values.lengthMm);
    return `${values.widthMm / gcd}:${values.lengthMm / gcd}`;
  });
  protected readonly selectionSummary = computed(() => {
    const parts = [];

    if (this.selectedEdge()) {
      parts.push(formatEdgeLabel(this.selectedEdge()!));
    }

    if (this.selectedFacet()) {
      parts.push(formatFacetLabel(this.selectedFacet()!));
    }

    if (this.selectedTempering()) {
      parts.push(formatTemperingLabel(this.selectedTempering()!));
    }

    return parts.length ? parts : ['Без дополнительных опций'];
  });
  protected readonly isSizeStepValid = computed(() => {
    const values = this.form();
    return values.widthMm != null && values.lengthMm != null && !this.dimensionsWarning();
  });
  protected readonly showCatalogSkeleton = computed(
    () => this.shop.catalogLoading() && this.shop.categories().length === 0
  );
  protected readonly showCartSkeleton = computed(
    () => this.shop.cartLoading() && this.user() != null && (this.shop.cart()?.items?.length ?? 0) === 0
  );
  protected readonly cartPreviewItems = computed(() => (this.shop.cart()?.items ?? []).slice(0, 3));
  protected readonly remainingCartItemsCount = computed(() => {
    const items = this.shop.cart()?.items ?? [];
    return Math.max(items.length - this.cartPreviewItems().length, 0);
  });
  protected readonly heroTitleWeight = computed(
    () => 510 + Math.round(this.heroScrollProgress() * 130)
  );
  protected readonly heroTitleTracking = computed(
    () => `${(-0.055 + this.heroScrollProgress() * 0.014).toFixed(3)}em`
  );
  protected readonly heroTitleVariation = computed(
    () => `'wght' ${this.heroTitleWeight()}, 'opsz' 72`
  );
  protected readonly dimensionsWarning = computed(() => {
    const product = this.selectedProduct();
    const values = this.form();

    if (
      product == null ||
      values.widthMm == null ||
      values.lengthMm == null ||
      product.min_width == null ||
      product.min_length == null ||
      product.max_width == null ||
      product.max_length == null
    ) {
      return '';
    }

    if (values.widthMm < product.min_width || values.widthMm > product.max_width) {
      return `Ширина должна быть от ${product.min_width} до ${product.max_width} мм.`;
    }

    if (values.lengthMm < product.min_length || values.lengthMm > product.max_length) {
      return `Длина должна быть от ${product.min_length} до ${product.max_length} мм.`;
    }

    return '';
  });
  protected readonly heroStats = [
    { value: '48 ч', label: 'старт производства после подтверждения проекта' },
    { value: '±1 мм', label: 'точность размеров в онлайн-конфигураторе' },
    { value: '3 шага', label: 'от выбора материала до рабочей сметы' }
  ];
  protected readonly promises = [
    'Подбираем зеркало и стекло под интерьер, мебель, фасады и коммерческие пространства.',
    'Показываем обработку и ограничения сразу в интерфейсе, без отдельных таблиц и лишних переходов.',
    'Фиксируем стоимость и корзину, чтобы к заказу можно было вернуться без повторного расчета.'
  ];

  constructor() {
    void this.shop.loadCatalog();

    effect(
      () => {
        this.form.set(createDefaultForm(this.shop.selectedConfig()));
        this.activeStep.set(1);
      },
      { allowSignalWrites: true }
    );

    effect(() => {
      if (this.authService.user()) {
        void this.shop.loadCart();
        return;
      }

      this.shop.clearLocalCart();
    });
  }

  ngAfterViewInit(): void {
    void this.animateCatalogCards(this.catalogCards.toArray());
    this.catalogCards.changes
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((cards: QueryList<ElementRef<HTMLElement>>) => {
        void this.animateCatalogCards(cards.toArray());
      });

    this.bindPreviewStage(this.previewStages.first?.nativeElement ?? null);
    this.previewStages.changes
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((stages: QueryList<ElementRef<HTMLElement>>) => {
        this.bindPreviewStage(stages.first?.nativeElement ?? null);
      });
  }

  @HostListener('window:scroll')
  protected updateHeroTypography(): void {
    const progress = Math.min(window.scrollY / 320, 1);
    this.heroScrollProgress.set(progress);
  }

  protected async chooseCategory(categoryId: number): Promise<void> {
    await this.shop.selectCategory(categoryId);
  }

  protected async chooseProduct(productId: number): Promise<void> {
    await this.shop.selectProduct(productId);
    this.activeStep.set(1);
    this.scrollTo('configurator');
  }

  protected updateNumber(field: 'widthMm' | 'lengthMm' | 'qty', value: string): void {
    const parsed = Number.parseInt(value, 10);

    this.form.update((current) => ({
      ...current,
      [field]:
        Number.isNaN(parsed)
          ? field === 'qty'
            ? 1
            : null
          : field === 'qty'
            ? Math.min(Math.max(parsed, 1), 99)
            : parsed
    }));
  }

  protected updateOption(field: 'edgeId' | 'facetId' | 'temperingId', value: string): void {
    this.form.update((current) => ({
      ...current,
      [field]: value ? Number.parseInt(value, 10) : null
    }));
  }

  protected adjustQty(delta: number): void {
    this.form.update((current) => ({
      ...current,
      qty: Math.min(Math.max(current.qty + delta, 1), 99)
    }));
  }

  protected applyPreset(preset: 'min' | 'balanced' | 'max'): void {
    const product = this.selectedProduct();

    if (
      product?.min_width == null ||
      product.min_length == null ||
      product.max_width == null ||
      product.max_length == null
    ) {
      return;
    }

    const nextWidth =
      preset === 'min'
        ? product.min_width
        : preset === 'max'
          ? product.max_width
          : Math.round((product.min_width + product.max_width) / 2);
    const nextLength =
      preset === 'min'
        ? product.min_length
        : preset === 'max'
          ? product.max_length
          : Math.round((product.min_length + product.max_length) / 2);

    this.form.update((current) => ({
      ...current,
      widthMm: nextWidth,
      lengthMm: nextLength
    }));
  }

  protected setStep(stepId: number): void {
    if (!this.canOpenStep(stepId)) {
      return;
    }

    this.activeStep.set(stepId);
  }

  protected nextStep(): void {
    if (this.activeStep() === 1 && !this.isSizeStepValid()) {
      return;
    }

    this.activeStep.update((value) => Math.min(value + 1, this.steps.length));
  }

  protected previousStep(): void {
    this.activeStep.update((value) => Math.max(value - 1, 1));
  }

  protected canOpenStep(stepId: number): boolean {
    return stepId === 1 || this.isSizeStepValid();
  }

  protected isStepComplete(stepId: number): boolean {
    if (stepId === 1) {
      return this.isSizeStepValid();
    }

    return this.activeStep() > stepId;
  }

  protected materialTone(product: Product | null): string {
    return product?.thickness_mm != null ? `${product.thickness_mm} мм` : 'Материал';
  }

  protected materialAtmosphere(product: Product | null): string {
    return this.productRangeCompact(product) ?? 'Размеры уточняются';
  }

  protected productPhotoUrl(product: Product | null): string | null {
    const value = product?.image_url?.trim();
    return value ? value : null;
  }

  protected materialSceneStyle(product: Product | null): string {
    const theme = this.materialTheme(product);
    return `linear-gradient(180deg, rgba(16, 19, 23, 0.05), rgba(16, 19, 23, 0.18)), radial-gradient(circle at 18% 18%, rgba(255, 255, 255, 0.58), transparent 26%), linear-gradient(135deg, ${theme.previewTint}, rgba(255, 255, 255, 0.08)), url('/img/back_main.png') center/cover no-repeat`;
  }

  protected materialImageUrl(product: Product | null): string {
    return this.productPhotoUrl(product) ?? 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22/%3E';
  }

  protected materialImagePosition(_product: Product | null): string {
    return 'center center';
  }

  protected materialCardOverlayStyle(product: Product | null): string {
    const theme = this.materialTheme(product);
    return `linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(16, 19, 23, 0.18)), linear-gradient(135deg, ${theme.previewTint}, rgba(255, 255, 255, 0.12))`;
  }

  protected materialSwatchStyle(product: Product | null): string {
    const theme = this.materialTheme(product);
    const photoUrl = this.productPhotoUrl(product);

    if (photoUrl == null) {
      return theme.surface;
    }

    return `linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(16, 19, 23, 0.18)), url("${photoUrl}") center/cover no-repeat`;
  }

  protected materialAccent(product: Product | null): string {
    return this.materialTheme(product).accent;
  }

  protected edgeOptionText(edge: ProductConfig['edges'][number] | null): string {
    if (edge == null) {
      return 'Торец без шлифовки и полировки.';
    }

    const finish =
      edge.edge_type === 'transparent'
        ? 'Прозрачная полировка оставляет чистый блеск кромки.'
        : 'Матовая шлифовка делает торец мягче и спокойнее.';
    const shape =
      edge.edge_shape === 'curved'
        ? 'Подходит для радиусных и скругленных форм.'
        : 'Лучше читается на прямой геометрии.';

    return `${finish} ${shape}`;
  }

  protected facetOptionText(facet: ProductConfig['facets'][number] | null): string {
    if (facet == null) {
      return 'Плоскость без светового скоса по краю.';
    }

    const shape =
      facet.shape === 'curved'
        ? 'Мягкий скос повторяет округлые формы.'
        : 'Прямой скос собирает четкую световую рамку.';

    return `${shape} Ширина фаски ${facet.facet_width_mm} мм.`;
  }

  protected temperingOptionText(tempering: ProductConfig['temperings'][number] | null): string {
    if (tempering == null) {
      return 'Базовое исполнение без термообработки.';
    }

    const thickness =
      tempering.thickness_mm != null ? ` Под стекло ${tempering.thickness_mm} мм.` : '';

    return `Термообработка повышает стойкость к удару и перепадам температуры.${thickness}`;
  }

  protected edgeSwatchStyle(edge: ProductConfig['edges'][number] | null): string {
    if (edge == null) {
      return 'radial-gradient(circle at 22% 24%, rgba(255,255,255,0.92), transparent 24%), linear-gradient(160deg, rgba(255,255,255,0.96), rgba(224,232,241,0.84))';
    }

    const edgeBand =
      edge.edge_type === 'transparent'
        ? 'linear-gradient(90deg, rgba(255,255,255,0.94) 0 10%, transparent 10% 90%, rgba(255,255,255,0.94) 90% 100%), linear-gradient(180deg, rgba(255,255,255,0.94) 0 14%, transparent 14% 86%, rgba(255,255,255,0.94) 86% 100%)'
        : 'linear-gradient(90deg, rgba(214,220,228,0.94) 0 12%, transparent 12% 88%, rgba(214,220,228,0.94) 88% 100%), linear-gradient(180deg, rgba(214,220,228,0.94) 0 16%, transparent 16% 84%, rgba(214,220,228,0.94) 84% 100%)';
    const shapeAccent =
      edge.edge_shape === 'curved'
        ? 'radial-gradient(circle at 18% 22%, rgba(255,255,255,0.88), transparent 20%), radial-gradient(circle at 82% 78%, rgba(255,255,255,0.7), transparent 18%)'
        : 'linear-gradient(135deg, rgba(255,255,255,0.45), transparent 42%)';

    return `${edgeBand}, ${shapeAccent}, linear-gradient(160deg, rgba(255,255,255,0.96), rgba(220,231,241,0.84))`;
  }

  protected facetSwatchStyle(facet: ProductConfig['facets'][number] | null): string {
    if (facet == null) {
      return 'radial-gradient(circle at 22% 24%, rgba(255,255,255,0.92), transparent 24%), linear-gradient(160deg, rgba(255,255,255,0.96), rgba(230,236,243,0.82))';
    }

    const bevel =
      facet.shape === 'curved'
        ? 'radial-gradient(circle at 20% 24%, rgba(255,255,255,0.92), transparent 18%), radial-gradient(circle at 80% 24%, rgba(255,255,255,0.78), transparent 16%), radial-gradient(circle at 20% 76%, rgba(255,255,255,0.78), transparent 16%), radial-gradient(circle at 80% 76%, rgba(255,255,255,0.7), transparent 16%), linear-gradient(180deg, transparent 0 18%, rgba(203,218,232,0.78) 18% 24%, transparent 24% 76%, rgba(203,218,232,0.78) 76% 82%, transparent 82%)'
        : 'linear-gradient(135deg, transparent 0 15%, rgba(255,255,255,0.9) 15% 20%, transparent 20% 80%, rgba(255,255,255,0.9) 80% 85%, transparent 85%), linear-gradient(45deg, transparent 0 15%, rgba(203,218,232,0.82) 15% 21%, transparent 21% 79%, rgba(203,218,232,0.82) 79% 85%, transparent 85%)';

    return `${bevel}, linear-gradient(160deg, rgba(255,255,255,0.96), rgba(224,233,242,0.84))`;
  }

  protected temperingSwatchStyle(tempering: ProductConfig['temperings'][number] | null): string {
    if (tempering == null) {
      return 'radial-gradient(circle at 22% 24%, rgba(255,255,255,0.92), transparent 24%), linear-gradient(160deg, rgba(255,255,255,0.96), rgba(231,237,243,0.82))';
    }

    const tint =
      tempering.thickness_mm != null && tempering.thickness_mm >= 6
        ? 'rgba(180,210,234,0.84)'
        : 'rgba(208,224,238,0.76)';

    return `repeating-linear-gradient(135deg, rgba(144,176,202,0.18) 0 8px, rgba(255,255,255,0) 8px 16px), radial-gradient(circle at 22% 24%, rgba(255,255,255,0.92), transparent 24%), linear-gradient(160deg, rgba(255,255,255,0.96), ${tint})`;
  }

  protected optionValue(id: number): string {
    return String(id);
  }

  protected selectedOptionValue(id: number | null): string {
    return id == null ? '' : String(id);
  }

  protected edgeSelectionSummary(): string {
    const edge = this.selectedEdge();

    if (edge == null) {
      return 'Чистый край без дополнительной обработки.';
    }

    const thickness = edge.thickness_mm != null ? `${edge.thickness_mm} мм` : 'под выбранное полотно';
    return `${formatEdgeLabel(edge)} · ${thickness} · ${formatPrice(edge.price)}`;
  }

  protected facetSelectionSummary(): string {
    const facet = this.selectedFacet();

    if (facet == null) {
      return 'Без фацета, чтобы оставить плоскость максимально спокойной.';
    }

    const geometry = facet.shape === 'curved' ? 'мягкая форма' : 'прямая линия';
    return `${formatFacetLabel(facet)} · ${geometry} · ${formatPrice(facet.price)}`;
  }

  protected temperingSelectionSummary(): string {
    const tempering = this.selectedTempering();

    if (tempering == null) {
      return 'Базовое исполнение без закалки.';
    }

    const thickness =
      tempering.thickness_mm != null ? `${tempering.thickness_mm} мм` : 'по выбранному формату';
    return `${formatTemperingLabel(tempering)} · ${thickness} · ${formatPrice(tempering.price)}`;
  }

  protected async addToCart(): Promise<void> {
    const config = this.shop.selectedConfig();
    const currentUser = this.user();

    if (config == null) {
      return;
    }

    if (currentUser == null) {
      await this.router.navigate(['/login'], { queryParams: { next: '/' } });
      return;
    }

    if (
      config.product.min_width == null ||
      config.product.min_length == null ||
      config.product.max_width == null ||
      config.product.max_length == null
    ) {
      this.shop.actionMessage.set(
        'Для этого материала лучше оставить запрос менеджеру. Онлайн-калькулятор по нему пока не включен.'
      );
      return;
    }

    if (this.dimensionsWarning()) {
      this.shop.actionMessage.set(this.dimensionsWarning());
      return;
    }

    const values = this.form();
    const isAdded = await this.shop.addToCart({
      product_id: config.product.id,
      width_mm: values.widthMm,
      length_mm: values.lengthMm,
      qty: values.qty,
      edge_id: values.edgeId,
      facet_id: values.facetId,
      tempering_id: values.temperingId
    });

    if (isAdded) {
      this.scrollTo('cart');
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

  protected productName(productId: number): string {
    return this.shop.getProduct(productId)?.name ?? `Материал #${productId}`;
  }

  protected productMeta(productId: number): string {
    const product = this.shop.getProduct(productId);

    if (product == null) {
      return 'Размер и параметры уточняются';
    }

    const parts = [];

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
      return 'Параметры обновляются';
    }

    const parts = [];

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

  protected productRangeLabel(): string {
    const product = this.selectedProduct();

    if (product == null) {
      return '';
    }

    if (
      product.min_width == null ||
      product.min_length == null ||
      product.max_width == null ||
      product.max_length == null
    ) {
      return 'Размеры по этому материалу лучше уточнить вручную.';
    }

    return `От ${product.min_width}×${product.min_length} до ${product.max_width}×${product.max_length} мм`;
  }

  protected scrollTo(id: string): void {
    document.getElementById(id)?.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });
  }

  private productRangeCompact(product: Product | null): string | null {
    if (product?.max_width != null && product.max_length != null) {
      return `до ${product.max_width} x ${product.max_length} мм`;
    }

    if (product?.max_width != null) {
      return `до ${product.max_width} мм по ширине`;
    }

    if (product?.max_length != null) {
      return `до ${product.max_length} мм по длине`;
    }

    return null;
  }

  private materialTheme(product: Product | null): MaterialTheme {
    if (product == null) {
      return MATERIAL_THEMES.crystal;
    }

    const name = product.name.toLowerCase();

    if (/сатин\s*светл|светл(?:ый|ое|ая)?\s*сатин|сатин\s*ультра|сатин\s*бел/.test(name)) {
      return MATERIAL_THEMES.satinLight;
    }

    if (/зелен|green/.test(name)) {
      return MATERIAL_THEMES.green;
    }

    if (/золот|gold/.test(name)) {
      return MATERIAL_THEMES.gold;
    }

    if (/бронз|коричнев/.test(name)) {
      return MATERIAL_THEMES.bronze;
    }

    if (/графит|серый|тёмн|темн|чёрн|черн/.test(name)) {
      return MATERIAL_THEMES.graphite;
    }

    if (/зеркал|серебр|хром/.test(name)) {
      return MATERIAL_THEMES.silver;
    }

    if (/тонир|дымч|smoke|smoked/.test(name)) {
      return MATERIAL_THEMES.tinted;
    }

    if (/сатин|матов/.test(name)) {
      return MATERIAL_THEMES.satinLight;
    }

    if (/прозрач|осветл|матов|бел/.test(name)) {
      return MATERIAL_THEMES.crystal;
    }

    return MATERIAL_THEMES.crystal;
  }

  private bindPreviewStage(element: HTMLElement | null): void {
    this.previewResizeObserver?.disconnect();

    if (element == null) {
      this.previewViewport.set({ width: 0, height: 0 });
      return;
    }

    const syncViewport = () => {
      const rect = element.getBoundingClientRect();
      const width = Math.round(rect.width);
      const height = Math.round(rect.height);
      const current = this.previewViewport();

      if (current.width !== width || current.height !== height) {
        this.previewViewport.set({ width, height });
      }
    };

    syncViewport();
    this.previewResizeObserver = new ResizeObserver(() => syncViewport());
    this.previewResizeObserver.observe(element);
    this.destroyRef.onDestroy(() => this.previewResizeObserver?.disconnect());
  }

  private async animateCatalogCards(cards: ElementRef<HTMLElement>[]): Promise<void> {
    const elements = cards.map((card) => card.nativeElement);

    if (!elements.length) {
      return;
    }

    const { default: gsap } = await this.loadGsap();

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      gsap.set(elements, { clearProps: 'all', autoAlpha: 1, y: 0, scale: 1 });
      return;
    }

    gsap.killTweensOf(elements);
    gsap.fromTo(
      elements,
      { autoAlpha: 0, y: 36, scale: 0.985 },
      {
        autoAlpha: 1,
        y: 0,
        scale: 1,
        duration: 0.82,
        ease: 'power3.out',
        stagger: 0.1,
        clearProps: 'opacity,visibility,transform'
      }
    );
  }

  private loadGsap(): Promise<typeof import('gsap')> {
    this.gsapModulePromise ??= import('gsap');
    return this.gsapModulePromise;
  }
}
