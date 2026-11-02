"""Where a profile points when nobody says: Coho's production service.

A fresh install has no config file at all, and `coho login` on a new laptop should
reach the service people pay for rather than stop at an error naming a URL they have
no way to know. So a profile being *created* — by `coho configure`, or implicitly by
the first command on a machine with no config — starts life pointed at production.

These are defaults, not policy. `--url` and `--oidc-domain` still win, and a profile
that already exists is never rewritten: pointing one at dev stays done.

The hosts carry no environment in their names (`coho-data` doc 56 §7a). Dev and
production are different domains in different AWS accounts, so the `-dev` suffix dev
needs to share a zone would only put `-prod` in front of every customer.
"""

from __future__ import annotations

from coho_management_sdk.profiles import Profile

# The BFF (`coho-data` doc 22): every management call this CLI makes goes here.
PRODUCTION_URL = "https://api.coho-cms.com"

# Coho's own sign-in service (doc 27), which took over Cognito's hosted UI at the same
# /oauth2/authorize and /oauth2/token addresses.
PRODUCTION_OIDC_DOMAIN = "https://auth.coho-cms.com"

# The CLI's client there: public, no secret, any loopback port (RFC 8252). The same
# name in every environment, which is why it is a default and not a question.
CLIENT_ID = "coho-cli"


def point_at_production(profile: Profile) -> Profile:
    """Fill in a new profile's endpoints, leaving anything already set alone."""
    if not profile.url:
        profile.url = PRODUCTION_URL
    if not profile.oidc_domain:
        profile.oidc_domain = PRODUCTION_OIDC_DOMAIN
    if not profile.client_id:
        profile.client_id = CLIENT_ID
    return profile
