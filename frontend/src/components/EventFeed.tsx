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
    <section className="panel event-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Streaming</p>
          <h2>实时进度</h2>
        </div>
        <p>{events.length ? `${events.length} 条` : "等待事件"}</p>
      </div>

      {liveActivity || isLive ? (
        <div className={`live-activity ${isLive ? "is-live" : ""}`}>
          {isLive ? <span className="live-dot" aria-hidden="true" /> : null}
          <span>{liveActivity || "正在接收进度事件…"}</span>
        </div>
      ) : null}

      {lines.length === 0 ? (
        <p className="empty-hint">生成开始后，这里会实时滚动输出阶段与分集进度。</p>
      ) : (
        <ul className="event-list progress-log" ref={listRef}>
          {lines.map((line) => (
            <li key={line.id} className={`progress-line progress-line--${line.tone}`}>
              <time>{line.at}</time>
              <span>{line.text}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
