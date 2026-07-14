type ControlBarProps = {
  status?: string | null;
  controlPhase?: string | null;
  busy?: boolean;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
};

export function ControlBar({ status, controlPhase, busy = false, onPause, onResume, onCancel }: ControlBarProps) {
  if (!status) {
    return null;
  }

  const canPause = status === "running";
  const showResume = status === "paused" || status === "cancelled";
  const canCancel = status === "running" || status === "paused";

  return (
    <div className="control-bar">
      <div className="control-copy">
        {status === "paused" && controlPhase === "awaiting_plan_review"
          ? "分集规划已就绪，可先修改规划，再继续生成。"
          : status === "paused"
            ? "生成已暂停。可修改后续规划，或重生成已完成的集数后再继续。"
            : status === "running"
              ? "生成进行中。可随时暂停或停止（在当前集/阶段边界生效）。"
              : null}
      </div>
      <div className="control-actions">
        <button type="button" className="btn-secondary" disabled={!canPause || busy} onClick={onPause}>
          暂停
        </button>
        <button type="button" className="btn-secondary" disabled={!showResume || busy} onClick={onResume}>
          继续生成
        </button>
        <button type="button" className="btn-danger" disabled={!canCancel || busy} onClick={onCancel}>
          停止
        </button>
      </div>
    </div>
  );
}
