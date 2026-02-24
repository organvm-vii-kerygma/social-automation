"""social-automation: POSSE distribution and social platform automation.

Part of ORGAN VII (Kerygma) — the marketing and distribution layer
of the eight-organ creative-institutional system.
"""

__version__ = "0.3.0"

from kerygma_social.posse import PosseDistributor, Platform, ContentPost, SyndicationRecord
from kerygma_social.delivery_log import DeliveryLog, DeliveryRecord
from kerygma_social.config import load_config, SocialConfig
from kerygma_social.factory import build_distributor, build_distributor_for_profile

__all__ = [
    "PosseDistributor",
    "Platform",
    "ContentPost",
    "SyndicationRecord",
    "DeliveryLog",
    "DeliveryRecord",
    "load_config",
    "SocialConfig",
    "build_distributor",
    "build_distributor_for_profile",
]
