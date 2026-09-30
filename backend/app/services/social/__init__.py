"""Social publishing integrations.

One sub-module set per platform. TikTok is the first; Facebook/Instagram
land beside it later with the same shape:

    <platform>_client.py     pure HTTP client for the platform API
    <platform>_accounts.py   connected-account storage + token refresh
    <platform>_publisher.py  publish orchestration + status sync

Shared pieces: ``token_vault`` (encryption at rest) and ``_db`` (PostgREST
helpers over the service key).
"""
