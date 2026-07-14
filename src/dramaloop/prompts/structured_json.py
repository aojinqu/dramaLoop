def build_json_contract(schema: str, *, extra_rules: list[str] | None = None) -> list[str]:
    rules = [
        "只返回一个合法的 JSON object。",
        "不要输出 markdown 代码块、注释、标题、项目符号，JSON 前后也不要加任何解释文字。",
        "必须严格使用 schema 中给出的字段名，不要改名、翻译、删字段，也不要新增字段。",
        "所有 key 和字符串值都必须使用双引号。",
        "不要输出 trailing comma。",
        "如果某个必填字段本来可能为空，也要保留该字段，并填一个简洁且合理的值。",
        "必须遵守以下 JSON schema：",
        schema,
    ]
    if extra_rules:
        rules.append("额外 schema 规则：")
        rules.extend(f"- {rule}" for rule in extra_rules)
    return rules
