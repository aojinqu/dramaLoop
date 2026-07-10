export type StageStatus = "pending" | "running" | "completed" | "failed";

export interface WebStageSnapshot {
  name: string;
  status: StageStatus;
}

export interface WebEpisodeSnapshot {
  episode_number: number;
  title: string;
  status: StageStatus;
  word_count?: number | null;
  hook_line?: string | null;
  content?: string | null;
}

export interface RunFormInput {
  idea: string;
  style: string[];
  audience: string;
  constraints: string[];
  max_iterations: number;
  format: "episodic_series";
  episode_count: number;
  episode_min_words: number;
  episode_max_words: number;
  delivery_mode: "stream_and_final";
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
  current_episode_number?: number | null;
  completed_episode_count: number;
  episodes: WebEpisodeSnapshot[];
  final_story?: string | null;
  overall_score?: number | null;
  rewrite_focus?: string | null;
  season_summary?: string | null;
  available_artifacts: string[];
  stages: WebStageSnapshot[];
  request: {
    idea: string;
    style: string[];
    audience?: string | null;
    constraints: string[];
    max_iterations: number;
    length: "short";
    format: "single_story" | "episodic_series";
    episode_count: number;
    episode_min_words: number;
    episode_max_words: number;
    delivery_mode: "stream_and_final";
  };
}
