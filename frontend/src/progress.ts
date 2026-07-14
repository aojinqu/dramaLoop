import { stageLabel } from "./labels";
import type { StreamMessage } from "./types";

export type ProgressLine = {
  id: string;
  text: string;
  tone: "info" | "success" | "warn" | "error" | "live";
  at: string;
};

function timeLabel(date = new Date()): string {
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}

export function formatProgressMessage(message: StreamMessage, index: number): ProgressLine {
  const stage = typeof message.data.stage === "string" ? message.data.stage : null;
  const artifact = typeof message.data.artifact === "string" ? message.data.artifact : null;
  const iteration = typeof message.data.iteration === "number" ? message.data.iteration : null;
  const detail = typeof message.data.detail === "string" ? message.data.detail : null;
  const at = timeLabel();
  const id = `${message.event}-${index}`;

  switch (message.event) {
    case "season_started":
      return { id, at, tone: "live", text: "整季规划开始…" };
    case "season_completed":
      return { id, at, tone: "success", text: `整季规划完成${artifact ? ` → ${artifact}` : ""}` };
    case "episode_plan_ready":
      return { id, at, tone: "success", text: `分集规划就绪${artifact ? ` → ${artifact}` : ""}，可审查后继续` };
    case "episode_started":
      return {
        id,
        at,
        tone: "live",
        text: iteration ? `正在生成第 ${iteration} 集…` : "正在生成分集…",
      };
    case "episode_completed":
      return {
        id,
        at,
        tone: "success",
        text: iteration
          ? `第 ${iteration} 集完成${artifact ? ` → ${artifact}` : ""}`
          : `分集完成${artifact ? ` → ${artifact}` : ""}`,
      };
    case "episode_artifact_ready":
      return { id, at, tone: "info", text: `分集产物就绪 → ${artifact ?? "artifact"}` };
    case "final_assembly_started":
      return { id, at, tone: "live", text: "正在合并最终成稿…" };
    case "final_assembly_completed":
      return { id, at, tone: "success", text: `最终合并完成${artifact ? ` → ${artifact}` : ""}` };
    case "run_paused":
      return { id, at, tone: "warn", text: `已暂停${detail ? `（${detail}）` : ""}` };
    case "run_resumed":
      return { id, at, tone: "live", text: "已恢复生成" };
    case "run_cancelled":
      return { id, at, tone: "warn", text: "任务已停止" };
    case "run_completed":
      return { id, at, tone: "success", text: "全部完成" };
    case "run_failed":
      return { id, at, tone: "error", text: `任务失败${detail ? `：${detail}` : ""}` };
    case "artifact_ready":
      return { id, at, tone: "info", text: `产物就绪 → ${artifact ?? "artifact"}` };
    case "stage_started":
      return { id, at, tone: "live", text: `${stage ? stageLabel(stage) : "阶段"}开始…` };
    case "stage_completed":
      return {
        id,
        at,
        tone: "success",
        text: `${stage ? stageLabel(stage) : "阶段"}完成${artifact ? ` → ${artifact}` : ""}`,
      };
    default:
      return {
        id,
        at,
        tone: "info",
        text: [message.event, stage ? stageLabel(stage) : null, iteration ? `第${iteration}集` : null, artifact]
          .filter(Boolean)
          .join(" · "),
      };
  }
}

export function liveActivityFromMessage(message: StreamMessage): string | null {
  const iteration = typeof message.data.iteration === "number" ? message.data.iteration : null;
  switch (message.event) {
    case "season_started":
      return "正在做整季规划…";
    case "season_completed":
      return "整季规划已完成，准备分集规划…";
    case "episode_plan_ready":
      return "分集规划已就绪，等待继续…";
    case "episode_started":
      return iteration ? `正在生成第 ${iteration} 集正文…` : "正在生成分集正文…";
    case "episode_completed":
      return iteration ? `第 ${iteration} 集已写入，继续下一集…` : "分集已写入…";
    case "final_assembly_started":
      return "正在合并整季成稿…";
    case "final_assembly_completed":
      return "成稿合并完成";
    case "run_paused":
      return "已暂停，可修改规划或继续生成";
    case "run_resumed":
      return "已恢复，继续生成中…";
    case "run_completed":
      return "生成完成";
    case "run_cancelled":
      return "已停止";
    case "run_failed":
      return "生成失败";
    default:
      return null;
  }
}
