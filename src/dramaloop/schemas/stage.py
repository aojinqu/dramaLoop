from pydantic import BaseModel, Field


class StageSpec(BaseModel):
    name: str = Field(min_length=1)
    input_schema: str = Field(min_length=1)
    output_schema: str = Field(min_length=1)
    required_context: list[str] = Field(default_factory=list)
    optional_context: list[str] = Field(default_factory=list)
    artifact_outputs: list[str] = Field(default_factory=list)
    contract_rules: list[str] = Field(default_factory=list)
    forbidden_behaviors: list[str] = Field(default_factory=list)
    common_failure_modes: list[str] = Field(default_factory=list)
