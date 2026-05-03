from __future__ import annotations

from app.core.config import Settings
from app.models.user import BillingTier


class ProjectLimitExceededError(Exception):
    """Raised when an account has reached its billing-tier project limit."""


class BillingManager:
    def __init__(self, *, settings: Settings) -> None:
        self._project_limits = {
            BillingTier.FREE.value: settings.billing_free_max_projects,
            BillingTier.PRO.value: settings.billing_pro_max_projects,
        }

    def ensure_can_create_project(
        self,
        *,
        billing_tier: str | None,
        project_count: int,
    ) -> None:
        normalized_tier = self.normalize_billing_tier(billing_tier)
        max_projects = self.get_max_projects(normalized_tier)
        if max_projects is None or project_count < max_projects:
            return
        raise ProjectLimitExceededError(
            f"Project limit reached for the {normalized_tier} tier: "
            f"{project_count}/{max_projects} projects used. "
            "Delete an existing project or upgrade the account to create another one."
        )

    def get_max_projects(self, billing_tier: str | None) -> int | None:
        normalized_tier = self.normalize_billing_tier(billing_tier)
        max_projects = self._project_limits[normalized_tier]
        return None if max_projects < 0 else max_projects

    def normalize_billing_tier(self, billing_tier: str | None) -> str:
        if billing_tier is None:
            return BillingTier.FREE.value
        normalized_tier = billing_tier.strip().lower()
        if normalized_tier in self._project_limits:
            return normalized_tier
        return BillingTier.FREE.value
