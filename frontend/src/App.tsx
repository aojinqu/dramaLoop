import { useEffect, useRef, useState } from "react";
import {
  cancelRun,
  connectRunStream,
  createRun,
  fetchRunDetail,
  pauseRun,
  regenerateEpisode,
  resumeRun,
  updateEpisodePlan,
} from "./api";
import { ControlBar } from "./components/ControlBar";
import { EventFeed } from "./components/EventFeed";
import { ResultPanel } from "./components/ResultPanel";
import { RunForm } from "./components/RunForm";
import { RunTimeline } from "./components/RunTimeline";
import { liveActivityFromMessage } from "./progress";
import type { EpisodePlanItem, RunFormInput, StreamMessage, WebRunDetail, WebStageSnapshot } from "./types";
import "./app.css";

const defaultStages: WebStageSnapshot[] = [
  { name: "season_planning", status: "pending" },
  { name: "episode_plan_generation", status: "pending" },
  { name: "episode_generation", status: "pending" },
  { name: "final_assembly", status: "pending" },
];

function updateStageSnapshots(
  stages: WebStageSnapshot[],
  stageName: string,
  status: WebStageSnapshot["status"],
): WebStageSnapshot[] {
  return stages.map((stage) => (stage.name === stageName ? { ...stage, status } : stage));
}

function buildOptimisticDetail(runId: string, input: RunFormInput): WebRunDetail {
  return {
    run_id: runId,
    status: "running",
    current_stage: null,
    current_episode_number: null,
    completed_episode_count: 0,
    episodes: [],
    final_story: null,
    overall_score: null,
    rewrite_focus: null,
    season_summary: null,
    season_bible: null,
    episode_plan: null,
    available_artifacts: [],
    stages: defaultStages,
    control_phase: "idle",
    pause_after_plan: input.pause_after_plan,
    request: {
      idea: input.idea,
      style: input.style,
      audience: input.audience || null,
      constraints: input.constraints,
      max_iterations: input.max_iterations,
      length: "short",
      format: input.format,
      episode_count: input.episode_count,
      episode_min_words: input.episode_min_words,
      episode_max_words: input.episode_max_words,
      delivery_mode: input.delivery_mode,
    },
  };
}

export default function App() {
  const streamRef = useRef<EventSource | null>(null);
  const activeRunRef = useRef<string | null>(null);
  const lastEventIdRef = useRef<string | null>(null);
  const detailRequestRef = useRef(0);
  const launchPendingRef = useRef(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [detail, setDetail] = useState<WebRunDetail | null>(null);
  const [events, setEvents] = useState<StreamMessage[]>([]);
  const [streamState, setStreamState] = useState<"idle" | "streaming" | "paused" | "reconnecting" | "failed">("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [controlBusy, setControlBusy] = useState(false);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [liveActivity, setLiveActivity] = useState<string | null>(null);

  const refreshDetail = async (id: string) => {
    const requestId = ++detailRequestRef.current;
    try {
      const nextDetail = await fetchRunDetail(id);
      if (activeRunRef.current !== id || detailRequestRef.current !== requestId) {
        return null;
      }
      setDetail(nextDetail);
      return nextDetail;
    } catch {
      return null;
    }
  };

  const attachStream = (id: string) => {
    streamRef.current?.close();
    const source = connectRunStream(id, {
      onMessage: async (message) => {
        if (activeRunRef.current !== id) {
          return;
        }
        if (message.id) {
          lastEventIdRef.current = message.id;
        }
        setEvents((current) => [...current, message]);
        const activity = liveActivityFromMessage(message);
        if (activity) {
          setLiveActivity(activity);
        }

        setDetail((current) => {
          if (!current) {
            return current;
          }

          const stageName = typeof message.data.stage === "string" ? message.data.stage : null;
          const iteration = typeof message.data.iteration === "number" ? message.data.iteration : null;
          if (
            (message.event === "stage_started" ||
              message.event === "season_started" ||
              message.event === "episode_started" ||
              message.event === "final_assembly_started") &&
            stageName
          ) {
            return {
              ...current,
              current_stage: stageName,
              current_episode_number: message.event === "episode_started" ? iteration : current.current_episode_number,
              stages: updateStageSnapshots(current.stages, stageName, "running"),
            };
          }
          if (
            (message.event === "stage_completed" ||
              message.event === "season_completed" ||
              message.event === "episode_completed" ||
              message.event === "final_assembly_completed" ||
              message.event === "episode_plan_ready") &&
            stageName
          ) {
            return {
              ...current,
              current_stage: stageName,
              stages: updateStageSnapshots(current.stages, stageName, "completed"),
            };
          }
          if (message.event === "artifact_ready" || message.event === "episode_artifact_ready") {
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

        if (
          message.event === "season_completed" ||
          message.event === "episode_plan_ready" ||
          message.event === "episode_started" ||
          message.event === "episode_completed" ||
          message.event === "episode_artifact_ready" ||
          message.event === "final_assembly_completed" ||
          message.event === "run_paused" ||
          message.event === "run_resumed"
        ) {
          const next = await refreshDetail(id);
          if (message.event === "run_paused") {
            setStreamState("paused");
          } else if (message.event === "run_resumed") {
            setStreamState("streaming");
          } else if (next?.status === "paused") {
            setStreamState("paused");
          }
        }

        if (
          message.event === "run_completed" ||
          message.event === "run_failed" ||
          message.event === "run_cancelled"
        ) {
          await refreshDetail(id);
          if (message.event === "run_completed") {
            setLiveActivity("生成完成");
            setStreamState("idle");
          } else if (message.event === "run_cancelled") {
            setLiveActivity("已停止");
            setStreamState("idle");
          } else {
            setLiveActivity("生成失败");
            setStreamState("failed");
          }
          source.close();
          if (streamRef.current === source) {
            streamRef.current = null;
          }
        }
      },
      onError: async () => {
        if (activeRunRef.current !== id) {
          return;
        }
        setStreamState("reconnecting");
        const nextDetail = await refreshDetail(id);
        if (activeRunRef.current !== id) {
          return;
        }
        if (!nextDetail) {
          return;
        }
        if (nextDetail.status === "completed" || nextDetail.status === "cancelled") {
          setStreamState("idle");
          source.close();
          if (streamRef.current === source) {
            streamRef.current = null;
          }
        } else if (nextDetail.status === "failed") {
          setStreamState("failed");
          source.close();
          if (streamRef.current === source) {
            streamRef.current = null;
          }
        } else if (nextDetail.status === "paused") {
          setStreamState("paused");
        } else {
          setStreamState("streaming");
        }
      },
      onOpen: () => {
        if (activeRunRef.current !== id) {
          return;
        }
        setStreamState((current) => (current === "paused" ? current : "streaming"));
      },
      afterEventId: lastEventIdRef.current,
    });
    streamRef.current = source;
  };

  const handleLaunch = async (input: RunFormInput) => {
    if (launchPendingRef.current) {
      return;
    }
    launchPendingRef.current = true;
    streamRef.current?.close();
    streamRef.current = null;
    activeRunRef.current = null;
    lastEventIdRef.current = null;
    detailRequestRef.current += 1;
    setEvents([]);
    setRunId(null);
    setDetail(null);
    setLaunchError(null);
    setLiveActivity("正在创建任务…");
    setIsSubmitting(true);

    try {
      const created = await createRun(input);
      activeRunRef.current = created.run_id;
      setRunId(created.run_id);
      setStreamState("streaming");
      setDetail(buildOptimisticDetail(created.run_id, input));
      attachStream(created.run_id);
    } catch (error) {
      setStreamState("failed");
      setLaunchError(error instanceof Error ? error.message : "创建任务失败");
    } finally {
      launchPendingRef.current = false;
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    return () => {
      activeRunRef.current = null;
      detailRequestRef.current += 1;
      streamRef.current?.close();
      streamRef.current = null;
    };
  }, []);

  const withControl = async (action: () => Promise<void>) => {
    if (!runId) {
      return;
    }
    setControlBusy(true);
    setLaunchError(null);
    try {
      await action();
      await refreshDetail(runId);
    } catch (error) {
      setLaunchError(error instanceof Error ? error.message : "操作失败");
    } finally {
      setControlBusy(false);
    }
  };

  const handlePause = () => withControl(async () => {
    if (!runId) return;
    await pauseRun(runId);
    setStreamState("paused");
  });

  const handleResume = () => withControl(async () => {
    if (!runId) return;
    await resumeRun(runId);
    setStreamState("streaming");
    if (!streamRef.current) {
      attachStream(runId);
    }
  });

  const handleCancel = () => withControl(async () => {
    if (!runId) return;
    await cancelRun(runId);
  });

  const handleSavePlan = async (episodes: EpisodePlanItem[]) => {
    if (!runId) return;
    setControlBusy(true);
    try {
      const next = await updateEpisodePlan(runId, episodes);
      setDetail(next);
    } catch (error) {
      setLaunchError(error instanceof Error ? error.message : "保存规划失败");
      throw error;
    } finally {
      setControlBusy(false);
    }
  };

  const handleRegenerate = async (episodeNumber: number) => {
    if (!runId) return;
    setControlBusy(true);
    try {
      await regenerateEpisode(runId, episodeNumber);
      setStreamState("streaming");
      if (!streamRef.current) {
        attachStream(runId);
      }
      // poll until regenerate settles
      for (let i = 0; i < 40; i += 1) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        const next = await refreshDetail(runId);
        if (next && next.status !== "running") {
          setStreamState(next.status === "paused" ? "paused" : "idle");
          break;
        }
      }
    } catch (error) {
      setLaunchError(error instanceof Error ? error.message : "重生成失败");
    } finally {
      setControlBusy(false);
    }
  };

  const formBusy = isSubmitting || streamState === "streaming" || streamState === "reconnecting";

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">D</span>
          <div>
            <h1>短剧生成工作台</h1>
            <p>Dramaloop · AI Series Studio</p>
          </div>
        </div>
        <div className="header-run">
          <span className={`header-status header-status--${streamState}`}>
            <span className="header-status-dot" aria-hidden="true" />
            {detail?.status === "paused" ? "等待确认" : liveActivity || "准备就绪"}
          </span>
          {runId ? <code title={runId}>{runId}</code> : null}
        </div>
      </header>

      <div className="app-body">
        <aside className="composer-sidebar">
          <RunForm onSubmit={handleLaunch} disabled={formBusy} error={launchError} />
        </aside>

        <main className="workspace">
          <ControlBar
            status={detail?.status}
            controlPhase={detail?.control_phase}
            busy={controlBusy}
            onPause={handlePause}
            onResume={handleResume}
            onCancel={handleCancel}
          />
          <section className="runtime-dock" aria-label="运行监控">
            <RunTimeline detail={detail} streamState={streamState} />
            <EventFeed events={events} liveActivity={liveActivity} streamState={streamState} />
          </section>
          <ResultPanel
            detail={detail}
            runId={runId}
            onSavePlan={handleSavePlan}
            onRegenerate={handleRegenerate}
            controlBusy={controlBusy}
          />
        </main>
      </div>
    </div>
  );
}
