# Research Harness Eval Report

- case_count: 1
- ablation_run_count: 3
- success_rate: 1.0
- average_judge_score: 8.33
- pairwise_comparison_count: 2

## Ablation Summary
- baseline: completion_rate=1.0000, judge=8.44, originality=9.00, contract_pass_rate=1.0000, memory_recall_rate=0.0000, memory_compression_ratio=0.2747, unsupported_memory_rate=0.0000, provider_tokens=16503, regulation_actions={}
- memory_context_budgeted: completion_rate=1.0000, judge=8.11, originality=7.00, contract_pass_rate=1.0000, memory_recall_rate=0.8000, memory_compression_ratio=0.2868, unsupported_memory_rate=0.0000, provider_tokens=17125, regulation_actions={}
- full_harness: completion_rate=1.0000, judge=8.44, originality=6.00, contract_pass_rate=0.7500, memory_recall_rate=0.8000, memory_compression_ratio=0.2723, unsupported_memory_rate=0.0000, provider_tokens=25961, regulation_actions={}

## Ablation Runs
- floodgate-shift-live-001 / baseline: success=True, judge=8.44, completion=1.00, tokens=4349, latency=113.141s, interventions=0
- floodgate-shift-live-001 / memory_context_budgeted: success=True, judge=8.11, completion=1.00, tokens=4724, latency=79.635s, interventions=0
- floodgate-shift-live-001 / full_harness: success=True, judge=8.44, completion=1.00, tokens=4937, latency=158.970s, interventions=0

## Pairwise Summary
- comparison_count: 2
- tie_rate: 1.0
- mode_win_rate: {}
- dimension_win_rate: {'conflict_intensity': {'full_harness': 0.5}, 'continuity': {'memory_context_budgeted': 0.5}, 'hook_strength': {'full_harness': 0.5}, 'pacing': {'full_harness': 0.5}, 'short_drama_feel': {'full_harness': 0.5}}

## Pairwise
- floodgate-shift-live-001: baseline vs memory_context_budgeted -> tie
- floodgate-shift-live-001: memory_context_budgeted vs full_harness -> tie

## Failure Mining
- memory_recall_gap: 1