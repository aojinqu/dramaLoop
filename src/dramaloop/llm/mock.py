import json
from collections.abc import Mapping
from typing import Any

from dramaloop.harness.realization import realize_structured_output
from dramaloop.llm.base import LLMClient, LLMInvocationError, TModel
from dramaloop.schemas.realization import RealizationResult


def _build_default_episode_drafts() -> list[str]:
    return [
        "第1集正文。婚礼大屏亮起时，林晚看见未婚夫牵着旧爱走进来，整个宴会厅都安静了一瞬。她指尖发冷，却没有哭，只是在所有人的注视下慢慢转身，看向角落里的顾承骁。这个男人是前任最恨的死对头，也是全场唯一还带着笑的人。林晚提着婚纱一步步走到他面前，声音不高，却足够让满场宾客听清：‘顾总，你还缺一个新娘吗？’ 满堂哗然。前任脸色骤变，冲过来想抓她的手，却被顾承骁先一步挡开。顾承骁垂眼看着她，像是在确认她是不是一时赌气。几秒后，他抬手替她扶正头纱，低声道：‘你敢嫁，我就敢替你把这场羞辱翻过来。’ 下一秒，他当众宣布婚礼继续，只是新郎换人。前任彻底失控，旧爱也白了脸。林晚以为这已经够疯了，没想到走下台时，顾承骁忽然贴近她耳边，声音压得极低：‘我知道偷拍视频是谁放的。’",
        "第2集正文。顾承骁说他知道偷拍视频是谁放的后，直接把林晚带离喧闹的宴会厅。夜风里，林晚仍攥着婚纱裙摆，心跳却比刚才更乱。顾承骁把车门关上，没有安慰她，只把一份闪婚协议推到她面前：只要她点头，他就帮她把婚礼上的羞辱原封不动地还回去。林晚盯着那几页纸，终于意识到自己已经没有退路。与此同时，陆闻舟追出来失控质问，顾承骁当场护在她身前，逼得对方颜面尽失。林晚没有再回头，她提笔签下名字，也等于签下反击的开始。就在她以为这不过是一场交易时，顾承骁从文件袋里抽出一张存储卡，低声说：‘偷拍视频原件，就在我手里。’",
        "第3集正文。顾承骁拿出了偷拍视频原件，林晚连呼吸都顿了一下。两人连夜查看内容，发现偷拍视频里除了婚礼画面，还夹着一段陌生号码的转账记录。林晚迅速意识到，这不只是旧爱挑衅，而是有人故意把她往死里推。她和顾承骁顺着原件里的设备编号追查，很快锁定了婚礼策划团队中的可疑联系人。为了避免打草惊蛇，林晚强压怒火，装作还被舆论压得抬不起头。直到顾承骁调出另一段监控，她才看见偷拍视频里竟然闪过父亲旧公司的标识。线索越挖越深，林晚忽然明白，这场婚礼背后牵出的，可能不只是背叛。视频暂停的最后一帧里，赫然停着父亲签名的档案页。",
        "第4集正文。偷拍视频里出现了女主父亲的名字后，林晚一夜没合眼。第二天一早，家族长辈就把她叫回老宅，要求她别再追查，承认是自己在婚礼上冲动失态。林晚坐在满屋审视的目光里，第一次没有退让，她把偷拍视频原件摔在桌上，反问谁更怕旧案被翻出来。长辈们脸色发青，转而拿项目和名声逼她低头。就在气氛最紧绷的时候，顾承骁推门而入，当众表态这件事他会陪她查到底，也等于公开站到了林晚这一边。前任见局势不对，立刻放话要抢走她最后的珠宝项目，逼她在事业和真相之间二选一。林晚还没来得及回击，对方已经把竞标公告发到了她手机上。",
        "第5集正文。前任宣布要抢走她最后的项目后，林晚立刻赶到竞标会现场。她知道自己一旦失去这个项目，之前所有强撑出来的体面都会被踩碎。顾承骁替她挡下外部封锁，她则在会场里反向布线，把前任截胡的证据一点点套出来。双方在名利场上短兵相接，表面是争项目，实则是争谁先撑不住。林晚抓住对方财务漏洞，当众逼得前任改口，终于抢回了核心提案资格。会后她还来不及松口气，顾承骁忽然把一份早已准备好的辅助证据递给她，坦白自己从很早以前就开始留意她。林晚心神一乱，正想追问原因，顾承骁却低声承认：‘我早就喜欢你。’",
        "第6集正文。顾承骁承认他早就喜欢她后，林晚第一次在这场合作里乱了分寸。她明知自己不能被情绪拖住，却还是忍不住怀疑，顾承骁到底是真心，还是借喜欢来换取她更深的信任。两人一边继续追查旧案，一边在每次试探和靠近里反复拉扯。顾承骁为她挡掉舆论采访，她却在深夜故意试探他是否还藏着别的目的。误会在沉默里被一点点放大，连原本稳固的联盟都出现了裂缝。就在林晚决定先把感情问题压下时，前任突然在网上放出一份所谓的黑料预告，把矛头重新指向她。更糟的是，那份黑料里居然附着她最不愿公开的一段旧记录。",
        "第7集正文。前任手里突然多出一份她的黑料后，林晚几乎被全网舆论推上风口浪尖。她没有再像婚礼那天一样被动挨打，而是迅速联络顾承骁和公关团队，准备正面反击。两人沿着黑料传播链往回追，很快发现最早放料的账户和偷拍视频事件有关，显然幕后是同一拨人在持续下手。顾承骁替她争取时间，林晚则亲自下场回应，用事实一点点撕开造谣的口子。随着证据拼齐，原本摇摆的舆论开始反转，前任的节奏第一次被她硬生生打断。就在林晚以为终于摸到幕后边缘时，一个一直躲在暗处的大人物名字被挖了出来。顾承骁看着调查结果，低声说：‘幕后金主，终于露面了。’",
        "第8集正文。幕后金主终于露面后，林晚才发现自己之前面对的不过是棋盘边角。对方直接约她见面，开口就要她退出行业，否则不只她的项目，连父亲旧案都要一起被埋死。林晚压住怒火，没有当场撕破脸，而是和顾承骁默契配合，一边谈判拖延时间，一边暗中布下反杀局。她故意示弱，让幕后金主以为自己已经撑不住，实际却在逐条确认对方曾经动手的证据链。顾承骁则趁谈判间隙拿到了旧案的核心资料，发现当年的真相远比他们想的更深。离开时，林晚刚松口气，翻到资料最后一页却整个人僵住。父亲旧案里被隐藏的签字栏，竟然写着她最信任之人的名字。",
        "第9集正文。女主发现父亲旧案另有真相后，整个人都像被冰水浇透。她原以为自己已经接近结局，没想到真正的背叛一直藏在最熟悉的人身边。林晚和顾承骁把旧案资料重新拼接，终于确认内鬼并不是外围棋子，而是曾经最先安慰过她的人。真相逼得她必须在立刻复仇和彻底查清之间做选择，她咬牙压住情绪，决定先把证据链补全。顾承骁明知她快撑不住，仍陪她一条条核对账目和监控，直到天亮前终于锁死内鬼身份。可就在两人准备反向收网时，顾承骁突然接到消息，被人设计卷进一场商业陷害。林晚冲出门时，只看见他被带走前留给她的最后一个眼神。",
        "第10集正文。顾承骁被对手设计陷害后，林晚第一次真正体会到什么叫腹背受敌。她一边要想办法把人捞出来，一边还得稳住项目和舆论，不能让前任趁机翻盘。林晚把所有零碎证据重新整理，决定独自出面和幕后金主周旋，同时暗中安排律师与媒体线准备救人。她不再只是被顾承骁保护的人，而是开始主动调度所有能用的筹码。靠着旧案证据和最新财务漏洞，她终于逼得对方露出破绽，也为顾承骁争取到了脱身时间。等顾承骁从危机里出来时，林晚已经把终局所需的关键证据全部埋好。只是前任还沉浸在自己即将赢下这一局的错觉里，甚至开始提前庆祝。",
        "第11集正文。前任以为自己赢了之后，林晚没有立刻反击，而是先把所有人脉和证据重新排了一遍。她把直播场地、媒体顺序、盟友出场节奏都拆成了精确的时间表，甚至连谁负责拖住幕后金主都安排好了。顾承骁恢复行动后，没有再冲到最前面替她挡，而是按她的计划去补齐最后一段反证，让整场公开翻盘真正变成由林晚主导的局。随着夜色渐深，越来越多本来不敢站队的人被她说服加入，终局终于从一场冒险变成一张逐步闭合的网。可就在直播团队准备上线设备时，负责保管核心证据的人突然失联，备用硬盘也被人掉包成了空壳。林晚盯着那只被拆开的箱子，终于意识到最后的背叛并不在外面，而是在他们已经默认安全的环节里。",
        "第12集正文。直播开始前，证据突然消失，可林晚没有让慌乱写在脸上。她和顾承骁顺着最后一段监控迅速锁定偷走硬盘的人，当场反向逼问，终于把被藏起来的证据重新拿了回来。公开直播如期开始，林晚站在镜头前，把婚礼偷拍视频、旧案真相和前任勾连幕后金主的证据一层层推到所有人面前。前任还想辩解，后台的资金流和录音却同时被放出，连曾经偏袒他的长辈都再无话可说。那一刻，林晚终于把婚礼上失去的尊严、被压下的真相和一路忍到现在的怒火全部讨了回来。风波平息后，顾承骁没有提交易，也没有提利用，只在夜色里问她，还愿不愿意把这场婚姻继续下去。林晚看着他，第一次真正笑了出来。",
    ]


DEFAULT_STRUCTURED_OUTPUTS: dict[
    str,
    dict[str, Any] | str | list[dict[str, Any] | str],
] = {
    "premise_refinement": [
        {
            "title_candidate": "替嫁反击",
            "logline": "她被退婚后转身嫁给死对头。",
            "core_conflict": "两大家族的旧怨与新婚关系相互引爆。",
            "hook_promise": "婚礼羞辱后立刻反击。",
            "ending_payoff_plan": "前任公开失势，她赢回尊严。",
            "tone_notes": ["快节奏", "爽感强"],
            "hard_constraints": ["短篇"],
        }
    ],
    "character_card_generation": [
        {
            "characters": [
                {
                    "name": "林晚",
                    "role": "protagonist",
                    "public_identity": "珠宝设计师",
                    "core_desire": "夺回尊严与事业",
                    "core_fear": "再次成为被选择的人",
                    "hidden_secret": None,
                    "conflict_links": ["顾承骁", "陆闻舟"],
                    "voice_style": "冷静锋利",
                    "arc_target": "从隐忍到掌控局面",
                }
            ]
        }
    ],
    "story_outline_generation": [
        {
            "beats": [
                {"beat_id": "b1", "label": "hook", "purpose": "抓人", "summary": "婚礼被退婚", "tension_level": 9, "payoff_dependency": None},
                {"beat_id": "b2", "label": "inciting", "purpose": "冲突", "summary": "她当场改嫁死对头", "tension_level": 9, "payoff_dependency": None},
                {"beat_id": "b3", "label": "escalation", "purpose": "升级", "summary": "前任家族全线封杀", "tension_level": 8, "payoff_dependency": "b5"},
                {"beat_id": "b4", "label": "reveal", "purpose": "反转", "summary": "新婚丈夫早就布局复仇", "tension_level": 9, "payoff_dependency": "b5"},
                {"beat_id": "b5", "label": "payoff", "purpose": "回报", "summary": "前任众叛亲离", "tension_level": 10, "payoff_dependency": None},
            ],
            "ending_type": "revenge payoff",
        }
    ],
    "season_planning": [
        {
            "title_candidate": "退婚后我反嫁宿敌",
            "series_logline": "她在婚礼当天被抛弃后，反手嫁给宿敌，用12集完成反杀。",
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
                {
                    "episode_number": 3,
                    "title": "幕后线索",
                    "opening_situation": "两人开始追查偷拍视频来源。",
                    "core_conflict": "女主发现背后还有家族内鬼。",
                    "must_happen": ["追线索", "锁定嫌疑人"],
                    "hook_ending": "偷拍视频里出现了女主父亲的名字。",
                    "sets_up_next": "下一集家族冲突升级。",
                },
                {
                    "episode_number": 4,
                    "title": "家族逼宫",
                    "opening_situation": "家族长辈要求女主低头息事宁人。",
                    "core_conflict": "女主必须在家族压力下坚持反击。",
                    "must_happen": ["公开对抗长辈", "顾承骁站队"],
                    "hook_ending": "前任宣布要抢走她最后的项目。",
                    "sets_up_next": "下一集进入项目争夺战。",
                },
                {
                    "episode_number": 5,
                    "title": "项目争夺",
                    "opening_situation": "女主核心项目被前任截胡。",
                    "core_conflict": "她必须在名利场中抢回主动权。",
                    "must_happen": ["反制截胡", "拿到关键证据"],
                    "hook_ending": "顾承骁承认他早就喜欢她。",
                    "sets_up_next": "下一集感情和利益同时失控。",
                },
                {
                    "episode_number": 6,
                    "title": "真假试探",
                    "opening_situation": "女主怀疑顾承骁靠近她另有目的。",
                    "core_conflict": "两人关系在合作与真心之间摇摆。",
                    "must_happen": ["感情试探", "误会升级"],
                    "hook_ending": "前任手里突然多出一份她的黑料。",
                    "sets_up_next": "下一集黑料危机引爆。",
                },
                {
                    "episode_number": 7,
                    "title": "黑料引爆",
                    "opening_situation": "前任公开放出女主黑料。",
                    "core_conflict": "女主必须在舆论崩盘前翻盘。",
                    "must_happen": ["舆论反击", "找出造谣源头"],
                    "hook_ending": "幕后金主终于露面。",
                    "sets_up_next": "下一集直面幕后势力。",
                },
                {
                    "episode_number": 8,
                    "title": "幕后现身",
                    "opening_situation": "幕后金主逼迫女主彻底退场。",
                    "core_conflict": "女主与顾承骁必须联手破局。",
                    "must_happen": ["正面谈判", "布下反杀局"],
                    "hook_ending": "女主发现父亲旧案另有真相。",
                    "sets_up_next": "下一集翻旧案。",
                },
                {
                    "episode_number": 9,
                    "title": "旧案翻出",
                    "opening_situation": "父亲旧案成为新的突破口。",
                    "core_conflict": "女主必须在真相和复仇间做选择。",
                    "must_happen": ["拼凑旧案", "确认内鬼身份"],
                    "hook_ending": "顾承骁被对手设计陷害。",
                    "sets_up_next": "下一集救人反击。",
                },
                {
                    "episode_number": 10,
                    "title": "双线反扑",
                    "opening_situation": "顾承骁陷入危机，女主被迫独自上场。",
                    "core_conflict": "女主必须同时救人和保住局面。",
                    "must_happen": ["救顾承骁", "埋终局证据"],
                    "hook_ending": "前任以为自己赢了。",
                    "sets_up_next": "下一集进入终局前夜。",
                },
                {
                    "episode_number": 11,
                    "title": "终局前夜",
                    "opening_situation": "所有证据与人脉都被推上桌面。",
                    "core_conflict": "女主必须赌上最后一局。",
                    "must_happen": ["召集盟友", "锁定直播反杀方案"],
                    "hook_ending": "直播开始前，证据突然消失。",
                    "sets_up_next": "下一集公开终局反杀。",
                },
                {
                    "episode_number": 12,
                    "title": "公开反杀",
                    "opening_situation": "女主走上公开直播的终局战场。",
                    "core_conflict": "她必须当众完成对前任和幕后势力的终局反杀。",
                    "must_happen": ["公开翻案", "前任失势", "情感 payoff 落地"],
                    "hook_ending": "风波结束后，顾承骁问她还愿不愿意继续这场婚姻。",
                    "sets_up_next": "整季收束。",
                },
            ]
        }
    ],
    "critique_scoring": [
        {
            "dimension_scores": {
                "hook_strength": {"score": 6, "reason": "开头抓人但还不够猛", "evidence": "婚礼羞辱出现得快，但反击力度还可以更锋利", "improvement_advice": "让开场台词更有爆点"},
                "character_consistency": {"score": 7, "reason": "人物动机清晰", "evidence": "林晚始终围绕尊严和反击行动", "improvement_advice": "增加一处更强的内心决断"},
                "conflict_intensity": {"score": 7, "reason": "冲突已建立", "evidence": "退婚与改嫁形成正面对撞", "improvement_advice": "中段继续抬高外部压力"},
                "pacing": {"score": 6, "reason": "节奏还算顺", "evidence": "从婚礼到反击推进较快，但中段略短", "improvement_advice": "补一小段升级桥接"},
                "short_drama_feel": {"score": 7, "reason": "短剧感已出现", "evidence": "钩子、羞辱、反击都在位", "improvement_advice": "把结尾打脸拉得更狠"},
                "ending_payoff": {"score": 5, "reason": "结尾回报不足", "evidence": "目前只有反击起手，没有形成完整终局反杀", "improvement_advice": "增加一段更明确的公开反杀场景"},
                "language_fluency": {"score": 7, "reason": "语言基本流畅", "evidence": "句式简洁，易读", "improvement_advice": "增加一句更利落的收尾台词"},
            },
            "overall_score": 6.43,
            "weakest_dimensions": ["ending_payoff", "hook_strength"],
            "rewrite_target": "ending_payoff",
            "rewrite_plan": {"scope": "结尾两段", "must_fix": ["增加终局反杀", "补强公开羞辱的回报感"], "keep": ["婚礼开头", "改嫁钩子"]},
        },
        {
            "dimension_scores": {
                "hook_strength": {"score": 8, "reason": "开头明显更抓人", "evidence": "婚礼羞辱后立刻接改嫁动作", "improvement_advice": "继续保持开场锋利度"},
                "character_consistency": {"score": 7, "reason": "人物动机稳定", "evidence": "林晚的尊严诉求始终一致", "improvement_advice": "后续可再加一处心理描写"},
                "conflict_intensity": {"score": 8, "reason": "冲突强度够高", "evidence": "公开直播反杀抬升了冲突级别", "improvement_advice": "后续可以补更强的对手反扑"},
                "pacing": {"score": 7, "reason": "节奏更完整", "evidence": "开头-反击-结尾回报形成闭环", "improvement_advice": "中段桥接仍可略压缩"},
                "short_drama_feel": {"score": 8, "reason": "短剧感明显", "evidence": "羞辱、闪婚、直播反杀都很短剧", "improvement_advice": "后续可增加一层反转"},
                "ending_payoff": {"score": 7, "reason": "结尾已有明确回报", "evidence": "林晚在公开场合完成体面反击", "improvement_advice": "结尾再加一击会更爽"},
                "language_fluency": {"score": 7, "reason": "语言顺畅", "evidence": "关键台词简洁有力", "improvement_advice": "保持句式利落"},
            },
            "overall_score": 7.43,
            "weakest_dimensions": ["pacing"],
            "rewrite_target": "opening_hook",
            "rewrite_plan": {"scope": "开头一段", "must_fix": ["让第一句更锋利"], "keep": ["结尾直播反杀", "核心冲突关系"]},
        },
    ],
    "episode_critique_scoring": [
        {
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
            "issues": ["结尾钩子偏软", "中段节奏拖沓"],
        },
        {
            "episode_number": 2,
            "overall_score": 7.2,
            "dimension_scores": {
                "hook_strength": 7.0,
                "conflict_intensity": 7.5,
                "pacing": 7.0,
                "short_drama_feel": 7.5,
                "carryover": 7.0,
            },
            "weakest_dimensions": ["pacing"],
            "rewrite_needed": False,
            "rewrite_target": "本集节奏已达标，可微调中段过渡。",
            "issues": [],
        },
    ],
    "research_judge": [
        {
            "dimensions": {
                "hook_strength": 8.0,
                "conflict_intensity": 8.0,
                "pacing": 7.5,
                "short_drama_feel": 8.0,
                "character_consistency": 8.0,
                "continuity": 8.0,
                "context_fidelity": 8.0,
                "rewrite_effectiveness": 7.5,
            },
            "rationale": "结构完整，约束与改写目标均得到保留。",
        }
    ],
    "research_pairwise_judge": [
        {
            "winner": "tie",
            "dimension_winners": {
                "hook_strength": "tie",
                "conflict_intensity": "tie",
                "pacing": "tie",
                "short_drama_feel": "tie",
                "character_consistency": "tie",
                "continuity": "tie",
                "context_fidelity": "tie",
                "rewrite_effectiveness": "tie",
            },
            "rationale": "两个 mock 输出质量相同。",
        }
    ],
}

DEFAULT_TEXT_OUTPUTS: dict[str, str | list[str]] = {
    "draft_generation": [
        "# 替嫁反击\n\n婚礼大屏亮起时，林晚看见了陆闻舟牵着别人的手。\n\n她没有哭，只当着所有宾客的面，转头看向陆闻舟最大的死对头顾承骁：\"顾总，你还缺新娘吗？\"\n\n顾承骁看了她三秒，抬手替她摘下头纱：\"林小姐，你敢嫁，我就敢让他们今天一起难堪。\"\n"
    ],
    "targeted_rewrite": [
        "# 替嫁反击\n\n婚礼大屏亮起时，林晚看见了陆闻舟牵着别人的手。\n\n她没有哭，只当着所有宾客的面，转头看向陆闻舟最大的死对头顾承骁：\"顾总，你还缺新娘吗？\"\n\n顾承骁看了她三秒，抬手替她摘下头纱：\"林小姐，你敢嫁，我就敢让他们今天一起难堪。\"\n\n最后一场董事会直播里，顾承骁把陆闻舟转移资产的证据推上屏幕。林晚接过话筒，盯着那张瞬间惨白的脸，慢慢开口：\"你在婚礼上丢掉的，不只是我，是你陆家最后一点体面。\"\n\n直播弹幕刷得满屏都是，陆闻舟想解释，却被股东当场请出了会场。林晚终于把那口气，原封不动地还了回去。\n"
    ],
    "episode_draft_generation": _build_default_episode_drafts(),
    "episode_targeted_rewrite": [
        "第1集改写正文。婚礼大屏亮起时，林晚看见未婚夫牵着旧爱走进来，整个宴会厅都安静了一瞬。她指尖发冷，却没有哭，只是在所有人的注视下慢慢转身，看向角落里的顾承骁。这个男人是前任最恨的死对头，也是全场唯一还带着笑的人。林晚提着婚纱一步步走到他面前，声音不高，却足够让满场宾客听清：‘顾总，你还缺一个新娘吗？’ 满堂哗然。前任脸色骤变，冲过来想抓她的手，却被顾承骁先一步挡开。顾承骁垂眼看着她，像是在确认她是不是一时赌气。几秒后，他抬手替她扶正头纱，低声道：‘你敢嫁，我就敢替你把这场羞辱翻过来。’ 下一秒，他当众宣布婚礼继续，只是新郎换人。前任彻底失控，旧爱也白了脸。林晚以为这已经够疯了，没想到走下台时，顾承骁忽然贴近她耳边，声音压得极低：‘我知道偷拍视频是谁放的——而且证据就在我车上。’",
    ],
}


class MockLLMClient(LLMClient):
    def __init__(
        self,
        *,
        structured_outputs: Mapping[
            str,
            dict[str, Any] | str | list[dict[str, Any] | str],
        ],
        text_outputs: Mapping[str, str | list[str]],
    ) -> None:
        self._structured_outputs = {
            role: list(payloads) if isinstance(payloads, list) else [payloads]
            for role, payloads in structured_outputs.items()
        }
        self._text_outputs = {
            role: list(payloads) if isinstance(payloads, list) else [payloads]
            for role, payloads in text_outputs.items()
        }
        self.last_realization_result: RealizationResult | None = None

    def _next_payload(self, store: dict[str, list[Any]], role: str, kind: str) -> Any:
        try:
            payloads = store[role]
        except KeyError as exc:
            raise LLMInvocationError(f"Missing mock {kind} output for role={role}") from exc
        return payloads.pop(0) if len(payloads) > 1 else payloads[0]

    def generate_structured(self, *, role: str, prompt: str, response_model: type[TModel]) -> TModel:
        payload = self._next_payload(self._structured_outputs, role, "structured")
        if isinstance(payload, str):
            realized = realize_structured_output(
                role,
                payload,
                response_model,
                retry=lambda _: self._raw_retry_payload(role),
            )
            self.last_realization_result = realized.result
            if realized.output is None:
                raise LLMInvocationError("; ".join(realized.result.issues))
            return realized.output
        self.last_realization_result = RealizationResult(stage=role, status="accepted")
        return response_model.model_validate(payload)

    def _raw_retry_payload(self, role: str) -> str:
        payload = self._next_payload(self._structured_outputs, role, "structured")
        return payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)

    def generate_text(self, *, role: str, prompt: str) -> str:
        return self._next_payload(self._text_outputs, role, "text")


def build_default_mock_client() -> MockLLMClient:
    return MockLLMClient(structured_outputs=DEFAULT_STRUCTURED_OUTPUTS, text_outputs=DEFAULT_TEXT_OUTPUTS)
