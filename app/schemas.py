"""Pydantic request/response models."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, field_validator


class ExperimentCreate(BaseModel):
    conditions: List[str] = Field(
        ...,
        min_length=2,
        description="Distinct condition labels (at least two).",
    )
    subject_ids: List[str] = Field(
        ...,
        min_length=1,
        description="Distinct subject identifiers.",
    )
    seed: int = Field(
        ..., description="Random seed making the allocation reproducible."
    )

    @field_validator("conditions", "subject_ids")
    @classmethod
    def _unique_and_nonblank(cls, value: List[str]) -> List[str]:
        if any(not isinstance(v, str) or not v.strip() for v in value):
            raise ValueError("entries must be non-empty strings")
        if len(set(value)) != len(value):
            raise ValueError("entries must be distinct")
        return value


class AllocationOut(BaseModel):
    subject_id: str
    sequence_index: int = Field(
        ..., description="Index of the Williams sequence assigned."
    )
    sequence: List[str]


class ExperimentOut(BaseModel):
    id: str
    conditions: List[str]
    subject_ids: List[str]
    seed: int
    n_conditions: int
    n_subjects: int
    block_size: int
    complete_blocks: int
    created_at: str
    allocations: List[AllocationOut]


class ExperimentSummary(BaseModel):
    id: str
    n_conditions: int
    n_subjects: int
    block_size: int
    complete_blocks: int
    seed: int
    created_at: str


class SubjectCountError(BaseModel):
    detail: str
    block_size: int
    requested: int
    nearest_lower: int | None
    nearest_upper: int | None
    nearest_acceptable: int
