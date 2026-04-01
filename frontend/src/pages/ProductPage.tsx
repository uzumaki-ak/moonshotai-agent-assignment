// this file renders product drilldown route
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { fetchProductDetail, fetchReviews } from "../api/dashboard";
import { EmptyState } from "../components/EmptyState";
import { SentimentPill } from "../components/SentimentPill";
import { StatCard } from "../components/StatCard";

function formatInr(value: number | null) {
  // this helper formats inr values
  if (value === null) return "na";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}

export function ProductPage() {
  // this page gives product level pricing and review themes
  const params = useParams();
  const productId = Number(params.productId);

  const detailQuery = useQuery({
    queryKey: ["product-detail", productId],
    queryFn: () => fetchProductDetail(productId),
    enabled: Number.isFinite(productId),
  });

  const reviewsQuery = useQuery({
    queryKey: ["product-reviews", productId],
    queryFn: () => fetchReviews({ product_id: productId, limit: 80 }),
    enabled: Number.isFinite(productId),
  });

  const detail = detailQuery.data;
  const reviews = reviewsQuery.data ?? [];

  if (!detail) {
    return <EmptyState title="product not found" subtitle="open product from brand page" />;
  }

  return (
    <section className="page-grid">
      <div className="stat-grid">
        <StatCard label="brand" value={detail.brand_name} />
        <StatCard label="asin" value={detail.asin} />
        <StatCard label="price" value={formatInr(detail.price)} />
        <StatCard label="list price" value={formatInr(detail.list_price)} />
        <StatCard label="discount" value={`${detail.discount_percent?.toFixed(2) ?? "na"}%`} />
        <StatCard label="sentiment" value={detail.sentiment_score?.toFixed(3) ?? "na"} />
      </div>

      <div className="card banner">
        <h3>{detail.title}</h3>
        <p>{detail.review_synthesis}</p>
        <a href={detail.url} target="_blank" rel="noreferrer" className="ghost-link">
          open product source page
        </a>
      </div>

      <div className="two-col">
        <div className="card">
          <div className="card-head">
            <h3>top praise themes</h3>
          </div>
          <div className="chip-list">
            {detail.top_praise.length ? detail.top_praise.map((item) => <span className="chip active" key={item}>{item}</span>) : <span className="chip">none</span>}
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <h3>top complaint themes</h3>
          </div>
          <div className="chip-list">
            {detail.top_complaints.length ? detail.top_complaints.map((item) => <span className="chip" key={item}>{item}</span>) : <span className="chip">none</span>}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h3>review sample</h3>
        </div>
        {!reviews.length ? (
          <EmptyState title="no review rows" subtitle="scrape reviews for this product" />
        ) : (
          <div className="review-list">
            {reviews.slice(0, 20).map((review) => (
              <article key={review.id} className="review-item">
                <div className="review-head">
                  <h4>{review.title ?? "review"}</h4>
                  <SentimentPill score={review.sentiment_score} />
                </div>
                <p>{review.content}</p>
                {review.source_url ? (
                  <a href={review.source_url} target="_blank" rel="noreferrer" className="ghost-link">
                    open source review
                  </a>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
