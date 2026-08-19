from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Remediation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    severity: Literal["low", "medium", "high", "critical"]
    finding: str = Field(max_length=200)
    recommendation: str = Field(max_length=300)


class SecurityReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(max_length=300)
    remediations: list[Remediation] = Field(min_length=1, max_length=5)


class CameraScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene_summary: str
    person_present: bool
    person_count: int = Field(ge=0, le=20)
    package_present: bool
    vehicle_present: bool
    animal_present: bool
    door_open: bool
    lighting: Literal["day", "night", "uncertain"]
    weather_visible: Literal["clear", "snow", "rain", "uncertain"]
    notable_objects: list[str]
    confidence: float = Field(ge=0, le=1)
    uncertain: list[str]


class VisualAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str]


class TemporalChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["object_appeared", "object_disappeared", "door_state_changed", "scene_changed"]
    object: str
    first_seen: str


class TemporalAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    changes: list[TemporalChange]
    summary: str
    confidence: float = Field(ge=0, le=1)


class EvidenceFactor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    factor: str
    advantage: str
    evidence: str


class SportsPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    predicted_winner: str
    win_probability: float = Field(ge=0, le=1)
    key_factors: list[EvidenceFactor] = Field(min_length=1)
    risks_to_prediction: list[str]
    missing_information: list[str]
    confidence: float = Field(ge=0, le=1)


class RetrievalPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    endpoints: list[str] = Field(min_length=1, max_length=4)
    rationale: str


class RepositoryAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str
    files: list[str] = Field(max_length=8)
    evidence: list[str] = Field(max_length=6)
    confidence: float = Field(ge=0, le=1)


class CodeChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file: Literal["app/auth.py"]
    replacement: str
    explanation: str


class ChangeDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    change_required: bool
    files: list[str]
    explanation: str
    confidence: float = Field(ge=0, le=1)
