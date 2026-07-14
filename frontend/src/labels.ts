export const STAGE_LABELS: Record<string, string> = {
  season_planning: "整季规划",
  episode_plan_generation: "分集规划",
  episode_generation: "逐集生成",
  final_assembly: "最终合并",
  premise_refinement: "Premise",
  character_card_generation: "角色卡",
  story_outline_generation: "大纲",
  draft_generation: "初稿",
  critique_scoring: "评审",
  targeted_rewrite: "改写",
};

export const STATUS_LABELS: Record<string, string> = {
  pending: "等待中",
  running: "进行中",
  completed: "已完成",
  failed: "失败",
};

export const STREAM_STATE_LABELS: Record<string, string> = {
  idle: "就绪",
  streaming: "生成中",
  paused: "已暂停",
  reconnecting: "重连中",
  failed: "连接失败",
};

export const RUN_STATUS_LABELS: Record<string, string> = {
  running: "生成中",
  paused: "已暂停",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

export const EVENT_LABELS: Record<string, string> = {
  stage_started: "阶段开始",
  stage_completed: "阶段完成",
  artifact_ready: "产物就绪",
  season_started: "整季规划开始",
  season_completed: "整季规划完成",
  episode_plan_ready: "分集规划就绪",
  episode_started: "分集生成开始",
  episode_completed: "分集生成完成",
  episode_artifact_ready: "分集产物就绪",
  final_assembly_started: "最终合并开始",
  final_assembly_completed: "最终合并完成",
  run_paused: "任务暂停",
  run_resumed: "任务恢复",
  run_cancelled: "任务取消",
  run_completed: "任务完成",
  run_failed: "任务失败",
};

export function stageLabel(name: string): string {
  return STAGE_LABELS[name] ?? name;
}

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

export function streamStateLabel(state: string): string {
  return STREAM_STATE_LABELS[state] ?? state;
}

export function eventLabel(event: string): string {
  return EVENT_LABELS[event] ?? event;
}


export function runStatusLabel(status: string): string {
  return RUN_STATUS_LABELS[status] ?? status;
}
