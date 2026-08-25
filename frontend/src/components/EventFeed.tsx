import { useEffect, useMemo, useRef } from "react";
import { formatProgressMessage } from "../progress";
import type { StreamMessage } from "../types";

type EventFeedProps = {
  events: StreamMessage[];
  liveActivity?: string | null;
  streamState?: "idle" | "streaming" | "paused" | "reconnecting" | "failed";
};

export function EventFeed({ events, liveActivity = null, streamState = "idle" }: EventFeedProps) {
  const listRef = useRef<HTMLUListElement>(null);
  const lines = useMemo(
    () => events.map((message, index) => formatProgressMessage(message, index)),
    [events],
  );
  const isLive = streamState === "streaming" || streamState === "reconnecting";

  useEffect(() => {
    const node = listRef.current;
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  }, [lines.length, liveActivity]);

  return (
    <section className="runtime-card event-panel">
      <div className="runtime-card-header">
        <div className="runtime-title">
          <p className="eyebrow">Activity</p>
          <h2>实时动态</h2>
        </div>
        <span className="event-count">{events.length || 0}</span>
      </div>

      <div className={`live-activity ${isLive ? "is-live" : ""}`}>
        {isLive ? <span className="live-dot" aria-hidden="true" /> : <span className="live-dot is-idle" aria-hidden="true" />}
        <span>{liveActivity || "等待创建任务"}</span>
      </div>

      {lines.length ? (
        <details className="event-details">
          <summary>查看完整日志</summary>
          <ul className="event-list progress-log" ref={listRef}>
            {lines.map((line) => (
              <li key={line.id} className={`progress-line progress-line--${line.tone}`}>
                <time>{line.at}</time>
                <span>{line.text}</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}
