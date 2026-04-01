// this file renders pipeline control page for scrape and analyze jobs
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { deleteJob, fetchArtifactPreview, fetchJobArtifacts, fetchJobs, startAnalyzeJob, startScrapeJob } from "../api/dashboard";
import { EmptyState } from "../components/EmptyState";
import type { PipelineJob } from "../types/api";

const defaultBrands = ["Safari", "Skybags", "American Tourister", "VIP"];

function asNumber(value: unknown): number | null {
  // this helper normalizes api values into numbers
  if (typeof value === "number") return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function asStringArray(value: unknown): string[] {
  // this helper safely reads string arrays from job payloads
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function summarizeJob(job: PipelineJob) {
  // this helper builds readable note text from job payload
  if (job.error_message) return job.error_message;
  const result = job.result ?? {};
  const params = job.params ?? {};
  if (typeof result.reviews_saved === "number") {
    const brands = asStringArray(params.brands).length;
    return `brands ${brands}, products ${result.products_saved ?? 0}, reviews ${result.reviews_saved}`;
  }
  if (typeof result.metrics_rows === "number") {
    const hydrate = (result.hydrate_summary as Record<string, unknown> | undefined) ?? {};
    const source = typeof result.source_scrape_job_id === "string" ? result.source_scrape_job_id.slice(0, 8) : "latest";
    const loadedBrands = asStringArray(hydrate.brands).length;
    const loadedProducts = asNumber(hydrate.products_loaded) ?? 0;
    const loadedReviews = asNumber(hydrate.reviews_loaded) ?? 0;
    return `source ${source}, brands ${loadedBrands}, products ${loadedProducts}, reviews ${loadedReviews}`;
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
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      setSelectedJobId(job.id);
      setSelectedArtifactKey("");
      setSelectedScrapeJobId("");
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: startAnalyzeJob,
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      setSelectedJobId(job.id);
      setSelectedArtifactKey("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteJob,
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      if (selectedJobId === jobId) {
        setSelectedJobId("");
        setSelectedArtifactKey("");
      }
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

  const hasActiveScrapeJob = useMemo(() => {
    return (jobsQuery.data ?? []).some((job) => job.job_type === "scrape" && (job.status === "pending" || job.status === "running"));
  }, [jobsQuery.data]);

  const selectedJob = useMemo(() => {
    return (jobsQuery.data ?? []).find((job) => job.id === selectedJobId) ?? null;
  }, [jobsQuery.data, selectedJobId]);

  const canRunAnalysis = useMemo(() => {
    if (analyzeMutation.isPending || hasActiveScrapeJob) return false;
    if (!completedScrapeJobs.length) return false;
    if (!selectedScrapeJobId) return true;
    return completedScrapeJobs.some((job) => job.id === selectedScrapeJobId);
  }, [analyzeMutation.isPending, completedScrapeJobs, hasActiveScrapeJob, selectedScrapeJobId]);

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

          <button type="button" className="secondary" onClick={createAnalyze} disabled={!canRunAnalysis}>
            {analyzeMutation.isPending ? "starting" : "run analysis"}
          </button>
        </div>

        <div className="info-box subtle">
          <p>analysis replaces dashboard data with one scrape run at a time.</p>
          <p>leave source run blank to analyze the latest completed scrape.</p>
          {hasActiveScrapeJob ? <p className="warning-text">wait for the active scrape to finish before running analysis, otherwise you may analyze an older run.</p> : null}
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
                      <div className="control-row">
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
                        {job.status !== "running" && job.status !== "pending" ? (
                          <button
                            type="button"
                            className="tiny-btn secondary"
                            onClick={() => {
                              const confirmed = window.confirm(`delete job ${job.id.slice(0, 8)} and its stored run files?`);
                              if (!confirmed) return;
                              deleteMutation.mutate(job.id);
                            }}
                            disabled={deleteMutation.isPending}
                          >
                            delete
                          </button>
                        ) : null}
                      </div>
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
            {selectedJob ? (
              <div className="info-box">
                <p>
                  viewing {selectedJob.job_type} run <strong>{selectedJob.id.slice(0, 8)}</strong> with status <strong>{selectedJob.status}</strong>
                </p>
                {selectedJob.job_type === "scrape" ? (
                  <p>
                    requested brands {asStringArray(selectedJob.params?.brands).join(", ") || "na"} with {selectedJob.params?.products_per_brand ?? "na"} products per brand and{" "}
                    {selectedJob.params?.reviews_per_product ?? "na"} reviews per product
                  </p>
                ) : null}
                {selectedJob.job_type === "analyze" ? (
                  <>
                    <p>
                      source scrape run <strong>{typeof selectedJob.result?.source_scrape_job_id === "string" ? selectedJob.result.source_scrape_job_id.slice(0, 8) : "latest completed"}</strong>
                    </p>
                    <p>
                      loaded brands {asStringArray((selectedJob.result?.hydrate_summary as Record<string, unknown> | undefined)?.brands).join(", ") || "na"} | products{" "}
                      {asNumber((selectedJob.result?.hydrate_summary as Record<string, unknown> | undefined)?.products_loaded) ?? 0} | reviews{" "}
                      {asNumber((selectedJob.result?.hydrate_summary as Record<string, unknown> | undefined)?.reviews_loaded) ?? 0}
                    </p>
                  </>
                ) : null}
              </div>
            ) : null}

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
