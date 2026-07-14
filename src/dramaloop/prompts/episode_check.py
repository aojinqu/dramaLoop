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
