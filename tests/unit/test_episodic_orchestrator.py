import json
from pathlib import Path

import pytest

from dramaloop.config import Settings
from dramaloop.harness.episodic_orchestrator import _build_episode_plan_in_chunks, run_episodic_pipeline
from dramaloop.llm.mock import MockLLMClient, build_default_mock_client
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.season import SeasonBible


def _episodic_request(*, episode_count: int = 12) -> StoryRequest:
    return StoryRequest(
        idea="她被退婚后反手嫁给宿敌",
        style=["都市情感"],
        length="short",
        format="episodic_series",
        episode_count=episode_count,
    )


def _episodic_client(
    *,
    episode_drafts: list[str],
    episode_plan: list[dict[str, object]] | None = None,
    critique: dict[str, object] | None = None,
    rewrite_text: str | None = None,
) -> MockLLMClient:
    structured: dict[str, object] = {
        "season_planning": {
            "title_candidate": "退婚后我反嫁宿敌",
            "series_logline": "她在婚礼当天被抛弃后，反手嫁给宿敌，用12集完成反杀。",
            "core_conflict": "女主要在前任与家族的双重羞辱中拿回尊严和主动权。",
            "target_episode_count": 12,
            "final_payoff": "前任公开失势，女主赢回名声与感情主动权。",
            "main_character_arcs": ["林晚从受辱者变成设局者"],
            "must_land_beats": ["婚礼羞辱", "闪婚联盟", "公开反杀"],
        },
        "episode_plan_generation": {
            "episodes": episode_plan
            or [
                {
                    "episode_number": 1,
                    "title": "婚礼反击",
                    "opening_situation": "婚礼现场，新郎带旧爱现身。",
                    "core_conflict": "女主必须马上止损反击。",
                    "must_happen": ["当众受辱", "提出改嫁"],
                    "hook_ending": "顾承骁说他知道偷拍视频是谁放的。",
                    "sets_up_next": "下一集进入危险闪婚。",
                },
                {
                    "episode_number": 2,
                    "title": "危险闪婚",
                    "opening_situation": "顾承骁公开接住女主抛出的婚约。",
                    "core_conflict": "女主必须决定要不要借势反击。",
                    "must_happen": ["闪婚协议", "前任破防"],
                    "hook_ending": "顾承骁拿出了偷拍视频原件。",
                    "sets_up_next": "下一集追查幕后黑手。",
                },
            ]
        },
        "episode_critique_scoring": critique
        or {
            "episode_number": 1,
            "overall_score": 7.5,
            "dimension_scores": {
                "hook_strength": 7.5,
                "conflict_intensity": 7.5,
                "pacing": 7.5,
                "short_drama_feel": 7.5,
                "carryover": 8.0,
            },
            "weakest_dimensions": ["pacing"],
            "rewrite_needed": False,
            "rewrite_target": "本集已达标，无需大改。",
            "issues": [],
        },
    }
    text_outputs: dict[str, str | list[str]] = {"episode_draft_generation": episode_drafts}
    if rewrite_text is not None:
        text_outputs["episode_targeted_rewrite"] = rewrite_text
    return MockLLMClient(structured_outputs=structured, text_outputs=text_outputs)


def test_run_episodic_pipeline_writes_episode_files_and_final_story(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    client = build_default_mock_client()

    result = run_episodic_pipeline(_episodic_request(episode_count=1), settings, client)

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

    result = run_episodic_pipeline(_episodic_request(), settings, client)
    manifest = (result.run_dir / "run_manifest.json").read_text(encoding="utf-8")

    assert '"format": "episodic_series"' in manifest
    assert '"completed_episodes": 12' in manifest


def test_build_episode_plan_in_chunks_collects_requested_ranges_from_full_plan() -> None:
    client = build_default_mock_client()
    season = client.generate_structured(
        role="season_planning",
        prompt="season",
        response_model=SeasonBible,
    )

    episodes = _build_episode_plan_in_chunks(client, season, 12, chunk_size=4)

    assert [episode.episode_number for episode in episodes] == list(range(1, 13))
    assert episodes[0].title == "婚礼反击"
    assert episodes[-1].title == "公开反杀"


def test_run_episodic_pipeline_fails_when_episode_plan_does_not_cover_requested_range(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    client = _episodic_client(
        episode_drafts=[
            "第1集正文。婚礼现场，新郎带旧爱现身时，林晚当众提出改嫁，顾承骁替她扛下满场羞辱。",
        ],
        episode_plan=[
            {
                "episode_number": 1,
                "title": "婚礼反击",
                "opening_situation": "婚礼现场，新郎带旧爱现身。",
                "core_conflict": "女主必须马上止损反击。",
                "must_happen": ["当众受辱", "提出改嫁"],
                "hook_ending": "顾承骁说他知道偷拍视频是谁放的。",
                "sets_up_next": "下一集进入危险闪婚。",
            }
        ],
    )

    with pytest.raises(RuntimeError, match="Episode plan does not cover requested range 1-2"):
        run_episodic_pipeline(_episodic_request(episode_count=2), settings, client)

    run_dir = next((tmp_path / "runs").iterdir())
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "failed"
    assert manifest["completed_episodes"] == 0
    assert not (run_dir / "final_story.md").exists()
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    client = _episodic_client(
        episode_drafts=[
            "第1集正文。婚礼现场，新郎带旧爱现身时，林晚当众提出改嫁，顾承骁替她扛下满场羞辱。等宾客散去，他贴近她耳边低声说：‘顾承骁说他知道偷拍视频是谁放的。’",
            "第2集正文。故事刚开始，林晚又回到婚礼现场，像第一次认识所有人那样重新讲起自己的遭遇，仿佛前一集什么都没发生。",
            "第2集正文。顾承骁说他知道偷拍视频是谁放的后，直接把林晚带上车避开媒体。林晚没有再回头看婚礼现场，而是顺着这条线索答应先签下闪婚协议，再借顾承骁的势把羞辱还回去。陆闻舟追出来破防失态，反而让她更确定这次合作值得冒险。车门合上前，顾承骁把新的证物袋推到她手里，低声说里面装着偷拍视频原件。",
        ]
    )

    result = run_episodic_pipeline(_episodic_request(episode_count=2), settings, client)
    episode_two = json.loads((result.run_dir / "episodes" / "episode_02.json").read_text(encoding="utf-8"))
    continuity = json.loads((result.run_dir / "continuity_state.json").read_text(encoding="utf-8"))
    events = (result.run_dir / "events.jsonl").read_text(encoding="utf-8")

    assert "顾承骁说他知道偷拍视频是谁放的后" in episode_two["markdown"]
    assert continuity["last_episode_hook"] == "车门合上前，顾承骁把新的证物袋推到她手里，低声说里面装着偷拍视频原件。"
    assert episode_two["hook_delivered"] == continuity["last_episode_hook"]
    assert "episode=2;attempt=1" in events
    assert "episode=2;attempt=2" in events


def test_episode_summary_is_richer_than_core_conflict_template(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    client = build_default_mock_client()

    result = run_episodic_pipeline(_episodic_request(episode_count=2), settings, client)
    episode_one = json.loads((result.run_dir / "episodes" / "episode_01.json").read_text(encoding="utf-8"))

    assert episode_one["episode_summary"] != "第1集：女主必须马上止损反击。"
    assert "《婚礼反击》" in episode_one["episode_summary"]
    assert "婚礼现场，新郎带旧爱现身" in episode_one["episode_summary"]
    assert "实际收尾" in episode_one["episode_summary"]


def test_repeated_continuity_failure_aborts_before_final_story(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    client = _episodic_client(
        episode_drafts=[
            "第1集正文。婚礼现场，新郎带旧爱现身时，林晚当众提出改嫁，顾承骁替她扛下满场羞辱。散场时，他贴近她耳边低声说：‘顾承骁说他知道偷拍视频是谁放的。’",
            "第2集正文。故事刚开始，林晚重新站回婚礼门口，像第一集一样介绍所有恩怨，还说这一切都结束了。",
            "第2集正文。故事刚开始，林晚又回到婚礼当天，把前面的羞辱重新讲了一遍，还像大结局一样说从此以后所有风波都结束了。",
        ]
    )

    with pytest.raises(RuntimeError, match="Episode 2 failed continuity gate"):
        run_episodic_pipeline(_episodic_request(episode_count=2), settings, client)

    run_dir = next((tmp_path / "runs").iterdir())
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "failed"
    assert manifest["completed_episodes"] == 1
    assert "continuity gate" in manifest["error_message"]
    assert not (run_dir / "final_story.md").exists()
    assert manifest.get("final_artifact") is None


def test_requested_final_episode_can_end_cleanly(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    client = _episodic_client(
        episode_drafts=[
            "第1集正文。婚礼现场，新郎带旧爱现身时，林晚当众提出改嫁，顾承骁替她扛下满场羞辱。所有真相在当晚被公开，前任当场失势，她也终于把丢掉的尊严拿了回来。",
        ]
    )

    result = run_episodic_pipeline(_episodic_request(episode_count=1), settings, client)
    episode_one = json.loads((result.run_dir / "episodes" / "episode_01.json").read_text(encoding="utf-8"))

    assert "终局回收" in episode_one["episode_summary"]
    assert "把悬念推向下一集" not in episode_one["episode_summary"]


def test_run_episodic_pipeline_writes_critique_and_rewrites_low_score_episode(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    draft = (
        "第1集正文。婚礼大屏亮起时，林晚看见未婚夫牵着旧爱走进来。"
        "她当众提出改嫁，顾承骁接住她，散场时低声说他知道偷拍视频是谁放的。"
    )
    rewritten = draft + " 她盯着他，确认这句话不是安慰，而是下一场反击的起点。"
    client = MockLLMClient(
        structured_outputs={
            "season_planning": {
                "title_candidate": "退婚后我反嫁宿敌",
                "series_logline": "她在婚礼当天被抛弃后，反手嫁给宿敌，用12集完成反杀。",
                "core_conflict": "女主要在前任与家族的双重羞辱中拿回尊严和主动权。",
                "target_episode_count": 12,
                "final_payoff": "前任公开失势，女主赢回名声与感情主动权。",
                "main_character_arcs": ["林晚从受辱者变成设局者"],
                "must_land_beats": ["婚礼羞辱", "闪婚联盟", "公开反杀"],
            },
            "episode_plan_generation": {
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
                ]
            },
            "episode_critique_scoring": {
                "episode_number": 1,
                "overall_score": 5.5,
                "dimension_scores": {
                    "hook_strength": 5.0,
                    "conflict_intensity": 6.0,
                    "pacing": 5.5,
                    "short_drama_feel": 6.0,
                    "carryover": 8.0,
                },
                "weakest_dimensions": ["hook_strength", "pacing"],
                "rewrite_needed": True,
                "rewrite_target": "强化集末钩子并加快中段冲突推进。",
                "issues": ["结尾钩子偏软"],
            },
        },
        text_outputs={
            "episode_draft_generation": [draft],
            "episode_targeted_rewrite": [rewritten],
        },
    )

    result = run_episodic_pipeline(_episodic_request(episode_count=1), settings, client)
    critique_path = result.run_dir / "episodes" / "episode_01_critique.json"
    episode_md = (result.run_dir / "episodes" / "episode_01.md").read_text(encoding="utf-8")
    events = (result.run_dir / "events.jsonl").read_text(encoding="utf-8")

    assert critique_path.exists()
    critique = json.loads(critique_path.read_text(encoding="utf-8"))
    assert critique["rewrite_needed"] is True
    assert critique["overall_score"] == 5.5
    assert episode_md == rewritten
    assert "下一场反击的起点" in episode_md
    assert '"stage":"episode_critique"' in events
    assert '"stage":"episode_rewrite"' in events
