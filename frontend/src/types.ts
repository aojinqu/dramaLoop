export type StageStatus = "pending" | "running" | "completed" | "failed";

export interface WebStageSnapshot {
  name: string;
  status: StageStatus;
}

export interface RunFormInput {
  idea: string;
  style: string[];
  audience: string;
  constraints: string[];
  max_iterations: number;
}

export interface WebRunCreated {
  run_id: string;
  status: "running";
  stream_url: string;
}

export interface StreamMessage {
  event: string;
  data: Record<string, unknown>;
}

export interface WebRunDetail {
  run_id: string;
  status: "running" | "completed" | "failed";
  current_stage?: string | null;
  final_story?: string | null;
  overall_score?: number | null;
  rewrite_focus?: string | null;
  available_artifacts: string[];
  stages: WebStageSnapshot[];
  request: {
    idea: string;
    style: string[];
    audience?: string | null;
    constraints: string[];
    max_iterations: number;
    length: "short";
  };
}
