import { stageLabel, statusLabel, streamStateLabel } from "../labels";
import type { WebRunDetail } from "../types";

const fallbackStages = [
  "season_planning",
  "episode_plan_generation",
  "episode_generation",
  "final_assembly",
];

type RunTimelineProps = {
  detail: WebRunDetail | null;
  streamState: "idle" | "streaming" | "paused" | "reconnecting" | "failed";
};

export function RunTimeline({ detail, streamState }: RunTimelineProps) {
  const stages = detail?.stages ?? fallbackStages.map((name) => ({ name, status: "pending" as const }));
  const total = detail?.request.episode_count ?? 0;
  const completed = detail?.completed_episode_count ?? 0;
  const currentEpisode = detail?.current_episode_number;
  const progress = total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0;

  return (
    <section className="panel timeline-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Runtime</p>
          <h2>阶段进度</h2>
        </div>
        <p className={`stream-badge stream-badge--${streamState}`}>{streamStateLabel(streamState)}</p>
      </div>

      {detail ? (
        <div className="progress-block">
          <div className="progress-meta">
            <strong>
              {completed} / {total || "—"} 集
            </strong>
            <span>
              {detail.current_stage ? stageLabel(detail.current_stage) : statusLabel(detail.status)}
              {currentEpisode ? ` · 第 ${currentEpisode} 集` : ""}
            </span>
          </div>
          <div className="progress-track" aria-hidden="true">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      ) : (
        <p className="empty-hint">发起生成后，这里会显示四阶段进度。</p>
      )}

      <ul className="timeline-list">
        {stages.map((stage) => {
          const className = [
            "timeline-item",
            stage.status === "running" ? "active" : "",
            stage.status === "completed" ? "done" : "",
            stage.status === "failed" ? "failed" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <li key={stage.name} className={className}>
              <span className="timeline-dot" />
              <div>
                <strong>{stageLabel(stage.name)}</strong>
                <p>{statusLabel(stage.status)}</p>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
