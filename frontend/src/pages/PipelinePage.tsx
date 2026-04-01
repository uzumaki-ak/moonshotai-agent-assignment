// this file renders pipeline control page for scrape and analyze jobs
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchArtifactPreview, fetchJobArtifacts, fetchJobs, startAnalyzeJob, startScrapeJob } from "../api/dashboard";
import { EmptyState } from "../components/EmptyState";

const defaultBrands = ["Safari", "Skybags", "American Tourister", "VIP"];

function summarizeJob(job: { result: Record<string, unknown> | null; error_message: string | null }) {
  // this helper builds readable note text from job payload
  if (job.error_message) return job.error_message;
  const result = job.result ?? {};
  if (typeof result.reviews_saved === "number") {
    return `products ${result.products_saved ?? 0}, reviews ${result.reviews_saved}`;
  }
  if (typeof result.metrics_rows === "number") {
    return `metrics ${result.metrics_rows}, insights ${result.insights_created ?? 0}`;
  }
  return "ok";
}

export function PipelinePage() {
  // this page allows user to trigger and monitor pipeline jobs
  const [brandsInput, setBrandsInput] = useState(defaultBrands.join(", "));
  const [productsPerBrand, setProductsPerBrand] = useState(10);
  const [reviewsPerProduct, setReviewsPerProduct] = useState(50);
  const [selectedScrapeJobId, setSelectedScrapeJobId] = useState<string>("");
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [selectedArtifactKey, setSelectedArtifactKey] = useState<string>("");
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

  const artifactsQuery = useQuery({
    queryKey: ["job-artifacts", selectedJobId],
    queryFn: () => fetchJobArtifacts(selectedJobId),
    enabled: !!selectedJobId,
  });

  const artifactPreviewQuery = useQuery({
    queryKey: ["artifact-preview", selectedJobId, selectedArtifactKey],
    queryFn: () => fetchArtifactPreview(selectedJobId, selectedArtifactKey, 25),
    enabled: !!selectedJobId && !!selectedArtifactKey,
  });

  const parsedBrands = useMemo(() => {
    return brandsInput
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }, [brandsInput]);

  const completedScrapeJobs = useMemo(() => {
    return (jobsQuery.data ?? []).filter((job) => job.job_type === "scrape" && job.status === "completed");
  }, [jobsQuery.data]);

  useEffect(() => {
    // this effect auto selects latest completed scrape job for analysis
    if (!selectedScrapeJobId && completedScrapeJobs.length) {
      setSelectedScrapeJobId(completedScrapeJobs[0].id);
    }
  }, [completedScrapeJobs, selectedScrapeJobId]);

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
    // this handler starts analysis for selected scrape run
    analyzeMutation.mutate({
      force_recompute: true,
      source_scrape_job_id: selectedScrapeJobId || null,
    });
  };

  const artifactItems = useMemo(() => {
    const files = artifactsQuery.data?.artifacts?.files;
    if (!Array.isArray(files)) return [];
    return files
      .map((row) => {
        const brand = typeof row.brand === "string" ? row.brand : null;
        const key = typeof row.key === "string" ? row.key : brand;
        if (!key) return null;
        const label = brand ?? key.replace(/_/g, " ");
        return { key, label };
      })
      .filter(Boolean) as Array<{ key: string; label: string }>;
  }, [artifactsQuery.data]);

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

          <label className="inline-control">
            analyze source run
            <select value={selectedScrapeJobId} onChange={(event) => setSelectedScrapeJobId(event.target.value)}>
              <option value="">latest completed scrape</option>
              {completedScrapeJobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.id.slice(0, 8)} | {new Date(job.started_at).toLocaleString()}
                </option>
              ))}
            </select>
          </label>

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
                  <th>data</th>
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
                    <td>{summarizeJob(job).slice(0, 90)}</td>
                    <td>
                      <button
                        type="button"
                        className="tiny-btn"
                        onClick={() => {
                          setSelectedJobId(job.id);
                          setSelectedArtifactKey("");
                        }}
                      >
                        view
                      </button>
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
          <h3>job data preview</h3>
        </div>

        {!selectedJobId ? (
          <EmptyState title="select a job" subtitle="click view in job table to inspect raw or cleaned artifacts" />
        ) : artifactsQuery.isLoading ? (
          <div className="loader">loading artifacts</div>
        ) : (
          <>
            {artifactsQuery.data?.artifacts?.warnings?.length ? (
              <div className="warning-box">
                {artifactsQuery.data.artifacts.warnings.map((item) => (
                  <p key={item}>{item}</p>
                ))}
              </div>
            ) : null}

            {artifactItems.length ? (
              <div className="chip-list">
                {artifactItems.map((item) => (
                  <button
                    type="button"
                    key={item.key}
                    className={selectedArtifactKey === item.key ? "chip active" : "chip"}
                    onClick={() => setSelectedArtifactKey(item.key)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            ) : (
              <EmptyState title="no artifact files" subtitle="this job has no stored file outputs" />
            )}

            {selectedArtifactKey ? (
              artifactPreviewQuery.isLoading ? (
                <div className="loader">loading preview</div>
              ) : artifactPreviewQuery.data?.rows?.length ? (
                <div className="table-wrap artifact-table">
                  <table>
                    <thead>
                      <tr>
                        {Object.keys(artifactPreviewQuery.data.rows[0]).map((col) => (
                          <th key={col}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {artifactPreviewQuery.data.rows.map((row, index) => (
                        <tr key={`${selectedArtifactKey}-${index}`}>
                          {Object.entries(row).map(([col, value]) => (
                            <td key={`${col}-${index}`}>
                              {typeof value === "string" && value.startsWith("http") ? (
                                <a href={value} target="_blank" rel="noreferrer" className="ghost-link">
                                  open link
                                </a>
                              ) : (
                                String(value ?? "")
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState title="no rows in artifact" subtitle="file exists but no rows were found in preview" />
              )
            ) : null}
          </>
        )}
      </div>
    </section>
  );
}
