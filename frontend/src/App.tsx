import { useRef, useState } from "react";
import { connectRunStream, createRun, fetchRunDetail } from "./api";
import { EventFeed } from "./components/EventFeed";
import { ResultPanel } from "./components/ResultPanel";
import { RunForm } from "./components/RunForm";
import { RunTimeline } from "./components/RunTimeline";
import type { RunFormInput, StreamMessage, WebRunDetail, WebStageSnapshot } from "./types";
import "./app.css";

const defaultStages: WebStageSnapshot[] = [
  { name: "premise_refinement", status: "pending" },
  { name: "character_card_generation", status: "pending" },
  { name: "story_outline_generation", status: "pending" },
  { name: "draft_generation", status: "pending" },
  { name: "critique_scoring", status: "pending" },
  { name: "targeted_rewrite", status: "pending" },
  { name: "final_assembly", status: "pending" },
];

function updateStageSnapshots(
  stages: WebStageSnapshot[],
  stageName: string,
  status: WebStageSnapshot["status"],
): WebStageSnapshot[] {
  return stages.map((stage) => (stage.name === stageName ? { ...stage, status } : stage));
}

export default function App() {
  const streamRef = useRef<EventSource | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [detail, setDetail] = useState<WebRunDetail | null>(null);
  const [events, setEvents] = useState<StreamMessage[]>([]);
  const [streamState, setStreamState] = useState<"idle" | "streaming" | "reconnecting" | "failed">("idle");

  const handleLaunch = async (input: RunFormInput) => {
    streamRef.current?.close();
    setEvents([]);
    setRunId(null);

    const created = await createRun(input);
    setRunId(created.run_id);
    setStreamState("streaming");
    setDetail({
      run_id: created.run_id,
      status: "running",
      current_stage: null,
      final_story: null,
      overall_score: null,
      rewrite_focus: null,
      available_artifacts: [],
      stages: defaultStages,
      request: {
        idea: input.idea,
        style: input.style,
        audience: input.audience || null,
        constraints: input.constraints,
        max_iterations: input.max_iterations,
        length: "short",
      },
    });

    const source = connectRunStream(created.run_id, {
      onMessage: async (message) => {
        setEvents((current) => [...current, message]);

        setDetail((current) => {
          if (!current) {
            return current;
          }

          const stageName = typeof message.data.stage === "string" ? message.data.stage : null;
          if (message.event === "stage_started" && stageName) {
            return {
              ...current,
              current_stage: stageName,
              stages: updateStageSnapshots(current.stages, stageName, "running"),
            };
          }
          if (message.event === "stage_completed" && stageName) {
            return {
              ...current,
              current_stage: stageName,
              stages: updateStageSnapshots(current.stages, stageName, "completed"),
            };
          }
          if (message.event === "artifact_ready") {
            const artifact = typeof message.data.artifact === "string" ? message.data.artifact : null;
            if (!artifact || current.available_artifacts.includes(artifact)) {
              return current;
            }
            return {
              ...current,
              available_artifacts: [...current.available_artifacts, artifact],
            };
          }
          return current;
        });

        if (message.event === "run_completed" || message.event === "run_failed") {
          const nextDetail = await fetchRunDetail(created.run_id);
          setDetail(nextDetail);
          setStreamState(message.event === "run_completed" ? "idle" : "failed");
          source.close();
          streamRef.current = null;
        }
      },
      onError: async () => {
        setStreamState("reconnecting");
        try {
          const nextDetail = await fetchRunDetail(created.run_id);
          setDetail(nextDetail);
          setStreamState(nextDetail.status === "failed" ? "failed" : "streaming");
        } catch {
          setStreamState("failed");
        }
      },
    });

    streamRef.current = source;
  };

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
        <RunForm onSubmit={handleLaunch} />
      </aside>
      <main className="right-panel">
        <section className="top-grid">
          <RunTimeline detail={detail} streamState={streamState} />
          <EventFeed events={events} />
        </section>
        <ResultPanel detail={detail} runId={runId} />
      </main>
    </div>
  );
}
