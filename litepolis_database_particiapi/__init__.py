"""
LitePolis Database ParticiAPI - ParticiAPI-specific database models

This module extends LitePolis-database-default with ParticiAPI-specific models:
- ParticiapiUser: Extended participant model with ParticiAPI fields
- ParticipantExtended: Additional participant metadata
- ParticiapiIssuer: OIDC issuer configuration
- MathMain: Math results caching
- NotificationTasks: Notification queue management
"""

# Re-export DEFAULT_CONFIG from database-default (shared database connection)
from litepolis_database_default import DEFAULT_CONFIG
from .Actor import DatabaseActor

__all__ = ["DatabaseActor", "DEFAULT_CONFIG"]