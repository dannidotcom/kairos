LEAD_STATUSES = (
    "new",
    "qualified",
    "contacted",
    "replied",
    "meeting",
    "won",
    "lost",
    "disqualified",
)

CAMPAIGN_STATUSES = ("draft", "active", "paused", "completed", "archived")
CAMPAIGN_LEAD_STATUSES = (
    "enrolled",
    "invited",
    "connected",
    "messaged",
    "replied",
    "meeting",
    "stopped",
    "completed",
    "failed",
)
SIGNAL_TYPES = (
    "job_change",
    "funding",
    "hiring",
    "linkedin_post",
    "website_visit",
    "company_growth",
    "product_launch",
    "engagement",
    "manual",
)
ACTION_TYPES = ("connection_request", "message", "follow_up", "inmail")
ACTION_STATUSES = ("scheduled", "processing", "sent", "failed", "cancelled", "skipped")
ACCOUNT_STATUSES = ("connected", "warming", "paused", "disconnected")
MEMBERSHIP_ROLES = ("owner", "admin", "member")
