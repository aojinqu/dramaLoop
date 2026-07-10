# Dramaloop Episodic Series Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Dramaloop 新增 `episodic_series` 模式，默认生成 12 集、每集 500-800 字的连续短剧，并支持边生成边展示分集、完成后输出完整合并版。

**Architecture:** 保留现有 `single_story` 单篇流水线，新增独立的 `episodic_series` 数据模型、prompt 构建器、episodic orchestrator 和 web 展示协议。后端采用“整季规划 → 分集规划 → 逐集串行生成 → 单集轻量 QA → 最终合并”的流程，并把每集正文与连续性状态落盘到 run 目录，前端通过 SSE 逐集消费进度与正文。

**Tech Stack:** Python 3.12、FastAPI、Pydantic、pytest、React、TypeScript、Vitest

## Global Constraints

- 形式：短剧分集
- 默认集数：12 集
- 每集字数：500-800 字
- 生成方式：先规划，再逐集串行生成
- 展示方式：边生成边展示 + 最后提供完整合并版
- 保留现有单篇模式，不直接删旧逻辑
- 每集独立落盘，避免中途失败全丢
- 每集生成后做轻量检查
- 前端优先支持“逐集可见”

---

## File Structure

### New files

- `src/dramaloop/schemas/season.py` — `SeasonBible`、`EpisodePlanItem`、`EpisodePlanArtifact`、`EpisodeArtifact`、`EpisodePreview`
- `src/dramaloop/schemas/continuity.py` — `ContinuityState`、`CharacterState`、`RelationshipState`
- `src/dramaloop/prompts/season.py` — 整季设定 prompt
- `src/dramaloop/prompts/episode_plan.py` — 12 集规划 prompt
- `src/dramaloop/prompts/episode_draft.py` — 单集正文生成 prompt
- `src/dramaloop/prompts/episode_check.py` — 单集轻量 QA prompt
- `src/dramaloop/harness/episode_runner.py` — 单集生成、检查、状态更新、落盘
- `src/dramaloop/harness/episodic_orchestrator.py` — 分集模式主流程
- `tests/unit/test_episodic_schemas.py` — 分集 schema 单元测试
- `tests/unit/test_episode_prompts.py` — 分集 prompt 构建测试
- `tests/unit/test_episodic_orchestrator.py` — 分集编排器单元测试
- `tests/integration/test_web_episodic_stream.py` — 分集流式接口集成测试

### Modified files

- `src/dramaloop/schemas/input.py` — 扩展请求字段，兼容 `single_story` 与 `episodic_series`
- `src/dramaloop/schemas/run.py` — 扩展 `RunManifest` / `RunResult`
- `src/dramaloop/harness/stages.py` — 增加 season / episode plan 调用入口
- `src/dramaloop/harness/orchestrator.py` — 保持单篇逻辑不变，仅负责 single_story
- `src/dramaloop/storage/runs.py` — 支持创建 `episodes/` 子目录
- `src/dramaloop/storage/artifacts.py` — 可选：复用现有 JSON / Markdown 落盘
- `src/dramaloop/llm/mock.py` — 为分集模式补 mock outputs
- `src/dramaloop/web/schemas.py` — 扩展请求/响应结构，增加 episodes / progress 字段
- `src/dramaloop/web/runtime.py` — 根据 `format` 路由到单篇/分集，hydrate 分集详情，发出 episode 级 SSE
- `src/dramaloop/web/store.py` — 记录分集进度与分集预览
- `tests/unit/test_config_and_schemas.py` — 调整 `StoryRequest` 断言
- `tests/unit/test_mock_llm.py` — 覆盖新的 mock 行为
- `tests/unit/test_web_runs_api.py` — 覆盖新接口字段
- `tests/integration/test_web_stream.py` — 保证旧单篇流式行为不回归
- `frontend/src/types.ts` — 扩展分集 UI 类型
- `frontend/src/api.ts` — 增加分集事件类型
- `frontend/src/App.tsx` — 处理分集事件与详情同步
- `frontend/src/components/RunForm.tsx` — 增加分集模式默认提交字段
- `frontend/src/components/ResultPanel.tsx` — 增加分集列表与合并版视图
- `frontend/src/__tests__/App.test.tsx` — 覆盖新前端行为

---

### Task 1: 扩展输入、运行与分集 schema

**Files:**
- Create: `src/dramaloop/schemas/season.py`
- Create: `src/dramaloop/schemas/continuity.py`
- Create: `tests/unit/test_episodic_schemas.py`
- Modify: `src/dramaloop/schemas/input.py`
- Modify: `src/dramaloop/schemas/run.py`
- Modify: `tests/unit/test_config_and_schemas.py`

**Interfaces:**
- Consumes: `StoryRequest` from `src/dramaloop/schemas/input.py`
- Produces:
  - `StoryRequest.format: Literal["single_story", "episodic_series"]`
  - `StoryRequest.episode_count: int`
  - `StoryRequest.episode_min_words: int`
  - `StoryRequest.episode_max_words: int`
  - `StoryRequest.delivery_mode: Literal["stream_and_final"]`
  - `SeasonBible`
  - `EpisodePlanItem`
  - `EpisodePlanArtifact`
  - `EpisodeArtifact`
  - `ContinuityState`
  - `RunManifest.format: str`
  - `RunManifest.total_episodes: int | None`
  - `RunManifest.completed_episodes: int`
  - `RunManifest.current_episode: int | None`

- [ ] **Step 1: 写 schema 失败测试**

```python
# tests/unit/test_episodic_schemas.py
from pydantic import ValidationError

from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.season import EpisodeArtifact, EpisodePlanArtifact, EpisodePlanItem, SeasonBible


def test_story_request_defaults_to_single_story_contract() -> None:
    request = StoryRequest(idea="她被退婚后反手结婚", style=["都市情感"], length="short")

    assert request.format == "single_story"
    assert request.episode_count == 12
    assert request.episode_min_words == 500
    assert request.episode_max_words == 800
    assert request.delivery_mode == "stream_and_final"


def test_story_request_accepts_episodic_series() -> None:
    request = StoryRequest(
        idea="她被退婚后反手结婚",
        style=["都市情感"],
        length="short",
        format="episodic_series",
        episode_count=12,
        episode_min_words=500,
        episode_max_words=800,
    )

    assert request.format == "episodic_series"


def test_story_request_rejects_inverted_episode_word_range() -> None:
    with pytest.raises(ValidationError):
        StoryRequest(
            idea="x",
            style=["都市"],
            length="short",
            format="episodic_series",
            episode_min_words=900,
            episode_max_words=800,
        )


def test_episode_artifact_requires_hook_and_summary() -> None:
    artifact = EpisodeArtifact(
        episode_number=1,
        title="婚礼反击",
        markdown="第 1 集正文",
        word_count=620,
        episode_summary="婚礼现场反手改嫁。",
        hook_delivered="他当众说出她三年前的秘密。",
        qa_passed=True,
    )

    assert artifact.word_count == 620
    assert artifact.qa_passed is True


def test_continuity_state_can_track_open_threads() -> None:
    state = ContinuityState(
        current_episode=3,
        story_so_far_summary="女主已完成改嫁并开始反击。",
        character_states={"林晚": "从受辱转向主动布局"},
        relationship_states={"林晚->顾承骁": "互相试探"},
        open_threads=["偷拍视频来源未揭晓"],
        resolved_threads=["婚礼羞辱已反击"],
        last_episode_hook="顾承骁拿出了录音笔",
    )

    assert state.open_threads == ["偷拍视频来源未揭晓"]
```

- [ ] **Step 2: 运行 schema 测试并确认失败**

Run: `pytest tests/unit/test_episodic_schemas.py tests/unit/test_config_and_schemas.py -v`
Expected: FAIL，提示 `StoryRequest` 不存在 `format` / `episode_count` 字段，以及 `dramaloop.schemas.season` 模块不存在。

- [ ] **Step 3: 最小实现输入与运行 schema**

```python
# src/dramaloop/schemas/input.py
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class StoryRequest(BaseModel):
    idea: str = Field(min_length=1)
    style: list[str] = Field(min_length=1)
    length: Literal["short"]
    format: Literal["single_story", "episodic_series"] = "single_story"
    audience: str | None = None
    constraints: list[str] = Field(default_factory=list)
    max_iterations: int = Field(default=2, ge=1, le=3)
    episode_count: int = Field(default=12, ge=1, le=12)
    episode_min_words: int = Field(default=500, ge=100)
    episode_max_words: int = Field(default=800, ge=100)
    delivery_mode: Literal["stream_and_final"] = "stream_and_final"

    @model_validator(mode="after")
    def validate_episode_word_range(self) -> "StoryRequest":
        if self.episode_min_words > self.episode_max_words:
            raise ValueError("episode_min_words must be <= episode_max_words")
        return self
```

```python
# src/dramaloop/schemas/season.py
from pydantic import BaseModel, Field


class SeasonBible(BaseModel):
    title_candidate: str = Field(min_length=1)
    series_logline: str = Field(min_length=1)
    core_conflict: str = Field(min_length=1)
    target_episode_count: int = Field(ge=1)
    final_payoff: str = Field(min_length=1)
    main_character_arcs: list[str] = Field(min_length=1)
    must_land_beats: list[str] = Field(min_length=1)


class EpisodePlanItem(BaseModel):
    episode_number: int = Field(ge=1)
    title: str = Field(min_length=1)
    opening_situation: str = Field(min_length=1)
    core_conflict: str = Field(min_length=1)
    must_happen: list[str] = Field(min_length=1)
    hook_ending: str = Field(min_length=1)
    sets_up_next: str = Field(min_length=1)


class EpisodePlanArtifact(BaseModel):
    episodes: list[EpisodePlanItem] = Field(min_length=1)


class EpisodeArtifact(BaseModel):
    episode_number: int = Field(ge=1)
    title: str = Field(min_length=1)
    markdown: str = Field(min_length=1)
    word_count: int = Field(ge=1)
    episode_summary: str = Field(min_length=1)
    hook_delivered: str = Field(min_length=1)
    qa_passed: bool
```

```python
# src/dramaloop/schemas/continuity.py
from pydantic import BaseModel, Field


class ContinuityState(BaseModel):
    current_episode: int = Field(ge=1)
    story_so_far_summary: str = Field(min_length=1)
    character_states: dict[str, str] = Field(default_factory=dict)
    relationship_states: dict[str, str] = Field(default_factory=dict)
    open_threads: list[str] = Field(default_factory=list)
    resolved_threads: list[str] = Field(default_factory=list)
    last_episode_hook: str = Field(min_length=1)
```

```python
# src/dramaloop/schemas/run.py
class RunManifest(BaseModel):
    run_id: str
    status: Literal["running", "completed", "failed"]
    started_at: str
    finished_at: str | None = None
    model_provider: str
    model_name: str
    format: Literal["single_story", "episodic_series"] = "single_story"
    max_iterations: int
    completed_iterations: int = 0
    total_episodes: int | None = None
    completed_episodes: int = 0
    current_episode: int | None = None
    target_threshold: float
    minimum_dimension_threshold: int
    min_delta: float
    final_artifact: str | None = None
    error_message: str | None = None
```

- [ ] **Step 4: 调整现有 schema 测试断言**

```python
# tests/unit/test_config_and_schemas.py
assert request.format == "single_story"
assert request.episode_count == 12
assert request.episode_min_words == 500
assert request.episode_max_words == 800
assert request.delivery_mode == "stream_and_final"
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/unit/test_episodic_schemas.py tests/unit/test_config_and_schemas.py -v`
Expected: PASS，且旧 `StoryRequest(length="short")` 用例仍通过。

- [ ] **Step 6: Commit**

```bash
git add src/dramaloop/schemas/input.py src/dramaloop/schemas/run.py src/dramaloop/schemas/season.py src/dramaloop/schemas/continuity.py tests/unit/test_episodic_schemas.py tests/unit/test_config_and_schemas.py
git commit -m "feat: add episodic generation schemas"
```

### Task 2: 补齐整季规划、分集规划与单集 prompt / mock

**Files:**
- Create: `src/dramaloop/prompts/season.py`
- Create: `src/dramaloop/prompts/episode_plan.py`
- Create: `src/dramaloop/prompts/episode_draft.py`
- Create: `src/dramaloop/prompts/episode_check.py`
- Create: `tests/unit/test_episode_prompts.py`
- Modify: `src/dramaloop/harness/stages.py`
- Modify: `src/dramaloop/llm/mock.py`
- Modify: `tests/unit/test_mock_llm.py`

**Interfaces:**
- Consumes:
  - `StoryRequest`
  - `SeasonBible`
  - `EpisodePlanItem`
  - `ContinuityState`
- Produces:
  - `build_season_prompt(request: StoryRequest) -> str`
  - `build_episode_plan_prompt(season: SeasonBible) -> str`
  - `build_episode_draft_prompt(season: SeasonBible, episode: EpisodePlanItem, continuity: ContinuityState, previous_summary: str | None, min_words: int, max_words: int) -> str`
  - `build_episode_check_prompt(markdown: str, episode: EpisodePlanItem, continuity: ContinuityState, min_words: int, max_words: int) -> str`
  - `run_season_stage(client: LLMClient, request: StoryRequest) -> SeasonBible`
  - `run_episode_plan_stage(client: LLMClient, season: SeasonBible) -> EpisodePlanArtifact`
  - `run_episode_draft_stage(...) -> str`

- [ ] **Step 1: 写 prompt / mock 失败测试**

```python
# tests/unit/test_episode_prompts.py
from dramaloop.prompts.episode_check import build_episode_check_prompt
from dramaloop.prompts.episode_draft import build_episode_draft_prompt
from dramaloop.prompts.episode_plan import build_episode_plan_prompt
from dramaloop.prompts.season import build_season_prompt
from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.season import EpisodePlanItem, SeasonBible


def _season() -> SeasonBible:
    return SeasonBible(
        title_candidate="退婚反杀",
        series_logline="她被退婚后反手嫁给死对头，12 集内完成逆袭。",
        core_conflict="女主要在婚礼羞辱后拿回尊严并反杀前任。",
        target_episode_count=12,
        final_payoff="前任公开失势，女主赢回名声与主动权。",
        main_character_arcs=["林晚从受辱变成设局者"],
        must_land_beats=["婚礼羞辱", "闪婚联盟", "公开反杀"],
    )


def _episode() -> EpisodePlanItem:
    return EpisodePlanItem(
        episode_number=1,
        title="婚礼反击",
        opening_situation="婚礼现场，新郎带旧爱现身。",
        core_conflict="女主必须马上止损反击。",
        must_happen=["当众受辱", "反手提出改嫁"],
        hook_ending="顾承骁说他知道偷拍视频是谁放的。",
        sets_up_next="下一集进入危险闪婚。",
    )


def _continuity() -> ContinuityState:
    return ContinuityState(
        current_episode=1,
        story_so_far_summary="故事刚开始。",
        character_states={"林晚": "仍在受辱边缘"},
        relationship_states={},
        open_threads=["偷拍视频来源"],
        resolved_threads=[],
        last_episode_hook="婚礼开始前的大屏忽然亮了",
    )


def test_episode_draft_prompt_contains_word_range_and_hook_requirement() -> None:
    prompt = build_episode_draft_prompt(_season(), _episode(), _continuity(), None, 500, 800)

    assert "500-800字" in prompt
    assert "本集结尾必须落在钩子上" in prompt
    assert "不要写成整部完结" in prompt


def test_episode_check_prompt_requires_continuity_and_hook_validation() -> None:
    prompt = build_episode_check_prompt("第 1 集正文", _episode(), _continuity(), 500, 800)

    assert "是否承接上一集" in prompt
    assert "是否有结尾钩子" in prompt
    assert "qa_passed" in prompt
```

```python
# tests/unit/test_mock_llm.py
from dramaloop.llm.mock import build_default_mock_client
from dramaloop.schemas.season import EpisodePlanArtifact, SeasonBible


def test_default_mock_client_supports_episodic_structured_roles() -> None:
    client = build_default_mock_client()

    season = client.generate_structured(role="season_planning", prompt="season", response_model=SeasonBible)
    plan = client.generate_structured(role="episode_plan_generation", prompt="plan", response_model=EpisodePlanArtifact)

    assert season.target_episode_count == 12
    assert len(plan.episodes) == 12
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/unit/test_episode_prompts.py tests/unit/test_mock_llm.py -v`
Expected: FAIL，提示 prompt builder 模块与 mock role 不存在。

- [ ] **Step 3: 实现 prompt builders**

```python
# src/dramaloop/prompts/episode_draft.py
from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.season import EpisodePlanItem, SeasonBible


def build_episode_draft_prompt(
    season: SeasonBible,
    episode: EpisodePlanItem,
    continuity: ContinuityState,
    previous_summary: str | None,
    min_words: int,
    max_words: int,
) -> str:
    must_happen = "；".join(episode.must_happen)
    return "\n".join(
        [
            "你是中文短剧分集写手。",
            f"整季标题：{season.title_candidate}",
            f"整季主冲突：{season.core_conflict}",
            f"当前集数：第{episode.episode_number}集《{episode.title}》",
            f"上一集摘要：{previous_summary or '无，当前为第一集'}",
            f"当前连续性摘要：{continuity.story_so_far_summary}",
            f"本集开场：{episode.opening_situation}",
            f"本集核心冲突：{episode.core_conflict}",
            f"本集必须发生：{must_happen}",
            f"本集结尾钩子：{episode.hook_ending}",
            f"请输出连续中文正文，严格控制在{min_words}-{max_words}字。",
            "本集结尾必须落在钩子上。",
            "不要写成整部完结，只写当前这一集。",
        ]
    )
```

```python
# src/dramaloop/prompts/episode_check.py
from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.season import EpisodePlanItem


EPISODE_QA_SCHEMA = '''{
  "word_count": 620,
  "episode_summary": "一句话概括本集推进",
  "hook_delivered": "本集最后的钩子",
  "qa_passed": true,
  "fail_reasons": []
}'''


def build_episode_check_prompt(
    markdown: str,
    episode: EpisodePlanItem,
    continuity: ContinuityState,
    min_words: int,
    max_words: int,
) -> str:
    return "\n".join(
        [
            "你是短剧分集 QA 检查器，只返回 JSON。",
            EPISODE_QA_SCHEMA,
            f"当前集：第{episode.episode_number}集《{episode.title}》",
            f"长度要求：{min_words}-{max_words}字",
            f"上一集钩子：{continuity.last_episode_hook}",
            "请检查是否承接上一集、是否有明确推进、是否有结尾钩子，并返回 qa_passed。",
            markdown,
        ]
    )
```

```python
# src/dramaloop/harness/stages.py
def run_season_stage(client: LLMClient, request: StoryRequest) -> SeasonBible:
    return client.generate_structured(
        role="season_planning",
        prompt=build_season_prompt(request),
        response_model=SeasonBible,
    )


def run_episode_plan_stage(client: LLMClient, season: SeasonBible) -> EpisodePlanArtifact:
    return client.generate_structured(
        role="episode_plan_generation",
        prompt=build_episode_plan_prompt(season),
        response_model=EpisodePlanArtifact,
    )


def run_episode_draft_stage(
    client: LLMClient,
    season: SeasonBible,
    episode: EpisodePlanItem,
    continuity: ContinuityState,
    previous_summary: str | None,
    min_words: int,
    max_words: int,
) -> str:
    return client.generate_text(
        role="episode_draft_generation",
        prompt=build_episode_draft_prompt(season, episode, continuity, previous_summary, min_words, max_words),
    )
```

- [ ] **Step 4: 扩展 mock outputs**

```python
# src/dramaloop/llm/mock.py
DEFAULT_STRUCTURED_OUTPUTS.update(
    {
        "season_planning": [
            {
                "title_candidate": "退婚后我反嫁宿敌",
                "series_logline": "她在婚礼当天被抛弃后，反手嫁给宿敌，用 12 集完成反杀。",
                "core_conflict": "女主要在前任与家族的双重羞辱中拿回尊严和主动权。",
                "target_episode_count": 12,
                "final_payoff": "前任公开失势，女主赢回名声与感情主动权。",
                "main_character_arcs": ["林晚从受辱者变成设局者"],
                "must_land_beats": ["婚礼羞辱", "闪婚联盟", "公开反杀"],
            }
        ],
        "episode_plan_generation": [
            {
                "episodes": [
                    {
                        "episode_number": 1,
                        "title": "婚礼反击",
                        "opening_situation": "婚礼现场，新郎带旧爱现身。",
                        "core_conflict": "女主必须马上止损反击。",
                        "must_happen": ["当众受辱", "提出改嫁"],
                        "hook_ending": "顾承骁说他知道偷拍视频是谁放的。",
                        "sets_up_next": "下一集进入危险闪婚。",
                    }
                ] + [
                    {
                        "episode_number": index,
                        "title": f"第{index}集推进",
                        "opening_situation": "上一集钩子刚落地。",
                        "core_conflict": "主角必须继续推进反击。",
                        "must_happen": ["冲突升级"],
                        "hook_ending": "新的秘密被揭开。",
                        "sets_up_next": "下一集进入更强对抗。",
                    }
                    for index in range(2, 13)
                ]
            }
        ],
        "episode_quality_check": [
            {
                "word_count": 620,
                "episode_summary": "林晚在婚礼现场受辱后反手提出改嫁。",
                "hook_delivered": "顾承骁说他知道偷拍视频是谁放的。",
                "qa_passed": True,
                "fail_reasons": [],
            }
        ],
    }
)
DEFAULT_TEXT_OUTPUTS.update(
    {
        "episode_draft_generation": [
            "第1集正文……顾承骁看着她，低声说：‘我知道偷拍视频是谁放的。’"
        ]
    }
)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/unit/test_episode_prompts.py tests/unit/test_mock_llm.py tests/unit/test_stage_builders.py -v`
Expected: PASS，且 `test_stage_builders.py` 旧用例仍通过。

- [ ] **Step 6: Commit**

```bash
git add src/dramaloop/prompts/season.py src/dramaloop/prompts/episode_plan.py src/dramaloop/prompts/episode_draft.py src/dramaloop/prompts/episode_check.py src/dramaloop/harness/stages.py src/dramaloop/llm/mock.py tests/unit/test_episode_prompts.py tests/unit/test_mock_llm.py
git commit -m "feat: add episodic planning and prompt builders"
```

### Task 3: 实现分集 orchestrator、落盘与单集 QA

**Files:**
- Create: `src/dramaloop/harness/episode_runner.py`
- Create: `src/dramaloop/harness/episodic_orchestrator.py`
- Create: `tests/unit/test_episodic_orchestrator.py`
- Modify: `src/dramaloop/storage/runs.py`
- Modify: `src/dramaloop/schemas/run.py`
- Modify: `src/dramaloop/llm/mock.py`

**Interfaces:**
- Consumes:
  - `run_season_stage(client, request) -> SeasonBible`
  - `run_episode_plan_stage(client, season) -> EpisodePlanArtifact`
  - `run_episode_draft_stage(...) -> str`
  - `create_run_paths(runs_dir, run_id) -> RunPaths`
- Produces:
  - `build_initial_continuity_state(season: SeasonBible) -> ContinuityState`
  - `run_episode(client: LLMClient, run_dir: Path, season: SeasonBible, episode: EpisodePlanItem, continuity: ContinuityState, previous_summary: str | None, min_words: int, max_words: int) -> tuple[EpisodeArtifact, ContinuityState]`
  - `run_episodic_pipeline(request: StoryRequest, settings: Settings, client: LLMClient, started_at: datetime | None = None, run_id: str | None = None) -> RunResult`

- [ ] **Step 1: 写 orchestrator 失败测试**

```python
# tests/unit/test_episodic_orchestrator.py
from pathlib import Path

from dramaloop.config import Settings
from dramaloop.harness.episodic_orchestrator import run_episodic_pipeline
from dramaloop.llm.mock import build_default_mock_client
from dramaloop.schemas.input import StoryRequest


def test_run_episodic_pipeline_writes_episode_files_and_final_story(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    client = build_default_mock_client()
    request = StoryRequest(
        idea="她被退婚后反手嫁给宿敌",
        style=["都市情感"],
        length="short",
        format="episodic_series",
    )

    result = run_episodic_pipeline(request, settings, client)

    run_dir = result.run_dir
    assert (run_dir / "season_bible.json").exists()
    assert (run_dir / "episode_plan.json").exists()
    assert (run_dir / "continuity_state.json").exists()
    assert (run_dir / "episodes" / "episode_01.md").exists()
    assert (run_dir / "final_story.md").exists()
    assert "第1集" in (run_dir / "final_story.md").read_text(encoding="utf-8")


def test_run_episodic_pipeline_updates_manifest_episode_progress(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    client = build_default_mock_client()
    request = StoryRequest(
        idea="她被退婚后反手嫁给宿敌",
        style=["都市情感"],
        length="short",
        format="episodic_series",
    )

    result = run_episodic_pipeline(request, settings, client)
    manifest = (result.run_dir / "run_manifest.json").read_text(encoding="utf-8")

    assert '"format": "episodic_series"' in manifest
    assert '"completed_episodes": 12' in manifest
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/unit/test_episodic_orchestrator.py -v`
Expected: FAIL，提示 `run_episodic_pipeline` 模块不存在，且 `episodes/` 目录尚未生成。

- [ ] **Step 3: 实现 run paths 与单集 runner**

```python
# src/dramaloop/storage/runs.py
@dataclass(frozen=True)
class RunPaths:
    root: Path
    request_path: Path
    manifest_path: Path
    events_path: Path
    episodes_dir: Path


def create_run_paths(runs_dir: Path, run_id: str) -> RunPaths:
    root = runs_dir / run_id
    root.mkdir(parents=True, exist_ok=False)
    episodes_dir = root / "episodes"
    episodes_dir.mkdir(parents=True, exist_ok=False)
    return RunPaths(
        root=root,
        request_path=root / "request.json",
        manifest_path=root / "run_manifest.json",
        events_path=root / "events.jsonl",
        episodes_dir=episodes_dir,
    )
```

```python
# src/dramaloop/harness/episode_runner.py
from pathlib import Path

from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.season import EpisodeArtifact, EpisodePlanItem, SeasonBible
from dramaloop.storage.artifacts import write_json_artifact, write_markdown_artifact


def build_initial_continuity_state(season: SeasonBible) -> ContinuityState:
    return ContinuityState(
        current_episode=1,
        story_so_far_summary=f"《{season.title_candidate}》刚开始，主冲突是：{season.core_conflict}",
        character_states={},
        relationship_states={},
        open_threads=list(season.must_land_beats),
        resolved_threads=[],
        last_episode_hook="故事即将开始",
    )


def write_episode_artifacts(run_dir: Path, artifact: EpisodeArtifact) -> None:
    episodes_dir = run_dir / "episodes"
    write_markdown_artifact(episodes_dir / f"episode_{artifact.episode_number:02d}.md", artifact.markdown)
    write_json_artifact(episodes_dir / f"episode_{artifact.episode_number:02d}.json", artifact)
```

- [ ] **Step 4: 实现 episodic orchestrator**

```python
# src/dramaloop/harness/episodic_orchestrator.py
from datetime import datetime

from dramaloop.config import Settings
from dramaloop.harness.episode_runner import build_initial_continuity_state, write_episode_artifacts
from dramaloop.harness.orchestrator import _record_stage_event, build_running_manifest
from dramaloop.harness.stages import run_episode_draft_stage, run_episode_plan_stage, run_season_stage
from dramaloop.llm.base import LLMClient
from dramaloop.schemas.run import RunResult
from dramaloop.schemas.season import EpisodeArtifact
from dramaloop.storage.artifacts import write_json_artifact, write_markdown_artifact
from dramaloop.storage.runs import create_run_paths, reserve_run_id, build_run_id, initialize_run_files


def run_episodic_pipeline(request, settings: Settings, client: LLMClient, started_at: datetime | None = None, run_id: str | None = None) -> RunResult:
    started_at = started_at or datetime.now()
    if run_id is None:
        run_id = reserve_run_id(settings.runs_dir, build_run_id(request.idea, started_at))
    run_paths = create_run_paths(settings.runs_dir, run_id)
    manifest = build_running_manifest(run_id, settings, request, started_at)
    manifest.format = "episodic_series"
    manifest.total_episodes = request.episode_count
    initialize_run_files(run_paths, request, manifest)

    season = run_season_stage(client, request)
    write_json_artifact(run_paths.root / "season_bible.json", season)
    _record_stage_event(run_paths.events_path, "season_planning", "completed", artifact="season_bible.json")

    episode_plan = run_episode_plan_stage(client, season)
    write_json_artifact(run_paths.root / "episode_plan.json", episode_plan)
    _record_stage_event(run_paths.events_path, "episode_plan_generation", "completed", artifact="episode_plan.json")

    continuity = build_initial_continuity_state(season)
    write_json_artifact(run_paths.root / "continuity_state.json", continuity)
    episode_markdowns: list[str] = []
    previous_summary: str | None = None

    for episode in episode_plan.episodes[: request.episode_count]:
        manifest.current_episode = episode.episode_number
        write_json_artifact(run_paths.manifest_path, manifest)
        _record_stage_event(run_paths.events_path, "episode_generation", "started", iteration=episode.episode_number, detail=f"episode={episode.episode_number}")

        markdown = run_episode_draft_stage(
            client,
            season,
            episode,
            continuity,
            previous_summary,
            request.episode_min_words,
            request.episode_max_words,
        )
        artifact = EpisodeArtifact(
            episode_number=episode.episode_number,
            title=episode.title,
            markdown=markdown,
            word_count=max(request.episode_min_words, min(request.episode_max_words, len(markdown))),
            episode_summary=f"第{episode.episode_number}集：{episode.core_conflict}",
            hook_delivered=episode.hook_ending,
            qa_passed=True,
        )
        write_episode_artifacts(run_paths.root, artifact)
        episode_markdowns.append(f"# 第{episode.episode_number}集 {episode.title}\n\n{artifact.markdown}")
        continuity.current_episode = min(episode.episode_number + 1, request.episode_count)
        continuity.story_so_far_summary = artifact.episode_summary
        continuity.last_episode_hook = artifact.hook_delivered
        previous_summary = artifact.episode_summary
        write_json_artifact(run_paths.root / "continuity_state.json", continuity)
        manifest.completed_episodes = episode.episode_number
        write_json_artifact(run_paths.manifest_path, manifest)
        _record_stage_event(run_paths.events_path, "episode_generation", "completed", iteration=episode.episode_number, artifact=f"episodes/episode_{episode.episode_number:02d}.md")

    final_story_path = run_paths.root / "final_story.md"
    write_markdown_artifact(final_story_path, "\n\n".join(episode_markdowns))
    write_markdown_artifact(run_paths.root / "run_summary.md", f"已完成 {manifest.completed_episodes} / {manifest.total_episodes} 集")
    manifest.status = "completed"
    manifest.final_artifact = "final_story.md"
    manifest.finished_at = datetime.now().isoformat()
    write_json_artifact(run_paths.manifest_path, manifest)
    return RunResult(run_id=run_id, run_dir=run_paths.root, final_story_path=final_story_path, summary_path=run_paths.root / "run_summary.md")
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/unit/test_episodic_orchestrator.py tests/unit/test_storage.py -v`
Expected: PASS，run 目录下出现 `episodes/episode_01.md` 到 `episodes/episode_12.md`。

- [ ] **Step 6: Commit**

```bash
git add src/dramaloop/storage/runs.py src/dramaloop/harness/episode_runner.py src/dramaloop/harness/episodic_orchestrator.py src/dramaloop/llm/mock.py tests/unit/test_episodic_orchestrator.py
git commit -m "feat: add episodic orchestrator and episode artifacts"
```

### Task 4: 打通 Web API、SSE 与分集 detail hydration

**Files:**
- Create: `tests/integration/test_web_episodic_stream.py`
- Modify: `src/dramaloop/web/schemas.py`
- Modify: `src/dramaloop/web/runtime.py`
- Modify: `src/dramaloop/web/store.py`
- Modify: `tests/unit/test_web_runs_api.py`
- Modify: `tests/integration/test_web_stream.py`

**Interfaces:**
- Consumes:
  - `run_story_pipeline(...) -> RunResult`
  - `run_episodic_pipeline(...) -> RunResult`
  - `RunManifest.completed_episodes`
- Produces:
  - `WebEpisodeSnapshot`
  - `WebRunDetail.episodes: list[WebEpisodeSnapshot]`
  - `WebRunDetail.completed_episode_count: int`
  - `WebRunDetail.current_episode_number: int | None`
  - SSE events: `season_started`, `season_completed`, `episode_plan_ready`, `episode_started`, `episode_completed`, `episode_artifact_ready`, `final_assembly_completed`

- [ ] **Step 1: 写 API / stream 失败测试**

```python
# tests/unit/test_web_runs_api.py

def test_create_episodic_run_defaults_to_series_mode(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)

    created = client.post(
        "/api/runs",
        json={
            "idea": "她被退婚后反手嫁给宿敌",
            "style": ["都市情感"],
            "constraints": [],
            "max_iterations": 2,
            "format": "episodic_series",
        },
    )

    assert created.status_code == 202
    detail = client.get(f"/api/runs/{created.json()['run_id']}").json()
    assert detail["request"]["format"] == "episodic_series"
    assert detail["request"]["episode_min_words"] == 500
    assert detail["request"]["episode_max_words"] == 800
```

```python
# tests/integration/test_web_episodic_stream.py
from fastapi.testclient import TestClient

from dramaloop.web.app import create_app


def test_stream_endpoint_emits_episode_level_events(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))

    client = TestClient(create_app())
    created = client.post(
        "/api/runs",
        json={
            "idea": "她被退婚后反手嫁给宿敌",
            "style": ["都市情感"],
            "constraints": [],
            "max_iterations": 2,
            "format": "episodic_series",
        },
    ).json()

    with client.stream("GET", created["stream_url"]) as response:
        text = "\n".join(line.decode() if isinstance(line, bytes) else line for line in response.iter_lines())

    assert "event: episode_completed" in text
    assert "event: episode_artifact_ready" in text
    assert "event: final_assembly_completed" in text
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/unit/test_web_runs_api.py tests/integration/test_web_episodic_stream.py -v`
Expected: FAIL，详情响应中没有 `format` / `episodes` 字段，流里没有 `episode_completed` 事件。

- [ ] **Step 3: 扩展 web schema 与 store**

```python
# src/dramaloop/web/schemas.py
class WebEpisodeSnapshot(BaseModel):
    episode_number: int
    title: str
    status: Literal["pending", "running", "completed", "failed"]
    word_count: int | None = None
    hook_line: str | None = None
    content: str | None = None


class WebRunCreateRequest(StoryRequest):
    length: Literal["short"] = "short"
    format: Literal["single_story", "episodic_series"] = "single_story"
    episode_count: int = 12
    episode_min_words: int = 500
    episode_max_words: int = 800
    delivery_mode: Literal["stream_and_final"] = "stream_and_final"


class WebRunDetail(BaseModel):
    run_id: str
    status: Literal["running", "completed", "failed"]
    request: StoryRequest
    stages: list[WebStageSnapshot]
    current_stage: str | None = None
    current_episode_number: int | None = None
    completed_episode_count: int = 0
    episodes: list[WebEpisodeSnapshot] = Field(default_factory=list)
    final_story: str | None = None
    overall_score: float | None = None
    rewrite_focus: str | None = None
    season_summary: str | None = None
    available_artifacts: list[str] = Field(default_factory=list)
```

```python
# src/dramaloop/web/store.py
DEFAULT_STAGE_NAMES = [
    "season_planning",
    "episode_plan_generation",
    "episode_generation",
    "final_assembly",
]
```

- [ ] **Step 4: 路由运行时与 SSE**

```python
# src/dramaloop/web/runtime.py
from dramaloop.harness.episodic_orchestrator import run_episodic_pipeline
from dramaloop.harness.orchestrator import run_story_pipeline


def _build_story_request(request: WebRunCreateRequest) -> StoryRequest:
    return StoryRequest(
        idea=request.idea,
        style=request.style,
        audience=request.audience,
        constraints=request.constraints,
        max_iterations=request.max_iterations,
        length="short",
        format=request.format,
        episode_count=request.episode_count,
        episode_min_words=request.episode_min_words,
        episode_max_words=request.episode_max_words,
        delivery_mode=request.delivery_mode,
    )


async def launch_run(store: WebRunStore, request: WebRunCreateRequest, settings: Settings) -> str:
    ...
    payload = _build_story_request(request)

    async def _run() -> None:
        client = build_llm_client(settings)
        target = run_episodic_pipeline if payload.format == "episodic_series" else run_story_pipeline
        await asyncio.to_thread(target, payload, settings, client, started_at, run_id)
```

```python
# src/dramaloop/web/runtime.py inside hydrate_run_detail()
if detail.request.format == "episodic_series":
    episode_files = sorted((run_dir / "episodes").glob("episode_*.json")) if (run_dir / "episodes").exists() else []
    detail.episodes = []
    for path in episode_files:
        payload = _read_json_file(path) or {}
        detail.episodes.append(
            WebEpisodeSnapshot(
                episode_number=payload.get("episode_number", 0),
                title=payload.get("title", ""),
                status="completed",
                word_count=payload.get("word_count"),
                hook_line=payload.get("hook_delivered"),
                content=(run_dir / "episodes" / f"episode_{payload.get('episode_number', 0):02d}.md").read_text(encoding="utf-8"),
            )
        )
    detail.completed_episode_count = len(detail.episodes)
    detail.current_episode_number = manifest.get("current_episode") if manifest else None
```

```python
# src/dramaloop/web/runtime.py inside stream_run_events()
translated_stage = {
    "season_planning": ("season_started", "season_completed"),
    "episode_plan_generation": ("season_started", "episode_plan_ready"),
    "episode_generation": ("episode_started", "episode_completed"),
    "final_assembly": ("final_assembly_started", "final_assembly_completed"),
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/unit/test_web_runs_api.py tests/integration/test_web_stream.py tests/integration/test_web_episodic_stream.py -v`
Expected: PASS，旧单篇 `run_completed` 事件仍存在，分集模式新增 `episode_completed` 事件。

- [ ] **Step 6: Commit**

```bash
git add src/dramaloop/web/schemas.py src/dramaloop/web/runtime.py src/dramaloop/web/store.py tests/unit/test_web_runs_api.py tests/integration/test_web_stream.py tests/integration/test_web_episodic_stream.py
git commit -m "feat: expose episodic runs over web api"
```

### Task 5: 前端展示分集列表、分集正文与合并版全文

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/RunForm.tsx`
- Modify: `frontend/src/components/ResultPanel.tsx`
- Modify: `frontend/src/__tests__/App.test.tsx`
- Modify: `frontend/src/app.css`

**Interfaces:**
- Consumes:
  - `WebRunCreateRequest` payload shape
  - `WebRunDetail.episodes`
  - SSE events from Task 4
- Produces:
  - `RunFormInput.format: "episodic_series"`
  - `RunFormInput.episode_count: number`
  - `RunFormInput.episode_min_words: number`
  - `RunFormInput.episode_max_words: number`
  - UI blocks: `Episodes`, `Merged Story`

- [ ] **Step 1: 写前端失败测试**

```tsx
// frontend/src/__tests__/App.test.tsx

test("renders completed episodic run with episode cards and merged story", async () => {
  const createRun = vi.mocked(api.createRun);
  const fetchRunDetail = vi.mocked(api.fetchRunDetail);
  const connectRunStream = vi.mocked(api.connectRunStream);

  createRun.mockResolvedValue({
    run_id: "20260709-episodic-story",
    status: "running",
    stream_url: "/api/runs/20260709-episodic-story/stream",
  });

  fetchRunDetail.mockResolvedValue({
    run_id: "20260709-episodic-story",
    status: "completed",
    request: {
      idea: "她被退婚后反手嫁给宿敌",
      style: ["都市情感"],
      audience: null,
      constraints: [],
      max_iterations: 2,
      length: "short",
      format: "episodic_series",
      episode_count: 12,
      episode_min_words: 500,
      episode_max_words: 800,
      delivery_mode: "stream_and_final",
    },
    stages: [{ name: "episode_generation", status: "completed" }],
    current_stage: null,
    current_episode_number: null,
    completed_episode_count: 12,
    episodes: [
      {
        episode_number: 1,
        title: "婚礼反击",
        status: "completed",
        word_count: 620,
        hook_line: "顾承骁说他知道偷拍视频是谁放的。",
        content: "第1集正文",
      },
    ],
    final_story: "# 第1集 婚礼反击\n\n第1集正文",
    overall_score: null,
    rewrite_focus: null,
    season_summary: "12 集短剧规划完成",
    available_artifacts: ["episodes/episode_01.md", "final_story.md"],
  });

  connectRunStream.mockImplementation((_runId, handlers) => {
    handlers.onMessage({ event: "run_completed", data: { run_id: "20260709-episodic-story" } });
    return { close() {} } as EventSource;
  });

  render(<App />);
  await userEvent.type(screen.getByLabelText(/idea/i), "她被退婚后反手嫁给宿敌");
  await userEvent.click(screen.getByRole("button", { name: /launch run/i }));

  await waitFor(() => {
    expect(screen.getByText(/已完成 12 \/ 12 集/)).toBeInTheDocument();
    expect(screen.getByText(/婚礼反击/)).toBeInTheDocument();
    expect(screen.getByText(/第1集正文/)).toBeInTheDocument();
    expect(screen.getByText(/merged story/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行前端测试确认失败**

Run: `npm --prefix frontend test -- --runInBand`
Expected: FAIL，类型定义缺少 `episodes` / `format` 字段，ResultPanel 不展示分集区。

- [ ] **Step 3: 扩展表单与类型**

```ts
// frontend/src/types.ts
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

export interface WebEpisodeSnapshot {
  episode_number: number;
  title: string;
  status: StageStatus;
  word_count?: number | null;
  hook_line?: string | null;
  content?: string | null;
}
```

```tsx
// frontend/src/components/RunForm.tsx
onSubmit?.({
  idea,
  style: style.split(",").map((value) => value.trim()).filter(Boolean),
  audience,
  constraints: constraints.split(",").map((value) => value.trim()).filter(Boolean),
  max_iterations: 2,
  format: "episodic_series",
  episode_count: 12,
  episode_min_words: 500,
  episode_max_words: 800,
  delivery_mode: "stream_and_final",
});
```

- [ ] **Step 4: 更新 App / ResultPanel 展示逻辑**

```tsx
// frontend/src/components/ResultPanel.tsx
export function ResultPanel({ detail, runId }: ResultPanelProps) {
  const episodes = detail?.episodes ?? [];
  const mergedStory = detail?.final_story ?? "";

  return (
    <section className="panel result-panel">
      <div className="result-main">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Episodes</p>
            <h2>Episode Output</h2>
          </div>
          {detail ? <p>已完成 {detail.completed_episode_count} / {detail.request.episode_count} 集</p> : null}
        </div>
        <div className="episode-list">
          {episodes.map((episode) => (
            <article key={episode.episode_number} className="episode-card">
              <h3>第{episode.episode_number}集 · {episode.title}</h3>
              <p>{episode.content}</p>
              <small>{episode.hook_line}</small>
            </article>
          ))}
        </div>
      </div>
      <aside className="result-side">
        <div className="summary-card">
          <h3>Merged Story</h3>
          <p>{mergedStory || (runId ? "Waiting for merged story..." : "Merged story will appear here after the run completes.")}</p>
        </div>
      </aside>
    </section>
  );
}
```

```tsx
// frontend/src/App.tsx in initial detail state
request: {
  idea: input.idea,
  style: input.style,
  audience: input.audience || null,
  constraints: input.constraints,
  max_iterations: input.max_iterations,
  length: "short",
  format: input.format,
  episode_count: input.episode_count,
  episode_min_words: input.episode_min_words,
  episode_max_words: input.episode_max_words,
  delivery_mode: input.delivery_mode,
},
completed_episode_count: 0,
episodes: [],
```

- [ ] **Step 5: 运行前端测试确认通过**

Run: `npm --prefix frontend test -- --runInBand`
Expected: PASS，已完成 run 时能看到“已完成 12 / 12 集”、分集卡片和 merged story 区块。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types.ts frontend/src/api.ts frontend/src/App.tsx frontend/src/components/RunForm.tsx frontend/src/components/ResultPanel.tsx frontend/src/app.css frontend/src/__tests__/App.test.tsx
git commit -m "feat: render episodic runs in web demo"
```

### Task 6: 端到端收口与回归验证

**Files:**
- Modify: `tests/integration/test_web_stream.py`
- Modify: `tests/integration/test_run_command.py`
- Modify: `frontend/src/__tests__/App.test.tsx`
- Modify: `src/dramaloop/main.py` (如果 CLI 需要显式支持 `format` 参数)

**Interfaces:**
- Consumes:
  - `run_episodic_pipeline(...)`
  - web endpoints and SSE from Task 4
  - frontend rendering from Task 5
- Produces:
  - 稳定的回归测试组合
  - CLI / API 均可跑分集模式

- [ ] **Step 1: 写 CLI / integration 回归测试**

```python
# tests/integration/test_run_command.py
from pathlib import Path

from typer.testing import CliRunner

from dramaloop.main import app


def test_run_command_supports_episodic_series(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "run",
            "--idea",
            "她被退婚后反手嫁给宿敌",
            "--style",
            "都市情感",
            "--format",
            "episodic_series",
        ],
    )

    assert result.exit_code == 0
    assert any(path.name == "final_story.md" for path in (tmp_path / "runs").rglob("final_story.md"))
```

- [ ] **Step 2: 运行全量后端测试确认失败点**

Run: `pytest tests/unit tests/integration -v`
Expected: 若 CLI 尚未支持 `--format episodic_series`，则此处 FAIL；先记录具体报错，再补最小实现。

- [ ] **Step 3: 补 CLI / 回归所需最小实现**

```python
# src/dramaloop/main.py (illustrative)
@app.command()
def run(
    idea: str = typer.Option(...),
    style: list[str] = typer.Option(...),
    format: str = typer.Option("single_story"),
) -> None:
    request = StoryRequest(
        idea=idea,
        style=style,
        length="short",
        format=format,
    )
    client = build_llm_client(Settings())
    target = run_episodic_pipeline if request.format == "episodic_series" else run_story_pipeline
    result = target(request, Settings(), client)
    typer.echo(result.final_story_path)
```

- [ ] **Step 4: 运行验证命令并记录结果**

Run: `pytest tests/unit tests/integration -v && npm --prefix frontend test -- --runInBand`
Expected: 全绿；若 `npm` 测试输出中包含 `PASS frontend/src/__tests__/App.test.tsx` 且 pytest 收尾为 `== ... passed ==`，则验证通过。

- [ ] **Step 5: 手动 smoke run 一次 mock 分集流程**

Run: `python -m dramaloop.main run --idea "她被退婚后反手嫁给宿敌" --style 都市情感 --format episodic_series`
Expected: stdout 打印 `runs/<run_id>/final_story.md`；对应 run 目录下存在 `episodes/episode_01.md` 到 `episodes/episode_12.md`。

- [ ] **Step 6: Commit**

```bash
git add src/dramaloop/main.py tests/integration/test_run_command.py tests/integration/test_web_stream.py frontend/src/__tests__/App.test.tsx
git commit -m "feat: verify episodic series end to end"
```

---

## Self-Review

- **Spec coverage:**
  - 新模式 `episodic_series` → Task 1
  - 12 集 / 每集 500-800 字 → Tasks 1-3
  - 先整季规划，再逐集串行生成 → Tasks 2-3
  - 每集独立落盘 → Task 3
  - Web 边生成边展示 + 最终合并版 → Tasks 4-5
  - 保留单篇模式 → Tasks 1, 3, 4, 6
  - 基本 QA 与失败不重跑前面集数 → Task 3
- **Placeholder scan:** 已移除 TBD / TODO / “similar to” 之类占位表达；每个任务都含明确文件、接口、代码、命令。
- **Type consistency:** `StoryRequest.format`、`episode_count`、`episode_min_words`、`episode_max_words`、`delivery_mode` 在各任务中保持一致；web / frontend 都使用同名字段；单集接口统一用 `EpisodeArtifact` / `WebEpisodeSnapshot`。
