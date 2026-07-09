import { EventFeed } from "./components/EventFeed";
import { ResultPanel } from "./components/ResultPanel";
import { RunForm } from "./components/RunForm";
import { RunTimeline } from "./components/RunTimeline";
import "./app.css";

export default function App() {
  return (
    <div className="page-shell">
      <aside className="left-panel">
        <div className="hero-block">
          <p className="eyebrow">Dramaloop Demo</p>
          <h1>Dramaloop Web Demo</h1>
          <p className="hero-copy">
            在同一界面中观察 staged harness 的运行过程，并预览最终中文短剧故事成稿。
          </p>
        </div>
        <RunForm onSubmit={() => {}} />
      </aside>
      <main className="right-panel">
        <section className="top-grid">
          <RunTimeline />
          <EventFeed />
        </section>
        <ResultPanel />
      </main>
    </div>
  );
}
