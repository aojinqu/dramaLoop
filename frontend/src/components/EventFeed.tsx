import type { StreamMessage } from "../types";

type EventFeedProps = {
  events: StreamMessage[];
};

const placeholderEvents = [
  "run_created · run_id reserved",
  "stage_started · premise_refinement",
  "artifact_ready · premise.json",
];

export function EventFeed({ events }: EventFeedProps) {
  const lines =
    events.length > 0
      ? events.map(({ event, data }) => {
          const stage = typeof data.stage === "string" ? data.stage : null;
          const artifact = typeof data.artifact === "string" ? data.artifact : null;
          const suffix = stage ?? artifact ?? "event received";
          return `${event} · ${suffix}`;
        })
      : placeholderEvents;

  return (
    <section className="panel event-panel">
      <div className="panel-header">
        <p className="eyebrow">Streaming</p>
        <h2>Event Stream</h2>
      </div>
      <ul className="event-list">
        {lines.map((event) => (
          <li key={event}>{event}</li>
        ))}
      </ul>
    </section>
  );
}
