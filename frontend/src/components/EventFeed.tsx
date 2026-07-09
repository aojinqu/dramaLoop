const placeholderEvents = [
  "run_created · run_id reserved",
  "stage_started · premise_refinement",
  "artifact_ready · premise.json",
];

export function EventFeed() {
  return (
    <section className="panel event-panel">
      <div className="panel-header">
        <p className="eyebrow">Streaming</p>
        <h2>Event Stream</h2>
      </div>
      <ul className="event-list">
        {placeholderEvents.map((event) => (
          <li key={event}>{event}</li>
        ))}
      </ul>
    </section>
  );
}
