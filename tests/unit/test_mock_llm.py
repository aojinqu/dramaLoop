from dramaloop.llm.mock import MockLLMClient, build_default_mock_client
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.premise import PremiseArtifact


def test_mock_client_returns_validated_structured_model() -> None:
    client = MockLLMClient(
        structured_outputs={
            "premise_refinement": {
                "title_candidate": "替嫁反击",
                "logline": "她被退婚后嫁给死对头反击前任。",
                "core_conflict": "前任和新婚丈夫的权力对抗把她卷到中心。",
                "hook_promise": "婚礼背叛后立即反击。",
                "ending_payoff_plan": "前任失去一切，她赢回尊严与爱。",
                "tone_notes": ["快节奏"],
                "hard_constraints": ["短篇"],
            }
        },
        text_outputs={},
    )

    artifact = client.generate_structured(
        role="premise_refinement",
        prompt="refine premise",
        response_model=PremiseArtifact,
    )

    assert artifact.title_candidate == "替嫁反击"


def test_default_mock_client_can_generate_text() -> None:
    client = build_default_mock_client()

    assert "替嫁反击" in client.generate_text(role="draft_generation", prompt="write draft")


def test_default_mock_client_advances_structured_sequences() -> None:
    client = build_default_mock_client()

    first = client.generate_structured(
        role="critique_scoring",
        prompt="critique v1",
        response_model=CritiqueArtifact,
    )
    second = client.generate_structured(
        role="critique_scoring",
        prompt="critique v2",
        response_model=CritiqueArtifact,
    )

    assert first.overall_score < second.overall_score
    assert first.rewrite_target == "ending_payoff"
    assert second.rewrite_target == "opening_hook"
