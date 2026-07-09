type RunFormProps = {
  onSubmit?: () => void;
};

export function RunForm({ onSubmit }: RunFormProps) {
  return (
    <form
      className="panel run-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit?.();
      }}
    >
      <div className="panel-header">
        <p className="eyebrow">Launch Config</p>
        <h2>Story Input</h2>
      </div>
      <label className="field">
        <span>Idea</span>
        <textarea aria-label="Idea" name="idea" placeholder="输入短剧故事核心设定" rows={6} />
      </label>
      <label className="field">
        <span>Style tags</span>
        <input name="style" placeholder="都市情感, 逆袭, 狗血短剧感" />
      </label>
      <label className="field">
        <span>Audience</span>
        <input name="audience" placeholder="女性向短剧用户" />
      </label>
      <label className="field">
        <span>Constraints</span>
        <input name="constraints" placeholder="节奏快, 结尾有回报" />
      </label>
      <button type="submit">Launch Run</button>
    </form>
  );
}
