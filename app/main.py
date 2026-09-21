"""FastAPI application: build and query Williams-balanced crossover designs."""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Response

from . import db
from .schemas import (
    AllocationOut,
    ExperimentCreate,
    ExperimentOut,
    ExperimentSummary,
)
from .williams import (
    assign_subjects,
    group_size,
    nearest_acceptable_subject_counts,
    williams_square,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    # Tables are created when the container starts the application.
    db.init_db()
    yield


app = FastAPI(
    title="Crossover Experiment Order Balancing API",
    version="1.0.0",
    description=(
        "Builds Williams-balanced Latin-square sequences for crossover "
        "experiments and maps them to subjects."
    ),
    lifespan=lifespan,
)


def _serialize_experiment(
    experiment: dict[str, Any] | Any, include_allocations: bool
) -> dict[str, Any]:
    conditions = json.loads(experiment["conditions"])
    subject_ids = json.loads(experiment["subject_ids"])
    block_size = experiment["block_size"]
    base = {
        "id": experiment["id"],
        "conditions": conditions,
        "subject_ids": subject_ids,
        "seed": experiment["seed"],
        "n_conditions": experiment["n_conditions"],
        "n_subjects": experiment["n_subjects"],
        "block_size": block_size,
        "complete_blocks": experiment["n_subjects"] // block_size,
        "created_at": experiment["created_at"],
    }
    if include_allocations:
        rows = db.get_allocations(experiment["id"])
        base["allocations"] = [
            AllocationOut(
                subject_id=row["subject_id"],
                sequence_index=row["sequence_index"],
                sequence=json.loads(row["sequence"]),
            )
            for row in rows
        ]
    return base


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/experiments",
    response_model=ExperimentOut,
    status_code=201,
    responses={422: {"description": "Validation error"}},
)
def create_experiment(payload: ExperimentCreate) -> ExperimentOut:
    n = len(payload.conditions)
    size = group_size(n)
    requested = len(payload.subject_ids)

    if requested % size != 0:
        lower, upper = nearest_acceptable_subject_counts(n, requested)
        # Deterministic tie-break: prefer the larger acceptable count.
        nearest = upper if upper is not None else lower
        raise HTTPException(
            status_code=422,
            detail={
                "block_size": size,
                "requested": requested,
                "nearest_lower": lower,
                "nearest_upper": upper,
                "nearest_acceptable": nearest,
                "detail": (
                    f"For {n} conditions the Williams design needs subjects "
                    f"in complete blocks of {size}; received {requested}. "
                    f"Nearest acceptable counts: "
                    f"{lower if lower is not None else '-'} / {upper}. "
                    f"Use {nearest} (or another positive multiple of "
                    f"{size})."
                ),
            },
        )

    assignments = assign_subjects(
        payload.conditions, payload.subject_ids, payload.seed
    )
    square = williams_square(n)

    # Map each concrete condition sequence back to its canonical index so the
    # balanced structure is visible in the response.
    sequence_to_index = {
        tuple(payload.conditions[i] for i in seq): idx
        for idx, seq in enumerate(square)
    }
    rows = [
        (
            a.subject_id,
            a.sequence,
            sequence_to_index[tuple(a.sequence)],
        )
        for a in assignments
    ]

    experiment_id = str(uuid.uuid4())
    db.save_experiment(
        experiment_id,
        payload.conditions,
        payload.subject_ids,
        payload.seed,
        size,
        rows,
    )

    record = db.get_experiment(experiment_id)
    return ExperimentOut(**_serialize_experiment(record, True))


@app.get("/experiments", response_model=list[ExperimentSummary])
def list_experiments() -> list[ExperimentSummary]:
    return [
        ExperimentSummary(**_serialize_experiment(row, False))
        for row in db.list_experiments()
    ]


@app.get("/experiments/{experiment_id}", response_model=ExperimentOut)
def get_experiment(experiment_id: str) -> ExperimentOut:
    record = db.get_experiment(experiment_id)
    if record is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    return ExperimentOut(**_serialize_experiment(record, True))


@app.get("/experiments/{experiment_id}/allocations")
def get_allocations(experiment_id: str, response: Response) -> list[AllocationOut]:
    record = db.get_experiment(experiment_id)
    if record is None:
        raise HTTPException(status_code=404, detail="experiment not found")
    rows = db.get_allocations(experiment_id)
    response.headers["X-Total-Count"] = str(len(rows))
    return [
        AllocationOut(
            subject_id=row["subject_id"],
            sequence_index=row["sequence_index"],
            sequence=json.loads(row["sequence"]),
        )
        for row in rows
    ]
