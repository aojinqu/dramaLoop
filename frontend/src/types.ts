export type StageStatus = "pending" | "running" | "completed" | "failed";

export interface WebStageSnapshot {
  name: string;
  status: StageStatus;
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
