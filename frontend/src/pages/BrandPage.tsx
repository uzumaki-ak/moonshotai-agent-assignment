// this file renders brand specific drilldown page
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { fetchBrandDetail, fetchProducts, fetchReviews } from "../api/dashboard";
import { EmptyState } from "../components/EmptyState";
import { SentimentPill } from "../components/SentimentPill";
import { StatCard } from "../components/StatCard";

function formatInr(value: number | null) {
  // this helper formats inr values
  if (value === null) return "na";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}

export function BrandPage() {
  // this page shows one brand products and review snippets
  const params = useParams();
  const brandId = Number(params.brandId);
  const [ratingMin, setRatingMin] = useState(0);

  const detailQuery = useQuery({ queryKey: ["brand-detail", brandId], queryFn: () => fetchBrandDetail(brandId), enabled: Number.isFinite(brandId) });
  const productsQuery = useQuery({
    queryKey: ["brand-products", brandId, ratingMin],
    queryFn: () => fetchProducts({ brand_id: brandId, rating_min: ratingMin || undefined, limit: 100 }),
    enabled: Number.isFinite(brandId),
  });
  const reviewsQuery = useQuery({
    queryKey: ["brand-reviews", brandId],
    queryFn: () => fetchReviews({ brand_id: brandId, limit: 25 }),
    enabled: Number.isFinite(brandId),
  });

  const detail = detailQuery.data;
  const products = productsQuery.data ?? [];
  const reviews = reviewsQuery.data ?? [];

  const complaintShare = useMemo(() => {
    if (!reviews.length) return null;
    const negatives = reviews.filter((row) => row.sentiment_label === "negative").length;
    return (negatives * 100) / reviews.length;
  }, [reviews]);

  if (!detail) {
    return <EmptyState title="brand not found" subtitle="choose a brand from compare page" />;
  }

  return (
    <section className="page-grid">
      <div className="stat-grid">
        <StatCard label="brand" value={detail.name} />
        <StatCard label="products" value={String(detail.product_count)} />
        <StatCard label="reviews" value={String(detail.review_count)} />
        <StatCard label="avg price" value={formatInr(detail.avg_price)} />
        <StatCard label="avg rating" value={detail.avg_rating?.toFixed(2) ?? "na"} />
        <StatCard label="sentiment" value={detail.sentiment_score?.toFixed(3) ?? "na"} />
      </div>

      <div className="card banner">
        <h3>complaint share</h3>
        <p>{complaintShare === null ? "no review sample yet" : `${complaintShare.toFixed(1)}% of sampled reviews look negative`}</p>
      </div>

      <div className="card">
        <div className="card-head">
          <h3>product list</h3>
          <div className="control-row">
            <label htmlFor="ratingMin">min rating</label>
            <select id="ratingMin" value={ratingMin} onChange={(event) => setRatingMin(Number(event.target.value))}>
              <option value={0}>all</option>
              <option value={3}>3+</option>
              <option value={3.5}>3.5+</option>
              <option value={4}>4+</option>
            </select>
          </div>
        </div>

        {!products.length ? (
          <EmptyState title="no products" subtitle="run scrape for this brand" />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>product</th>
                  <th>price</th>
                  <th>discount</th>
                  <th>rating</th>
                  <th>reviews</th>
                  <th>open</th>
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.id}>
                    <td>{product.title}</td>
                    <td>{formatInr(product.price)}</td>
                    <td>{product.discount_percent?.toFixed(1) ?? "na"}%</td>
                    <td>{product.rating?.toFixed(2) ?? "na"}</td>
                    <td>{product.review_count ?? 0}</td>
                    <td>
                      <Link to={`/products/${product.id}`} className="ghost-link">
                        details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-head">
          <h3>latest review sample</h3>
        </div>
        {!reviews.length ? (
          <EmptyState title="no reviews yet" subtitle="scrape reviews for this brand" />
        ) : (
          <div className="review-list">
            {reviews.slice(0, 10).map((review) => (
              <article key={review.id} className="review-item">
                <div className="review-head">
                  <h4>{review.title ?? "review"}</h4>
                  <SentimentPill score={review.sentiment_score} />
                </div>
                <p>{review.content}</p>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
