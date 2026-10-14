from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Literal
from uuid import uuid4

JobStatus = Literal["pending", "running", "succeeded", "failed"]


@dataclass
class JobImage:
    name: str
    filename: str


@dataclass
class TryOnJobImage:
    product: str
    model: str
    filename: str


@dataclass
class Job:
    id: str
    status: JobStatus = "pending"
    placement: str | None = None
    product_images: list[JobImage] = field(default_factory=list)
    try_on_images: list[TryOnJobImage] = field(default_factory=list)
    error: str | None = None


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = Lock()

    def create(self) -> Job:
        job = Job(id=uuid4().hex)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **changes) -> Job:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)
            return job
