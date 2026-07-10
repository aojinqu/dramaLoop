import type { RunFormInput, StreamMessage, WebRunCreated, WebRunDetail } from "./types";

export async function createRun(input: RunFormInput): Promise<WebRunCreated> {
  const response = await fetch("/api/runs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    throw new Error(`Failed to create run: ${response.status}`);
  }

  return (await response.json()) as WebRunCreated;
}

export async function fetchRunDetail(runId: string): Promise<WebRunDetail> {
  const response = await fetch(`/api/runs/${runId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch run detail: ${response.status}`);
  }

  return (await response.json()) as WebRunDetail;
}

export function connectRunStream(
  runId: string,
  handlers: {
    onMessage: (message: StreamMessage) => void;
    onError: () => void;
  },
): EventSource {
  const source = new EventSource(`/api/runs/${runId}/stream`);
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
    "run_completed",
    "run_failed",
  ];

  eventNames.forEach((eventName) => {
    source.addEventListener(eventName, (event) => {
      handlers.onMessage({
        event: eventName,
        data: JSON.parse((event as MessageEvent<string>).data) as Record<string, unknown>,
      });
    });
  });

  source.onerror = () => {
    handlers.onError();
  };

  return source;
}
