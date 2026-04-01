// this file renders pipeline control page for scrape and analyze jobs
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchJobs, startAnalyzeJob, startScrapeJob } from "../api/dashboard";
import { EmptyState } from "../components/EmptyState";

const defaultBrands = ["Safari", "Skybags", "American Tourister", "VIP"];

export function PipelinePage() {
  // this page allows user to trigger and monitor pipeline jobs
  const [brandsInput, setBrandsInput] = useState(defaultBrands.join(", "));
  const [productsPerBrand, setProductsPerBrand] = useState(10);
  const [reviewsPerProduct, setReviewsPerProduct] = useState(50);
  const queryClient = useQueryClient();

  const jobsQuery = useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
    refetchInterval: 5000,
  });

  const scrapeMutation = useMutation({
    mutationFn: startScrapeJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: startAnalyzeJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const parsedBrands = useMemo(() => {
    return brandsInput
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }, [brandsInput]);

  const createScrape = () => {
    // this handler starts scrape job with current controls
    if (!parsedBrands.length) return;
    scrapeMutation.mutate({
      brands: parsedBrands,
      products_per_brand: productsPerBrand,
      reviews_per_product: reviewsPerProduct,
    });
  };

  const createAnalyze = () => {
    // this handler starts analysis and insight generation
    analyzeMutation.mutate({ force_recompute: true });
  };

  return (
    <section className="page-grid">
      <div className="card">
        <div className="card-head">
          <h3>run scrape job</h3>
        </div>

        <div className="form-grid">
          <label>
            brands
            <input value={brandsInput} onChange={(event) => setBrandsInput(event.target.value)} placeholder="Safari, Skybags, American Tourister, VIP" />
          </label>

          <label>
            products per brand
            <input
              type="number"
              value={productsPerBrand}
              min={2}
              max={20}
              onChange={(event) => setProductsPerBrand(Number(event.target.value))}
            />
          </label>

          <label>
            reviews per product
            <input
              type="number"
              value={reviewsPerProduct}
              min={10}
              max={120}
              onChange={(event) => setReviewsPerProduct(Number(event.target.value))}
            />
          </label>
        </div>

        <div className="button-row">
          <button type="button" onClick={createScrape} disabled={scrapeMutation.isPending || !parsedBrands.length}>
            {scrapeMutation.isPending ? "starting" : "start scrape"}
          </button>
          <button type="button" className="secondary" onClick={createAnalyze} disabled={analyzeMutation.isPending}>
            {analyzeMutation.isPending ? "starting" : "run analysis"}
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h3>job status</h3>
        </div>

        {!jobsQuery.data?.length ? (
          <EmptyState title="no jobs yet" subtitle="create scrape job to begin data collection" />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>id</th>
                  <th>type</th>
                  <th>status</th>
                  <th>started</th>
                  <th>completed</th>
                  <th>notes</th>
                </tr>
              </thead>
              <tbody>
                {jobsQuery.data.map((job) => (
                  <tr key={job.id}>
                    <td>{job.id.slice(0, 8)}</td>
                    <td>{job.job_type}</td>
                    <td>
                      <span className={`pill ${job.status === "completed" ? "good" : job.status === "failed" ? "bad" : "neutral"}`}>{job.status}</span>
                    </td>
                    <td>{new Date(job.started_at).toLocaleString()}</td>
                    <td>{job.completed_at ? new Date(job.completed_at).toLocaleString() : "running"}</td>
                    <td>{job.error_message ? job.error_message.slice(0, 80) : "ok"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
