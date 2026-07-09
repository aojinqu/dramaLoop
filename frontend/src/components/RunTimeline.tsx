import type { WebRunDetail } from "../types";

const fallbackStages = [
  "premise_refinement",
  "character_card_generation",
  "story_outline_generation",
  "draft_generation",
  "critique_scoring",
  "targeted_rewrite",
  "final_assembly",
];

type RunTimelineProps = {
  detail: WebRunDetail | null;
  streamState: "idle" | "streaming" | "reconnecting" | "failed";
};

export function RunTimeline({ detail, streamState }: RunTimelineProps) {
  const stages = detail?.stages ?? fallbackStages.map((name) => ({ name, status: "pending" as const }));

  return (
    <section className="panel timeline-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Runtime</p>
          <h2>Stage Timeline</h2>
        </div>
        <p>{streamState === "idle" ? "Ready to start" : streamState}</p>
      </div>
      <ul className="timeline-list">
        {stages.map((stage) => {
          const className = stage.status === "running" ? "timeline-item active" : "timeline-item";
          return (
            <li key={stage.name} className={className}>
              <span className="timeline-dot" />
              <div>
                <strong>{stage.name}</strong>
                <p>{stage.status}</p>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
