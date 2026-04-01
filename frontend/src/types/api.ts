// this file keeps frontend types aligned with backend responses
export type OverviewResponse = {
  stats: {
    total_brands: number;
    total_products: number;
    total_reviews: number;
    avg_sentiment: number | null;
    avg_price: number | null;
  };
  price_bands: Array<{ band: string; product_count: number }>;
  sentiment_trend: Array<{ date: string; sentiment: number }>;
};

export type BrandComparisonRow = {
  brand_id: number;
  brand_name: string;
  avg_price: number | null;
  avg_discount_pct: number | null;
  avg_rating: number | null;
  review_count: number;
  sentiment_score: number | null;
  premium_index: number | null;
  value_for_money: number | null;
  top_praise: string[];
  top_complaints: string[];
};

export type Brand = {
  id: number;
  name: string;
  slug: string;
};

export type BrandDetail = Brand & {
  product_count: number;
  review_count: number;
  avg_price: number | null;
  avg_discount_pct: number | null;
  avg_rating: number | null;
  sentiment_score: number | null;
};

export type Product = {
  id: number;
  brand_id: number;
  brand_name: string;
  asin: string;
  title: string;
  url: string;
  category: string | null;
  size: string | null;
  price: number | null;
  list_price: number | null;
  discount_percent: number | null;
  rating: number | null;
  review_count: number | null;
};

export type ProductDetail = Product & {
  sentiment_score: number | null;
  top_praise: string[];
  top_complaints: string[];
  review_synthesis: string;
};

export type Review = {
  id: number;
  product_id: number;
  rating: number | null;
  sentiment_score: number | null;
  sentiment_label: "positive" | "negative" | "neutral" | null;
  title: string | null;
  content: string;
  review_date: string | null;
  verified_purchase: boolean | null;
  helpful_votes: number | null;
  source_url: string | null;
};

export type Insight = {
  id: number;
  insight_type: string;
  title: string;
  body: string;
  confidence: number | null;
  payload: Record<string, unknown> | null;
};

export type PipelineJob = {
  id: string;
  job_type: string;
  status: "pending" | "running" | "completed" | "failed";
  params: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
};

export type JobArtifacts = {
  job_id: string;
  artifacts: {
    raw_dir?: string;
    cleaned_dir?: string;
    files?: Array<Record<string, unknown>>;
    warnings?: string[];
    row_counts?: Record<string, number>;
  };
  message?: string;
};

export type ArtifactPreview = {
  job_id: string;
  artifact_key: string;
  path: string;
  row_count: number;
  rows: Array<Record<string, unknown>>;
};
