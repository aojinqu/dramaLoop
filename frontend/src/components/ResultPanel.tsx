import { useEffect, useMemo, useState } from "react";
import { runStatusLabel } from "../labels";
import type { EpisodePlanItem, SeasonBible, WebRunDetail } from "../types";

type ResultTab = "season" | "plan" | "episodes" | "final";

type ResultPanelProps = {
  detail: WebRunDetail | null;
  runId: string | null;
  onSavePlan?: (episodes: EpisodePlanItem[]) => Promise<void>;
  onRegenerate?: (episodeNumber: number) => Promise<void>;
  controlBusy?: boolean;
};

function asStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function SeasonView({ bible, summary }: { bible?: SeasonBible | null; summary?: string | null }) {
  if (!bible && !summary) {
    return <p className="empty-hint">整季规划完成后，这里会展示系列设定与主线。</p>;
  }

  if (!bible) {
    return (
      <div className="story-shell">
        <p>{summary}</p>
      </div>
    );
  }

  const arcs = asStringList(bible.main_character_arcs);
  const beats = asStringList(bible.must_land_beats);

  return (
    <div className="plan-grid">
      <article className="plan-card">
        <h3>{bible.title_candidate || "季标题"}</h3>
        <p className="plan-lead">{bible.series_logline || summary}</p>
        {bible.core_conflict ? (
          <dl className="meta-list">
            <div>
              <dt>核心冲突</dt>
              <dd>{bible.core_conflict}</dd>
            </div>
            {bible.final_payoff ? (
              <div>
                <dt>最终回报</dt>
                <dd>{bible.final_payoff}</dd>
              </div>
            ) : null}
            {bible.target_episode_count ? (
              <div>
                <dt>规划集数</dt>
                <dd>{bible.target_episode_count}</dd>
              </div>
            ) : null}
          </dl>
        ) : null}
      </article>
      {arcs.length ? (
        <article className="plan-card">
          <h3>人物弧线</h3>
          <ul className="bullet-list">
            {arcs.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      ) : null}
      {beats.length ? (
        <article className="plan-card">
          <h3>必落节拍</h3>
          <ul className="bullet-list">
            {beats.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
      ) : null}
    </div>
  );
}

function PlanView({
  items,
  editable,
  busy,
  onSave,
}: {
  items: EpisodePlanItem[];
  editable: boolean;
  busy: boolean;
  onSave?: (episodes: EpisodePlanItem[]) => Promise<void>;
}) {
  const [draft, setDraft] = useState<EpisodePlanItem[]>(items);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setDraft(items);
  }, [items]);

  if (!items.length) {
    return <p className="empty-hint">分集规划完成后，这里会列出每集冲突与钩子。</p>;
  }

  const updateItem = (episodeNumber: number, patch: Partial<EpisodePlanItem>) => {
    setDraft((current) =>
      current.map((item) => (item.episode_number === episodeNumber ? { ...item, ...patch } : item)),
    );
  };

  return (
    <div className="episode-list">
      {editable ? (
        <div className="plan-toolbar">
          <p className="empty-hint" style={{ margin: 0 }}>
            可编辑标题、冲突、开场与钩子。保存后点「继续生成」。
          </p>
          <button
            type="button"
            disabled={busy || saving || !onSave}
            onClick={async () => {
              if (!onSave) return;
              setSaving(true);
              setMessage(null);
              try {
                await onSave(draft);
                setMessage("规划已保存");
              } catch {
                setMessage("保存失败");
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? "保存中…" : "保存规划"}
          </button>
          {message ? <span className="plan-save-msg">{message}</span> : null}
        </div>
      ) : null}

      {draft.map((item) => (
        <article key={item.episode_number} className="episode-card">
          {editable ? (
            <>
              <label className="field">
                <span>第{item.episode_number}集标题</span>
                <input
                  aria-label={`第${item.episode_number}集标题`}
                  value={item.title}
                  onChange={(event) => updateItem(item.episode_number, { title: event.target.value })}
                />
              </label>
              <label className="field">
                <span>开场</span>
                <textarea
                  aria-label={`第${item.episode_number}集开场`}
                  rows={3}
                  value={item.opening_situation ?? ""}
                  onChange={(event) => updateItem(item.episode_number, { opening_situation: event.target.value })}
                />
              </label>
              <label className="field">
                <span>核心冲突</span>
                <textarea
                  aria-label={`第${item.episode_number}集核心冲突`}
                  rows={2}
                  value={item.core_conflict ?? ""}
                  onChange={(event) => updateItem(item.episode_number, { core_conflict: event.target.value })}
                />
              </label>
              <label className="field">
                <span>必发生（逗号分隔）</span>
                <input
                  aria-label={`第${item.episode_number}集必发生情节`}
                  value={(item.must_happen ?? []).join("，")}
                  onChange={(event) =>
                    updateItem(item.episode_number, {
                      must_happen: event.target.value
                        .split(/[,，]/)
                        .map((value) => value.trim())
                        .filter(Boolean),
                    })
                  }
                />
              </label>
              <label className="field">
                <span>结尾钩子</span>
                <textarea
                  aria-label={`第${item.episode_number}集结尾钩子`}
                  rows={2}
                  value={item.hook_ending ?? ""}
                  onChange={(event) => updateItem(item.episode_number, { hook_ending: event.target.value })}
                />
              </label>
              <label className="field">
                <span>承接下一集</span>
                <textarea
                  aria-label={`第${item.episode_number}集承接下一集`}
                  rows={2}
                  value={item.sets_up_next ?? ""}
                  onChange={(event) => updateItem(item.episode_number, { sets_up_next: event.target.value })}
                />
              </label>
            </>
          ) : (
            <>
              <h3>
                第{item.episode_number}集 · {item.title}
              </h3>
              {item.opening_situation ? <p>{item.opening_situation}</p> : null}
              {item.core_conflict ? (
                <p>
                  <strong>冲突：</strong>
                  {item.core_conflict}
                </p>
              ) : null}
              {asStringList(item.must_happen).length ? (
                <ul className="bullet-list compact">
                  {asStringList(item.must_happen).map((beat) => (
                    <li key={beat}>{beat}</li>
                  ))}
                </ul>
              ) : null}
              {item.hook_ending ? <small>Hook：{item.hook_ending}</small> : null}
            </>
          )}
        </article>
      ))}
    </div>
  );
}

export function ResultPanel({ detail, runId, onSavePlan, onRegenerate, controlBusy = false }: ResultPanelProps) {
  const episodes = useMemo(() => detail?.episodes ?? [], [detail?.episodes]);
  const planItems = detail?.episode_plan?.episodes ?? [];
  const hasFinal = Boolean(detail?.final_story);
  const artifacts = detail?.available_artifacts ?? [];
  const editable =
    detail?.status === "paused" || detail?.status === "cancelled" || detail?.status === "completed";
  const canRegenerate =
    Boolean(onRegenerate) &&
    !detail?.has_live_controller &&
    (detail?.status === "paused" || detail?.status === "cancelled" || detail?.status === "completed");

  const defaultTab: ResultTab = hasFinal
    ? "final"
    : episodes.length
      ? "episodes"
      : planItems.length
        ? "plan"
        : "season";

  const [tab, setTab] = useState<ResultTab>(defaultTab);
  const [selectedEpisode, setSelectedEpisode] = useState<number | null>(null);

  useEffect(() => {
    setTab(defaultTab);
  }, [defaultTab, detail?.run_id]);

  useEffect(() => {
    if (!episodes.length) {
      setSelectedEpisode(null);
      return;
    }
    setSelectedEpisode((current) => {
      if (current && episodes.some((item) => item.episode_number === current)) {
        return current;
      }
      return episodes[episodes.length - 1]?.episode_number ?? null;
    });
  }, [episodes]);

  const activeEpisode = useMemo(
    () => episodes.find((item) => item.episode_number === selectedEpisode) ?? null,
    [episodes, selectedEpisode],
  );

  const tabs: { id: ResultTab; label: string; ready: boolean }[] = [
    { id: "season", label: "整季规划", ready: Boolean(detail?.season_bible || detail?.season_summary) },
    { id: "plan", label: "分集规划", ready: planItems.length > 0 },
    { id: "episodes", label: "分集正文", ready: episodes.length > 0 },
    { id: "final", label: "合并成稿", ready: hasFinal },
  ];

  return (
    <section className="panel result-panel">
      <div className="result-main">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Workspace</p>
            <h2>内容工作区</h2>
          </div>
          {detail ? (
            <span className="completion-badge">
              {detail.completed_episode_count}/{detail.request.episode_count} 集
            </span>
          ) : null}
        </div>

        <div className="result-tabs" role="tablist" aria-label="结果分区">
          {tabs.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={tab === item.id}
              className={tab === item.id ? "tab active" : "tab"}
              onClick={() => setTab(item.id)}
            >
              {item.label}
              {item.ready ? <span className="tab-dot" /> : null}
            </button>
          ))}
        </div>

        <div className="result-body">
          {!detail ? (
            <div className="workspace-empty">
              <span className="workspace-empty-mark" aria-hidden="true">✦</span>
              <h3>从一个故事想法开始</h3>
              <p>系统会先生成整季与分集规划，确认后再逐集创作。</p>
            </div>
          ) : null}

          {detail && tab === "season" ? <SeasonView bible={detail.season_bible} summary={detail.season_summary} /> : null}

          {detail && tab === "plan" ? (
            <PlanView items={planItems} editable={editable && planItems.length > 0} busy={controlBusy} onSave={onSavePlan} />
          ) : null}

          {detail && tab === "episodes" ? (
            episodes.length ? (
              <div className="episode-reader">
                <div className="episode-nav">
                  {episodes.map((episode) => (
                    <button
                      key={episode.episode_number}
                      type="button"
                      className={
                        selectedEpisode === episode.episode_number ? "episode-chip active" : "episode-chip"
                      }
                      onClick={() => setSelectedEpisode(episode.episode_number)}
                    >
                      第{episode.episode_number}集
                    </button>
                  ))}
                </div>
                {activeEpisode ? (
                  <article className="episode-card reading">
                    <div className="episode-header-row">
                      <h3>
                        第{activeEpisode.episode_number}集 · {activeEpisode.title}
                        {typeof activeEpisode.overall_score === "number" ? (
                          <span className="score-badge" title="本集质量分">
                            {activeEpisode.overall_score.toFixed(1)}
                          </span>
                        ) : null}
                      </h3>
                      {canRegenerate ? (
                        <button
                          type="button"
                          className="btn-secondary"
                          disabled={controlBusy}
                          onClick={() => onRegenerate?.(activeEpisode.episode_number)}
                        >
                          重生成本集
                        </button>
                      ) : null}
                    </div>
                    {activeEpisode.word_count ? (
                      <p className="episode-meta">{activeEpisode.word_count} 字</p>
                    ) : null}
                    <div className="story-shell episode-shell">
                      <p>{activeEpisode.content ?? "正文生成中…"}</p>
                    </div>
                    {activeEpisode.hook_line ? <small>Hook：{activeEpisode.hook_line}</small> : null}
                  </article>
                ) : null}
              </div>
            ) : (
              <p className="empty-hint">{runId ? "正在等待分集正文…" : "分集正文会在逐集生成阶段出现。"}</p>
            )
          ) : null}

          {detail && tab === "final" ? (
            hasFinal ? (
              <div className="story-shell final-shell">
                <p>{detail?.final_story}</p>
              </div>
            ) : (
              <p className="empty-hint">{runId ? "最终合并完成后会展示完整成稿。" : "合并成稿会在全部流程结束后出现。"}</p>
            )
          ) : null}
        </div>
      </div>

      <aside className="result-side">
        <div className="summary-card">
          <div className="side-card-title">
            <h3>任务概览</h3>
            {detail ? <span>{runStatusLabel(detail.status)}</span> : null}
          </div>
          {detail ? (
            <dl>
              <div>
                <dt>创意</dt>
                <dd className="summary-idea">{detail.request.idea}</dd>
              </div>
              <div>
                <dt>进度</dt>
                <dd>{detail.completed_episode_count} / {detail.request.episode_count} 集</dd>
              </div>
              <div>
                <dt>题材</dt>
                <dd>{detail.request.style.join(" / ") || "—"}</dd>
              </div>
              <div>
                <dt>字数范围</dt>
                <dd>
                  {detail.request.episode_min_words}–{detail.request.episode_max_words}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="empty-hint">创建任务后显示。</p>
          )}
        </div>
        <div className="summary-card">
          <details className="artifact-details">
            <summary>
              <span>生成产物</span>
              <small>{artifacts.length}</small>
            </summary>
            {artifacts.length ? (
              <ul>
                {artifacts.map((artifact) => (
                  <li key={artifact}>{artifact}</li>
                ))}
              </ul>
            ) : (
              <p className="empty-hint">暂无产物</p>
            )}
          </details>
        </div>
      </aside>
    </section>
  );
}
