import type { WebRunDetail } from "../types";

type ResultPanelProps = {
  detail: WebRunDetail | null;
  runId: string | null;
};

const placeholderArtifacts = ["run_summary.md", "rewrite_plan_v1.json", "events.jsonl"];
const placeholderStory =
  "婚礼进行到交换戒指的那一刻，周既白松开了她的手。整个宴会厅像被突然掐住呼吸，她抬眼看向那张冷淡到近乎残忍的脸，忽然意识到自己再也不需要向任何人证明温顺。";

export function ResultPanel({ detail, runId }: ResultPanelProps) {
  const hasCompletedStory = Boolean(detail?.final_story);
  const story = hasCompletedStory ? detail?.final_story ?? "" : runId ? "Waiting for final story..." : placeholderStory;
  const overallScore = detail?.overall_score ?? null;
  const rewriteFocus = detail?.rewrite_focus ?? null;
  const artifacts = detail?.available_artifacts?.length ? detail.available_artifacts : placeholderArtifacts;

  return (
    <section className="panel result-panel">
      <div className="result-main">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Output</p>
            <h2>Final Story</h2>
          </div>
          {runId ? <p>{runId}</p> : null}
        </div>
        <div className="story-shell">
          <p>{story}</p>
        </div>
      </div>
      <aside className="result-side">
        <div className="summary-card">
          <h3>Summary</h3>
          {hasCompletedStory ? (
            <dl>
              <div>
                <dt>Overall score</dt>
                <dd>{overallScore}</dd>
              </div>
              <div>
                <dt>Rewrite focus</dt>
                <dd>{rewriteFocus}</dd>
              </div>
            </dl>
          ) : (
            <p>{runId ? "Waiting for run summary..." : "Summary will appear here after the run completes."}</p>
          )}
        </div>
        <div className="summary-card">
          <h3>Artifacts</h3>
          <ul>
            {artifacts.map((artifact) => (
              <li key={artifact}>{artifact}</li>
            ))}
          </ul>
        </div>
      </aside>
    </section>
  );
}
