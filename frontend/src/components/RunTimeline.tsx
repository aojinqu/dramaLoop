const stages = [
  "premise_refinement",
  "character_card_generation",
  "story_outline_generation",
  "draft_generation",
  "critique_scoring",
  "targeted_rewrite",
  "final_assembly",
];

export function RunTimeline() {
  return (
    <section className="panel timeline-panel">
      <div className="panel-header">
        <p className="eyebrow">Runtime</p>
        <h2>Stage Timeline</h2>
      </div>
      <ul className="timeline-list">
        {stages.map((stage, index) => (
          <li key={stage} className={index === 0 ? "timeline-item active" : "timeline-item"}>
            <span className="timeline-dot" />
            <div>
              <strong>{stage}</strong>
              <p>{index === 0 ? "Ready to start" : "Pending"}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
