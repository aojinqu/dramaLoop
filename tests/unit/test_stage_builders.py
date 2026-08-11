from dramaloop.harness.stages import run_character_stage, run_outline_stage, run_premise_stage
from dramaloop.llm.mock import build_default_mock_client
from dramaloop.prompts.draft import build_draft_prompt
from dramaloop.prompts.premise import build_premise_prompt
from dramaloop.schemas.character import CharacterArtifact, CharacterCard
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.outline import OutlineArtifact, StoryBeat
from dramaloop.schemas.premise import PremiseArtifact


def test_premise_prompt_mentions_hook_and_ending_payoff() -> None:
    request = StoryRequest(idea="她被退婚后反手结婚", style=["都市情感"], length="short")
    prompt = build_premise_prompt(request)

    assert "hook" in prompt.lower()
    assert "ending_payoff_plan" in prompt
    assert "不要默认使用退婚改嫁" in prompt


def test_stage_chain_returns_typed_outputs() -> None:
    client = build_default_mock_client()
    request = StoryRequest(idea="她被退婚后反手结婚", style=["都市情感"], length="short")

    premise = run_premise_stage(client, request)
    characters = run_character_stage(client, premise)
    outline = run_outline_stage(client, premise, characters)

    assert premise.title_candidate == "替嫁反击"
    assert isinstance(characters, CharacterArtifact)
    assert outline.ending_type == "revenge payoff"


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
    assert "不可替换的故事细节" in prompt
    assert "禁止复用婚礼退婚后改嫁宿敌" in prompt
