// this file defines api helpers for all dashboard pages
import { apiClient } from "./client";
import type {
  Brand,
  BrandComparisonRow,
  BrandDetail,
  Insight,
  OverviewResponse,
  PipelineJob,
  Product,
  ProductDetail,
  Review,
} from "../types/api";

export async function fetchOverview(): Promise<OverviewResponse> {
  // this function loads overview cards and trend data
  const { data } = await apiClient.get<OverviewResponse>("/overview");
  return data;
}

export async function fetchBrands(): Promise<Brand[]> {
  // this function loads brand list for filters and navigation
  const { data } = await apiClient.get<Brand[]>("/brands");
  return data;
}

export async function fetchBrandComparison(brandIds: number[] = []): Promise<BrandComparisonRow[]> {
  // this function loads side by side brand benchmarks
  const params = new URLSearchParams();
  brandIds.forEach((id) => params.append("brand_ids", String(id)));

  const { data } = await apiClient.get<BrandComparisonRow[]>(`/brands/compare?${params.toString()}`);
  return data;
}

export async function fetchBrandDetail(brandId: number): Promise<BrandDetail> {
  // this function loads one brand detail summary
  const { data } = await apiClient.get<BrandDetail>(`/brands/${brandId}`);
  return data;
}

export async function fetchProducts(params?: {
  brand_id?: number;
  price_min?: number;
  price_max?: number;
  rating_min?: number;
  limit?: number;
}): Promise<Product[]> {
  // this function loads product list with optional filters
  const { data } = await apiClient.get<Product[]>("/products", { params });
  return data;
}

export async function fetchProductDetail(productId: number): Promise<ProductDetail> {
  // this function loads one product drilldown payload
  const { data } = await apiClient.get<ProductDetail>(`/products/${productId}`);
  return data;
}

export async function fetchReviews(params?: {
  product_id?: number;
  brand_id?: number;
  sentiment?: string;
  rating_min?: number;
  limit?: number;
}): Promise<Review[]> {
  // this function loads review list with active filters
  const { data } = await apiClient.get<Review[]>("/reviews", { params });
  return data;
}

export async function fetchInsights(): Promise<Insight[]> {
  // this function loads agent insight cards
  const { data } = await apiClient.get<Insight[]>("/insights/agent");
  return data;
}

export async function fetchJobs(): Promise<PipelineJob[]> {
  // this function loads recent scrape and analyze jobs
  const { data } = await apiClient.get<PipelineJob[]>("/jobs");
  return data;
}

export async function startScrapeJob(payload: {
  brands: string[];
  products_per_brand: number;
  reviews_per_product: number;
}): Promise<PipelineJob> {
  // this function starts scraper job
  const { data } = await apiClient.post<PipelineJob>("/jobs/scrape", payload);
  return data;
}

export async function startAnalyzeJob(payload: { force_recompute: boolean }): Promise<PipelineJob> {
  // this function starts analysis job
  const { data } = await apiClient.post<PipelineJob>("/jobs/analyze", payload);
  return data;
}
