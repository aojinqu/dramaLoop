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
  overall_score?: number | null;
}

export interface SeasonBible {
  title_candidate?: string;
  series_logline?: string;
  core_conflict?: string;
  target_episode_count?: number;
  final_payoff?: string;
  main_character_arcs?: string[];
  must_land_beats?: string[];
  [key: string]: unknown;
}

export interface EpisodePlanItem {
  episode_number: number;
  title: string;
  opening_situation?: string;
  core_conflict?: string;
  must_happen?: string[];
  hook_ending?: string;
  sets_up_next?: string;
  [key: string]: unknown;
}

export interface EpisodePlan {
  episodes: EpisodePlanItem[];
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
  pause_after_plan: boolean;
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

export type RunStatus = "running" | "paused" | "completed" | "failed" | "cancelled";
export type ControlPhase = "awaiting_plan_review" | "between_episodes" | "idle";

export interface WebRunDetail {
  run_id: string;
  status: RunStatus;
  current_stage?: string | null;
  current_episode_number?: number | null;
  completed_episode_count: number;
  episodes: WebEpisodeSnapshot[];
  final_story?: string | null;
  overall_score?: number | null;
  rewrite_focus?: string | null;
  season_summary?: string | null;
  season_bible?: SeasonBible | null;
  episode_plan?: EpisodePlan | null;
  available_artifacts: string[];
  stages: WebStageSnapshot[];
  control_phase?: ControlPhase | null;
  pause_after_plan?: boolean;
  has_live_controller?: boolean;
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
