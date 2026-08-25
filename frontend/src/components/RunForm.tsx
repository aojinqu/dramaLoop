import { useState } from "react";
import type { RunFormInput } from "../types";

type RunFormProps = {
  onSubmit?: (input: RunFormInput) => void | Promise<void>;
  disabled?: boolean;
  error?: string | null;
};

function parseTags(value: string): string[] {
  return value
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function RunForm({ onSubmit, disabled = false, error = null }: RunFormProps) {
  const [idea, setIdea] = useState("");
  const [style, setStyle] = useState("都市情感");
  const [audience, setAudience] = useState("女性向短剧用户");
  const [constraints, setConstraints] = useState("节奏快, 结尾有回报");
  const [episodeCount, setEpisodeCount] = useState(3);
  const [episodeMinWords, setEpisodeMinWords] = useState(500);
  const [episodeMaxWords, setEpisodeMaxWords] = useState(800);
  const [localError, setLocalError] = useState<string | null>(null);

  const validationError = localError ?? error;

  return (
    <form
      className="panel run-form"
      onSubmit={(event) => {
        event.preventDefault();
        setLocalError(null);

        const styles = parseTags(style);
        if (!idea.trim()) {
          setLocalError("请填写故事创意 / prompt");
          return;
        }
        if (styles.length === 0) {
          setLocalError("请至少填写一个题材标签");
          return;
        }
        if (episodeMinWords > episodeMaxWords) {
          setLocalError("每集最少字数不能大于最多字数");
          return;
        }

        void onSubmit?.({
          idea: idea.trim(),
          style: styles,
          audience: audience.trim(),
          constraints: parseTags(constraints),
          max_iterations: 2,
          format: "episodic_series",
          episode_count: episodeCount,
          episode_min_words: episodeMinWords,
          episode_max_words: episodeMaxWords,
          delivery_mode: "stream_and_final",
          pause_after_plan: true,
        });
      }}
    >
      <div className="panel-header">
        <div>
          <p className="eyebrow">Create</p>
          <h2>新建短剧</h2>
        </div>
        <span className="form-step">01</span>
      </div>

      <label className="field">
        <span>故事创意</span>
        <textarea
          aria-label="Idea"
          name="idea"
          placeholder="例如：一个普通人意外获得重来一次的机会，决定改写自己失败的人生"
          rows={5}
          value={idea}
          disabled={disabled}
          onChange={(event) => setIdea(event.target.value)}
        />
        <small>用一句话说明主角、冲突和核心反转。</small>
      </label>

      <label className="field">
        <span>题材标签</span>
        <input
          aria-label="Style tags"
          name="style"
          placeholder="都市情感, 逆袭, 重生"
          value={style}
          disabled={disabled}
          onChange={(event) => setStyle(event.target.value)}
        />
      </label>

      <div className="field-row field-row--primary">
        <label className="field">
          <span>集数</span>
          <input
            aria-label="Episode count"
            name="episode_count"
            type="number"
            min={1}
            max={12}
            value={episodeCount}
            disabled={disabled}
            onChange={(event) => setEpisodeCount(Number(event.target.value) || 1)}
          />
        </label>
        <div className="field field-static">
          <span>工作模式</span>
          <strong>规划后确认</strong>
        </div>
      </div>

      <details className="advanced-settings">
        <summary>高级设置</summary>
        <div className="field-row">
          <label className="field">
            <span>最少字数</span>
            <input
              aria-label="Episode min words"
              name="episode_min_words"
              type="number"
              min={100}
              step={50}
              value={episodeMinWords}
              disabled={disabled}
              onChange={(event) => setEpisodeMinWords(Number(event.target.value) || 100)}
            />
          </label>
          <label className="field">
            <span>最多字数</span>
            <input
              aria-label="Episode max words"
              name="episode_max_words"
              type="number"
              min={100}
              step={50}
              value={episodeMaxWords}
              disabled={disabled}
              onChange={(event) => setEpisodeMaxWords(Number(event.target.value) || 100)}
            />
          </label>
        </div>
        <label className="field">
          <span>目标受众</span>
          <input
            aria-label="Audience"
            name="audience"
            placeholder="女性向短剧用户"
            value={audience}
            disabled={disabled}
            onChange={(event) => setAudience(event.target.value)}
          />
        </label>
        <label className="field">
          <span>创作约束</span>
          <input
            aria-label="Constraints"
            name="constraints"
            placeholder="节奏快, 结尾有回报"
            value={constraints}
            disabled={disabled}
            onChange={(event) => setConstraints(event.target.value)}
          />
        </label>
      </details>

      {validationError ? <p className="form-error" role="alert">{validationError}</p> : null}

      <button type="submit" className="launch-button" disabled={disabled}>
        <span>{disabled ? "生成中…" : "开始创作"}</span>
        <span aria-hidden="true">→</span>
      </button>
    </form>
  );
}
