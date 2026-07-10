import type { WebRunDetail } from "../types";

type ResultPanelProps = {
  detail: WebRunDetail | null;
  runId: string | null;
};

const placeholderArtifacts = ["episode_plan.json", "episodes/episode_01.md", "final_story.md"];
const placeholderStory =
  "婚礼进行到交换戒指的那一刻，周既白松开了她的手。整个宴会厅像被突然掐住呼吸，她抬眼看向那张冷淡到近乎残忍的脸，忽然意识到自己再也不需要向任何人证明温顺。";

export function ResultPanel({ detail, runId }: ResultPanelProps) {
  const episodes = detail?.episodes ?? [];
  const isEpisodic = detail?.request.format === "episodic_series";
  const mergedStory = detail?.final_story ?? "";
  const hasCompletedStory = Boolean(detail?.final_story);
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

        {isEpisodic ? (
          <>
            <div className="summary-strip">
              <strong>
                已完成 {detail?.completed_episode_count ?? 0} / {detail?.request.episode_count ?? 12} 集
              </strong>
              {detail?.season_summary ? <span>{detail.season_summary}</span> : null}
            </div>
            <div className="episode-list">
              {episodes.length ? (
                episodes.map((episode) => (
                  <article key={episode.episode_number} className="episode-card">
                    <h3>
                      第{episode.episode_number}集 · {episode.title}
                    </h3>
                    {episode.word_count ? <p className="episode-meta">{episode.word_count} 字</p> : null}
                    <p>{episode.content ?? "Waiting for episode content..."}</p>
                    {episode.hook_line ? <small>Hook: {episode.hook_line}</small> : null}
                  </article>
                ))
              ) : (
                <div className="story-shell">
                  <p>{runId ? "Waiting for episode output..." : placeholderStory}</p>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="story-shell">
            <p>{hasCompletedStory ? mergedStory : runId ? "Waiting for final story..." : placeholderStory}</p>
          </div>
        )}
      </div>
      <aside className="result-side">
        <div className="summary-card">
          <h3>Merged Story</h3>
          <div className="story-shell compact-shell">
            <p>{hasCompletedStory ? mergedStory : runId ? "Waiting for merged story..." : placeholderStory}</p>
          </div>
        </div>
        <div className="summary-card">
          <h3>Summary</h3>
          {overallScore !== null || rewriteFocus ? (
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
            <p>{isEpisodic ? "Episode progress will update here as the season completes." : runId ? "Waiting for run summary..." : "Summary will appear here after the run completes."}</p>
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
