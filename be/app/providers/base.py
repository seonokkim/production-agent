from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class ProviderStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProviderSubmitResult:
    provider_job_id: str
    status: ProviderStatus = ProviderStatus.QUEUED


@dataclass
class ProviderOutput:
    file_path: str
    mime_type: str
    asset_type: str
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    checksum: str = ""


@dataclass
class ProviderStatusResult:
    status: ProviderStatus
    outputs: list[ProviderOutput] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    progress: float | None = None


@dataclass
class GenerationRequest:
    generation_type: str
    prompt: str
    negative_prompt: str
    seed: int
    width: int
    height: int
    duration_seconds: float | None
    reference_file_path: str | None
    workflow_snapshot: dict
    node_map: dict
    force_fail: bool = False


class GenerationProvider(ABC):
    @abstractmethod
    def submit(self, request: GenerationRequest) -> ProviderSubmitResult:
        raise NotImplementedError

    @abstractmethod
    def get_status(self, provider_job_id: str) -> ProviderStatusResult:
        raise NotImplementedError

    def cancel(self, provider_job_id: str) -> bool:
        return False
