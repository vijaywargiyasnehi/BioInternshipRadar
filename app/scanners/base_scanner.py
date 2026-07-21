"""Abstract base class all scanners implement."""
from abc import ABC, abstractmethod

from app.models import Company
from app.schemas import OpportunityCandidate


class ScanResult:
    def __init__(self, candidates: list[OpportunityCandidate], status: str = "success", error_message: str = ""):
        self.candidates = candidates
        self.status = status  # success | manual_review_required | error
        self.error_message = error_message


class BaseScanner(ABC):
    name: str = "base"

    @abstractmethod
    def scan_company(self, company: Company) -> ScanResult:
        """Scan a company's career page and return normalized opportunity candidates.

        Implementations must never raise for expected failure modes (timeout, 404, blocked) —
        catch them and return a ScanResult with status='error' or 'manual_review_required' so
        the scheduler can keep moving instead of aborting the whole batch.
        """
        raise NotImplementedError
