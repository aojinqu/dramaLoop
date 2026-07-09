const artifacts = ["run_summary.md", "rewrite_plan_v1.json", "events.jsonl"];

export function ResultPanel() {
  return (
    <section className="panel result-panel">
      <div className="result-main">
        <div className="panel-header">
          <p className="eyebrow">Output</p>
          <h2>Final Story</h2>
        </div>
        <div className="story-shell">
          <p>
            婚礼进行到交换戒指的那一刻，周既白松开了她的手。整个宴会厅像被突然掐住呼吸，
            她抬眼看向那张冷淡到近乎残忍的脸，忽然意识到自己再也不需要向任何人证明温顺。
          </p>
        </div>
      </div>
      <aside className="result-side">
        <div className="summary-card">
          <h3>Summary</h3>
          <dl>
            <div>
              <dt>Overall score</dt>
              <dd>7.9</dd>
            </div>
            <div>
              <dt>Rewrite focus</dt>
              <dd>ending_payoff</dd>
            </div>
          </dl>
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
