# Dramaloop Prose Prompt Tightening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tighten Dramaloop’s generated output so the live case reads like a continuous Chinese short-drama-style short story instead of screenplay-style beat formatting, then rerun the live case and compare the results.

**Architecture:** Keep the generation pipeline unchanged and concentrate the behavior change in the two text-generation prompt builders: `build_draft_prompt()` and `build_rewrite_prompt()`. Lock the new prose contract with regression tests, then verify the change against the existing revenge-story live case using the current Anthropic-compatible DeepSeek configuration.

**Tech Stack:** Python 3.11+, Typer CLI, Pydantic models, Anthropic-compatible LLM adapter, pytest, uv

## Global Constraints

- Modify runtime behavior only through `src/dramaloop/prompts/draft.py` and `src/dramaloop/prompts/rewrite.py`; do not change the orchestrator, schemas, or CLI flow for this feature.
- Treat `length="short"` as a prose-oriented target of roughly `1800-2500` Chinese characters/words for this pass.
- The output target is continuous Chinese short-story prose with strong short-drama hook, escalation, reversal, and payoff.
- The prose should feel natural and mature, not like screenplay text, beat sheets, stage directions, or translated English script formatting.
- Ban Beat/Scene/Act headings, character-label script blocks such as `**SHE**` / `**HE**`, bracketed stage directions, camera directions, and `FADE OUT`-style endings.
- Preserve the existing artifact structure under `runs/` and the existing CLI command `uv run dramaloop run --input examples/inputs/revenge_story.yaml`.
- Use `examples/inputs/revenge_story.yaml` as the live verification case and compare against `runs/20260708-193221-story/final_story.md` as the known pre-change baseline.

---

## File Map

- `src/dramaloop/prompts/draft.py` — strengthen the initial drafting contract so the first full story is generated as Chinese prose, using richer premise/character/outline detail and explicit bans on screenplay formatting.
- `src/dramaloop/prompts/rewrite.py` — preserve the same prose contract during targeted rewrites and require the model to return the full revised story, not a partial patch.
- `tests/unit/test_stage_builders.py` — add regression coverage for the new draft and rewrite prompt contracts.
- `runs/<timestamp>-story/` — generated runtime artifacts used to validate that the live case actually changes shape after the prompt update.

### Task 1: Tighten the draft-generation prompt contract

**Files:**
- Modify: `tests/unit/test_stage_builders.py`
- Modify: `src/dramaloop/prompts/draft.py`

**Interfaces:**
- Consumes: `build_draft_prompt(premise: PremiseArtifact, characters: CharacterArtifact, outline: OutlineArtifact) -> str`
- Produces: a draft prompt that explicitly requires prose form, length guidance, banned screenplay markers, and richer story context for the model

- [ ] **Step 1: Write the failing draft-prompt regression test**

Append the following helpers and test to `tests/unit/test_stage_builders.py` below the existing imports and tests:

```python
from dramaloop.prompts.draft import build_draft_prompt
from dramaloop.schemas.character import CharacterArtifact, CharacterCard
from dramaloop.schemas.outline import OutlineArtifact, StoryBeat
from dramaloop.schemas.premise import PremiseArtifact


def _sample_premise() -> PremiseArtifact:
    return PremiseArtifact(
        title_candidate="退婚后我嫁给了他的死对头",
        logline="被未婚夫当众退婚后，女主转身和他的死对头结婚，在名利场里一步步完成反杀。",
        core_conflict="女主既要报复背叛她的前未婚夫，也要在新婚联盟里拿回尊严和主动权。",
        hook_promise="婚礼当天被抛弃，新郎和旧爱高调现身羞辱女主。",
        ending_payoff_plan="前未婚夫在公开场合亲眼看着女主赢回名声、利益和感情主动权。",
        tone_notes=["都市情感", "逆袭", "短剧感", "成文自然"],
        hard_constraints=["节奏快", "结尾有回报"],
    )


def _sample_characters() -> CharacterArtifact:
    return CharacterArtifact(
        characters=[
            CharacterCard(
                name="沈砚秋",
                role="protagonist",
                public_identity="被临场退婚的豪门千金",
                core_desire="拿回尊严并让背叛者付出代价",
                core_fear="再次在众人面前成为笑话",
                hidden_secret="她早就掌握未婚夫转移资产的证据",
                conflict_links=["周既白", "顾承凛"],
                voice_style="克制冷静，受刺激时格外锋利",
                arc_target="从被动受辱变成主动设局者",
            ),
            CharacterCard(
                name="顾承凛",
                role="supporting",
                public_identity="前未婚夫的死对头，也是掌控媒体资源的资本新贵",
                core_desire="借合作婚姻反制商业宿敌",
                core_fear="自己的真心被当成另一场交易",
                hidden_secret="他多年前就注意到女主，只是一直没有介入",
                conflict_links=["沈砚秋", "周既白"],
                voice_style="寡言、强势、偶尔带嘲讽",
                arc_target="从冷眼旁观变成公开站队女主",
            ),
        ]
    )


def _sample_outline() -> OutlineArtifact:
    return OutlineArtifact(
        beats=[
            StoryBeat(
                beat_id="b1",
                label="婚礼羞辱",
                purpose="开场钩子",
                summary="婚礼现场，前未婚夫当众抛下女主，带着旧爱离场。",
                tension_level=10,
            ),
            StoryBeat(
                beat_id="b2",
                label="危险联盟",
                purpose="建立新关系",
                summary="死对头提出闪婚合作，让女主把羞辱反手变成新闻。",
                tension_level=8,
            ),
            StoryBeat(
                beat_id="b3",
                label="名利场反击",
                purpose="升级冲突",
                summary="女主借助新婚身份和手中证据，反向逼迫前未婚夫失去资源。",
                tension_level=9,
            ),
            StoryBeat(
                beat_id="b4",
                label="感情试探",
                purpose="补强人物关系",
                summary="女主意识到顾承凛并不只是利用她，两人的关系开始失控。",
                tension_level=7,
            ),
            StoryBeat(
                beat_id="b5",
                label="公开回报",
                purpose="结尾 payoff",
                summary="公开晚宴上，前未婚夫身败名裂，女主拿回尊严与主动权。",
                tension_level=10,
            ),
        ],
        ending_type="revenge payoff",
    )


def test_draft_prompt_requires_continuous_chinese_prose_contract() -> None:
    prompt = build_draft_prompt(_sample_premise(), _sample_characters(), _sample_outline())

    assert "连续中文短篇正文" in prompt
    assert "1800-2500字" in prompt
    assert "不要使用 Beat 1/Beat 2、Scene、Act、小标题分幕" in prompt
    assert "不要使用 **SHE**、**HE**、人物名大写标签" in prompt
    assert "以叙事为主，只在关键冲突处穿插少量短对白" in prompt
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
uv run pytest tests/unit/test_stage_builders.py::test_draft_prompt_requires_continuous_chinese_prose_contract -v
```

Expected: FAIL because `build_draft_prompt()` currently returns a short English prompt without the new Chinese prose contract strings.

- [ ] **Step 3: Replace the draft prompt with a prose-first contract**

Replace the body of `build_draft_prompt()` in `src/dramaloop/prompts/draft.py` with the following implementation:

```python
from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.outline import OutlineArtifact
from dramaloop.schemas.premise import PremiseArtifact



def build_draft_prompt(premise: PremiseArtifact, characters: CharacterArtifact, outline: OutlineArtifact) -> str:
    tone_notes = "、".join(premise.tone_notes) or "都市情感、逆袭、短剧感"
    hard_constraints = "；".join(premise.hard_constraints) or "节奏快；结尾有回报"
    character_lines = "\n".join(
        f"- {card.name}（{card.role}）：身份={card.public_identity}；想要={card.core_desire}；害怕={card.core_fear}；口吻={card.voice_style}；人物走向={card.arc_target}"
        for card in characters.characters
    )
    beat_lines = "\n".join(
        f"- {beat.label}：{beat.summary}（作用：{beat.purpose}；张力：{beat.tension_level}/10）"
        for beat in outline.beats
    )
    return "\n".join(
        [
            "你是中文短剧感短篇小说写手，不是编剧，不是分镜师。",
            f"标题候选：{premise.title_candidate}",
            f"一句话梗概：{premise.logline}",
            f"核心冲突：{premise.core_conflict}",
            f"开场钩子承诺：{premise.hook_promise}",
            f"结尾回报承诺：{premise.ending_payoff_plan}",
            f"风格关键词：{tone_notes}",
            f"硬约束：{hard_constraints}",
            "任务：写一篇1800-2500字的连续中文短篇正文，整体要有都市情感短剧的钩子、反转、打脸和情绪回报，但成文必须自然成熟。",
            "输出硬性要求：",
            "1. 必须直接输出连续故事正文，不要写提纲、说明、分析或自我解释。",
            "2. 不要使用 Beat 1/Beat 2、Scene、Act、小标题分幕。",
            "3. 不要使用 **SHE**、**HE**、人物名大写标签、人物名+冒号轮流对白、方括号舞台说明、镜头说明、FADE OUT 等脚本格式。",
            "4. 以叙事为主，只在关键冲突处穿插少量短对白，让对白服务于打脸、反转和情绪爆点。",
            "5. 开头两段内进入羞辱、背叛或利益冲突，随后持续升级矛盾，中后段给出明确反转，结尾给足回报。",
            "6. 语言要像自然中文短篇，不要像英文翻译腔，不要空喊口号，不要重复同义句。",
            "主要人物：",
            character_lines,
            "故事节拍：",
            beat_lines,
        ]
    )
```

- [ ] **Step 4: Run the stage-builder unit test file and verify it passes**

Run:

```bash
uv run pytest tests/unit/test_stage_builders.py -v
```

Expected: PASS, including the new draft-prompt regression test and the two existing prompt/stage-chain tests.

- [ ] **Step 5: Commit the draft prompt tightening**

```bash
git add tests/unit/test_stage_builders.py src/dramaloop/prompts/draft.py
git commit -m "feat: tighten dramaloop draft prose prompt"
```

### Task 2: Preserve the prose contract during targeted rewrites

**Files:**
- Modify: `tests/unit/test_stage_builders.py`
- Modify: `src/dramaloop/prompts/rewrite.py`

**Interfaces:**
- Consumes: `build_rewrite_prompt(draft_markdown: str, critique: CritiqueArtifact, premise: PremiseArtifact, characters: CharacterArtifact, outline: OutlineArtifact) -> str`
- Produces: a rewrite prompt that keeps the same prose-only contract, focuses edits on the weak area, and still requires the full revised story as output

- [ ] **Step 1: Add the failing rewrite-prompt regression test**

Extend `tests/unit/test_stage_builders.py` with the following imports, helper, and test:

```python
from dramaloop.prompts.rewrite import build_rewrite_prompt
from dramaloop.schemas.critique import CritiqueArtifact, DimensionCritique, RewritePlan



def _sample_critique() -> CritiqueArtifact:
    common_dimension = DimensionCritique(
        score=7,
        reason="基本达标",
        evidence="冲突和节奏都有雏形",
        improvement_advice="需要进一步强化回报与收束",
    )
    return CritiqueArtifact(
        dimension_scores={
            "hook_strength": common_dimension,
            "character_consistency": common_dimension,
            "conflict_intensity": common_dimension,
            "pacing": common_dimension,
            "short_drama_feel": common_dimension,
            "ending_payoff": DimensionCritique(
                score=5,
                reason="结尾力度不足",
                evidence="前未婚夫的惩罚来得太轻，女主回报不够痛快",
                improvement_advice="让结尾反杀落在公开场合，并补足女主情绪回收",
            ),
            "language_fluency": common_dimension,
        },
        overall_score=6.7,
        weakest_dimensions=["ending_payoff"],
        rewrite_target="ending_payoff",
        rewrite_plan=RewritePlan(
            scope="最后三段",
            must_fix=["补强公开反杀", "让女主拿回情绪主动权"],
            keep=["婚礼退婚开场", "顾承凛与女主的危险联盟"],
        ),
    )


def test_rewrite_prompt_requires_full_prose_rewrite_contract() -> None:
    prompt = build_rewrite_prompt(
        "这里是一版仍然偏脚本腔的初稿。",
        _sample_critique(),
        _sample_premise(),
        _sample_characters(),
        _sample_outline(),
    )

    assert "输出完整修订后全文" in prompt
    assert "连续中文短篇正文" in prompt
    assert "不要使用 Beat 1/Beat 2、Scene、Act、小标题分幕" in prompt
    assert "不要使用 **SHE**、**HE**、人物名大写标签" in prompt
    assert "只集中改动目标段落及其前后衔接，但成稿要整体顺滑" in prompt
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
uv run pytest tests/unit/test_stage_builders.py::test_rewrite_prompt_requires_full_prose_rewrite_contract -v
```

Expected: FAIL because the current rewrite prompt only says to rewrite the weak section and does not lock prose form or require returning the full revised story.

- [ ] **Step 3: Replace the rewrite prompt with a full-text prose rewrite contract**

Replace the body of `build_rewrite_prompt()` in `src/dramaloop/prompts/rewrite.py` with the following implementation:

```python
from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.outline import OutlineArtifact
from dramaloop.schemas.premise import PremiseArtifact



def build_rewrite_prompt(
    draft_markdown: str,
    critique: CritiqueArtifact,
    premise: PremiseArtifact,
    characters: CharacterArtifact,
    outline: OutlineArtifact,
) -> str:
    tone_notes = "、".join(premise.tone_notes) or "都市情感、逆袭、短剧感"
    must_fix = "；".join(critique.rewrite_plan.must_fix) or "无"
    keep = "；".join(critique.rewrite_plan.keep) or "无"
    character_lines = "\n".join(
        f"- {card.name}：目标={card.core_desire}；恐惧={card.core_fear}；人物走向={card.arc_target}"
        for card in characters.characters
    )
    beat_lines = "\n".join(
        f"- {beat.label}：{beat.summary}（作用：{beat.purpose}）"
        for beat in outline.beats
    )
    return "\n".join(
        [
            "你是中文短剧感短篇小说的修订编辑，不是编剧医生。",
            f"本轮改写目标：{critique.rewrite_target}",
            f"重点改写范围：{critique.rewrite_plan.scope}",
            f"必须修复：{must_fix}",
            f"必须保留：{keep}",
            f"核心冲突：{premise.core_conflict}",
            f"风格关键词：{tone_notes}",
            "任务：在保留现有故事主线的前提下，重点修补指定弱点，但输出必须是完整修订后全文，而不是局部片段。",
            "改写硬性要求：",
            "1. 输出完整修订后全文，长度仍控制在1800-2500字。",
            "2. 保持连续中文短篇正文形式，不要改成提纲、脚本、分幕或舞台说明。",
            "3. 不要使用 Beat 1/Beat 2、Scene、Act、小标题分幕。",
            "4. 不要使用 **SHE**、**HE**、人物名大写标签、人物名+冒号轮流对白、方括号舞台说明、镜头说明、FADE OUT 等脚本格式。",
            "5. 只集中改动目标段落及其前后衔接，但成稿要整体顺滑，人物关系和事件因果不能断。",
            "6. 保留已有强项，尤其保留 must keep 中的内容；强化短剧感，但语言仍要自然、成熟、像中文短篇。",
            "主要人物：",
            character_lines,
            "故事节拍：",
            beat_lines,
            "当前草稿：",
            draft_markdown,
        ]
    )
```

- [ ] **Step 4: Run the stage-builder unit test file and verify it passes**

Run:

```bash
uv run pytest tests/unit/test_stage_builders.py -v
```

Expected: PASS, including both new regression tests for draft and rewrite prompt contracts.

- [ ] **Step 5: Commit the rewrite prompt tightening**

```bash
git add tests/unit/test_stage_builders.py src/dramaloop/prompts/rewrite.py
git commit -m "feat: preserve prose contract during rewrite"
```

### Task 3: Rerun the live case and compare against the screenplay-style baseline

**Files:**
- Generate: `runs/<new-run-id>/draft_v1.md`
- Generate: `runs/<new-run-id>/final_story.md`
- Generate: `runs/<new-run-id>/run_summary.md`

**Interfaces:**
- Consumes: `uv run dramaloop run --input examples/inputs/revenge_story.yaml`
- Produces: a new `runs/<timestamp>-story/` directory whose `final_story.md` can be compared with `runs/20260708-193221-story/final_story.md`

- [ ] **Step 1: Run the prompt-focused unit tests before the live call**

Run:

```bash
uv run pytest tests/unit/test_stage_builders.py -v
```

Expected: PASS

- [ ] **Step 2: Rerun the revenge-story live case and capture the new run directory**

Run:

```bash
RUN_DIR=$(uv run dramaloop run --input examples/inputs/revenge_story.yaml)
printf '%s\n' "$RUN_DIR"
```

Expected: stdout is a single path like `runs/20260708-221530-story` and the command exits `0`.

- [ ] **Step 3: Inspect the new run summary**

Run:

```bash
uv run dramaloop inspect "$RUN_DIR"
```

Expected: `status: completed` plus an `overall_scores:` line and a `weakest_dimensions:` line.

- [ ] **Step 4: Compare the new final story against the old baseline with an explicit prose-format check**

Run:

```bash
python - <<'PY'
from pathlib import Path

baseline_path = Path("runs/20260708-193221-story/final_story.md")
run_dir = Path(input().strip())
new_story_path = run_dir / "final_story.md"

baseline = baseline_path.read_text(encoding="utf-8")
new_story = new_story_path.read_text(encoding="utf-8")

banned_tokens = ["**SHE**", "**HE**", "Beat 1", "Beat 2", "Scene", "Act", "FADE OUT", "["]

print({
    "run_dir": run_dir.as_posix(),
    "baseline_has_script_markers": any(token in baseline for token in banned_tokens),
    "new_has_script_markers": any(token in new_story for token in banned_tokens),
    "baseline_length": len(baseline),
    "new_length": len(new_story),
    "baseline_preview": baseline[:120],
    "new_preview": new_story[:120],
})
PY
```

When prompted for stdin, paste the exact `$RUN_DIR` value from Step 2.

Expected:
- `baseline_has_script_markers` is `True`
- `new_has_script_markers` is `False`
- `new_length` is materially longer than the old screenplay-style output and lands near the `1800-2500` target window
- `new_preview` reads like prose narration rather than a beat heading

- [ ] **Step 5: Commit the prompt-tuning verification result**

```bash
git add src/dramaloop/prompts/draft.py src/dramaloop/prompts/rewrite.py tests/unit/test_stage_builders.py
git commit -m "feat: tune dramaloop prompts for prose output"
```
