// this file shows sentiment with color meaning
import clsx from "clsx";

type SentimentPillProps = {
  score: number | null;
};

export function SentimentPill({ score }: SentimentPillProps) {
  // this component maps score to readable badge
  if (score === null || Number.isNaN(score)) {
    return <span className="pill neutral">no data</span>;
  }

  const tone = score >= 0.2 ? "good" : score <= -0.2 ? "bad" : "neutral";
  return <span className={clsx("pill", tone)}>{score.toFixed(3)}</span>;
}
