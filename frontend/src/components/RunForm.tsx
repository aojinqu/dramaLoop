import { useState } from "react";
import type { RunFormInput } from "../types";

type RunFormProps = {
  onSubmit?: (input: RunFormInput) => void | Promise<void>;
};

export function RunForm({ onSubmit }: RunFormProps) {
  const [idea, setIdea] = useState("");
  const [style, setStyle] = useState("");
  const [audience, setAudience] = useState("");
  const [constraints, setConstraints] = useState("");

  return (
    <form
      className="panel run-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit?.({
          idea,
          style: style
            .split(",")
            .map((value) => value.trim())
            .filter(Boolean),
          audience,
          constraints: constraints
            .split(",")
            .map((value) => value.trim())
            .filter(Boolean),
          max_iterations: 2,
          format: "episodic_series",
          episode_count: 12,
          episode_min_words: 500,
          episode_max_words: 800,
          delivery_mode: "stream_and_final",
        });
      }}
    >
      <div className="panel-header">
        <p className="eyebrow">Launch Config</p>
        <h2>Story Input</h2>
      </div>
      <label className="field">
        <span>Idea</span>
        <textarea
          aria-label="Idea"
          name="idea"
          placeholder="输入短剧故事核心设定"
          rows={6}
          value={idea}
          onChange={(event) => setIdea(event.target.value)}
        />
      </label>
      <label className="field">
        <span>Style tags</span>
        <input
          aria-label="Style tags"
          name="style"
          placeholder="都市情感, 逆袭, 狗血短剧感"
          value={style}
          onChange={(event) => setStyle(event.target.value)}
        />
      </label>
      <label className="field">
        <span>Audience</span>
        <input
          aria-label="Audience"
          name="audience"
          placeholder="女性向短剧用户"
          value={audience}
          onChange={(event) => setAudience(event.target.value)}
        />
      </label>
      <label className="field">
        <span>Constraints</span>
        <input
          aria-label="Constraints"
          name="constraints"
          placeholder="节奏快, 结尾有回报"
          value={constraints}
          onChange={(event) => setConstraints(event.target.value)}
        />
      </label>
      <button type="submit">Launch Run</button>
    </form>
  );
}
