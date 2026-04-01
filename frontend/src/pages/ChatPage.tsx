// this file renders a grounded ask data assistant over current analyzed data
import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { askChat, fetchBrands } from "../api/dashboard";
import { EmptyState } from "../components/EmptyState";
import type { ChatAnswer } from "../types/api";

type Turn = {
  question: string;
  response: ChatAnswer;
};

export function ChatPage() {
  // this page lets users ask grounded questions against the analyzed dataset
  const [question, setQuestion] = useState("");
  const [selectedBrandIds, setSelectedBrandIds] = useState<number[]>([]);
  const [turns, setTurns] = useState<Turn[]>([]);

  const brandsQuery = useQuery({ queryKey: ["brands"], queryFn: fetchBrands });

  const askMutation = useMutation({
    mutationFn: askChat,
    onSuccess: (response) => {
      setTurns((current) => [{ question, response }, ...current].slice(0, 6));
      setQuestion("");
    },
  });

  const placeholderQuestions = useMemo(
    () => [
      "which brand looks strongest on value for money right now",
      "what are the biggest recurring complaints across all brands",
      "which premium brand is still holding sentiment well",
    ],
    []
  );

  const toggleBrand = (brandId: number) => {
    // this helper toggles brand filters for the assistant
    setSelectedBrandIds((current) => (current.includes(brandId) ? current.filter((id) => id !== brandId) : [...current, brandId]));
  };

  const submitQuestion = () => {
    // this handler sends one grounded question to the backend assistant
    const trimmed = question.trim();
    if (trimmed.length < 3) return;
    askMutation.mutate({
      question: trimmed,
      brand_ids: selectedBrandIds,
    });
  };

  return (
    <section className="page-grid">
      <div className="card banner">
        <h3>ask data</h3>
        <p>this assistant answers from the current analyzed database only. it should be treated as a grounded q and a layer, not a freeform chatbot.</p>
      </div>

      <div className="chat-layout">
        <aside className="chat-sidebar">
          <div className="card">
            <div className="card-head">
              <h3>brand scope</h3>
            </div>
            {!brandsQuery.data?.length ? (
              <EmptyState title="no active brands" subtitle="run scrape and analysis first" />
            ) : (
              <div className="chip-list scroll-chip-list">
                {brandsQuery.data.map((brand) => (
                  <button
                    type="button"
                    key={brand.id}
                    className={selectedBrandIds.includes(brand.id) ? "chip active" : "chip"}
                    onClick={() => toggleBrand(brand.id)}
                  >
                    {brand.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-head">
              <h3>example prompts</h3>
            </div>
            <div className="chat-citations">
              {placeholderQuestions.map((item) => (
                <button key={item} type="button" className="chip" onClick={() => setQuestion(item)}>
                  {item}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <div className="chat-main">
          <div className="card">
            <div className="card-head">
              <h3>ask a question</h3>
            </div>
            <label>
              question
              <textarea
                rows={4}
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="ask about price bands, complaints, winning brands, or sentiment by brand"
              />
            </label>
            <div className="button-row">
              <button type="button" onClick={submitQuestion} disabled={askMutation.isPending || question.trim().length < 3}>
                {askMutation.isPending ? "asking" : "ask data"}
              </button>
            </div>
          </div>

          {!turns.length ? (
            <EmptyState title="no questions yet" subtitle="ask something about sentiment, pricing, complaints, or value for money" />
          ) : (
            <div className="chat-thread">
              {turns.map((turn, index) => (
                <div key={`${turn.question}-${index}`} className="card">
                  <div className="chat-bubble user">
                    <h4>question</h4>
                    <p>{turn.question}</p>
                  </div>
                  <div className="chat-bubble">
                    <h4>grounded answer</h4>
                    <p>{turn.response.answer}</p>
                    <div className="chat-meta">
                      {turn.response.provider ? <span className="pill neutral">{turn.response.provider}</span> : null}
                      {turn.response.model ? <span className="pill neutral">{turn.response.model}</span> : null}
                      {turn.response.brands.length ? <span className="pill neutral">{turn.response.brands.length} brands in scope</span> : null}
                    </div>
                  </div>
                  {turn.response.citations.length ? (
                    <div className="chat-citations">
                      {turn.response.citations.map((citation, citationIndex) => (
                        <div className="chat-citation" key={`${citation.label}-${citationIndex}`}>
                          <p>{citation.label}</p>
                          <p>{citation.type}</p>
                          {citation.url ? (
                            <a className="ghost-link" href={citation.url} target="_blank" rel="noreferrer">
                              open source
                            </a>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
