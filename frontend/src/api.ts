import type { EpisodePlanItem, RunFormInput, StreamMessage, WebRunCreated, WebRunDetail } from "./types";

export async function createRun(input: RunFormInput): Promise<WebRunCreated> {
  const response = await fetch("/api/runs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `创建任务失败（${response.status}）`);
  }

  return (await response.json()) as WebRunCreated;
}

export async function fetchRunDetail(runId: string): Promise<WebRunDetail> {
  const response = await fetch(`/api/runs/${runId}`);

  if (!response.ok) {
    throw new Error(`获取任务详情失败（${response.status}）`);
  }

  return (await response.json()) as WebRunDetail;
}

async function postControl(runId: string, action: "pause" | "resume" | "cancel"): Promise<void> {
  const response = await fetch(`/api/runs/${runId}/${action}`, { method: "POST" });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `${action} failed (${response.status})`);
  }
}

export function pauseRun(runId: string): Promise<void> {
  return postControl(runId, "pause");
}

export function resumeRun(runId: string): Promise<void> {
  return postControl(runId, "resume");
}

export function cancelRun(runId: string): Promise<void> {
  return postControl(runId, "cancel");
}

export async function updateEpisodePlan(runId: string, episodes: EpisodePlanItem[]): Promise<WebRunDetail> {
  const response = await fetch(`/api/runs/${runId}/episode-plan`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ episodes }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `更新分集规划失败（${response.status}）`);
  }
  return (await response.json()) as WebRunDetail;
}

export async function regenerateEpisode(runId: string, episodeNumber: number): Promise<void> {
  const response = await fetch(`/api/runs/${runId}/episodes/${episodeNumber}/regenerate`, {
    method: "POST",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `重生成失败（${response.status}）`);
  }
}

export function connectRunStream(
  runId: string,
  handlers: {
    onMessage: (message: StreamMessage) => void;
    onError: () => void;
    onOpen?: () => void;
    afterEventId?: string | null;
  },
): EventSource {
  const query = handlers.afterEventId
    ? `?after=${encodeURIComponent(handlers.afterEventId)}`
    : "";
  const source = new EventSource(`/api/runs/${runId}/stream${query}`);
  const eventNames = [
    "stage_started",
    "stage_completed",
    "artifact_ready",
    "season_started",
    "season_completed",
    "episode_plan_ready",
    "episode_started",
    "episode_completed",
    "episode_artifact_ready",
    "final_assembly_started",
    "final_assembly_completed",
    "run_paused",
    "run_resumed",
    "run_cancelled",
    "run_completed",
    "run_failed",
  ];

  eventNames.forEach((eventName) => {
    source.addEventListener(eventName, (event) => {
      const messageEvent = event as MessageEvent<string>;
      handlers.onMessage({
        id: messageEvent.lastEventId || undefined,
        event: eventName,
        data: JSON.parse(messageEvent.data) as Record<string, unknown>,
      });
    });
  });

  source.onopen = () => {
    handlers.onOpen?.();
  };

  source.onerror = () => {
    handlers.onError();
  };

  return source;
}
