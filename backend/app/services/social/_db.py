"""Thin PostgREST helpers over the service key for the social tables.

The tables are service-role only (see migration 058), so every call here
goes through ``supabase_service``'s pooled client with the service headers.
Kept deliberately small: select / insert (optionally upsert) / update /
delete with an equality filter dict.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.supabase_client import supabase_service


class DbError(RuntimeError):
    pass


def _params(filters: Optional[Dict[str, Any]]) -> Dict[str, str]:
    return {k: f"eq.{v}" for k, v in (filters or {}).items()}


async def db_select(
    table: str,
    *,
    filters: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, str]] = None,
    select: str = "*",
) -> List[Dict[str, Any]]:
    params: Dict[str, str] = {"select": select, **_params(filters), **(extra or {})}
    async with supabase_service._client() as client:
        resp = await client.get(
            f"{supabase_service.url}/rest/v1/{table}",
            headers=supabase_service.service_headers,
            params=params,
        )
    if resp.status_code != 200:
        raise DbError(f"select {table} failed: {resp.status_code} {resp.text[:200]}")
    return resp.json() or []


async def db_insert(
    table: str, row: Dict[str, Any], *, on_conflict: Optional[str] = None
) -> Dict[str, Any]:
    headers = dict(supabase_service.service_headers)
    prefer = "return=representation"
    params: Dict[str, str] = {}
    if on_conflict:
        prefer += ",resolution=merge-duplicates"
        params["on_conflict"] = on_conflict
    headers["Prefer"] = prefer
    async with supabase_service._client() as client:
        resp = await client.post(
            f"{supabase_service.url}/rest/v1/{table}",
            headers=headers,
            params=params,
            json=row,
        )
    if resp.status_code not in (200, 201):
        raise DbError(f"insert {table} failed: {resp.status_code} {resp.text[:200]}")
    data = resp.json()
    return data[0] if isinstance(data, list) and data else (data or {})


async def db_update(
    table: str, filters: Dict[str, Any], patch: Dict[str, Any]
) -> List[Dict[str, Any]]:
    headers = dict(supabase_service.service_headers)
    headers["Prefer"] = "return=representation"
    async with supabase_service._client() as client:
        resp = await client.patch(
            f"{supabase_service.url}/rest/v1/{table}",
            headers=headers,
            params=_params(filters),
            json=patch,
        )
    if resp.status_code not in (200, 204):
        raise DbError(f"update {table} failed: {resp.status_code} {resp.text[:200]}")
    try:
        return resp.json() or []
    except ValueError:
        return []


async def db_delete(table: str, filters: Dict[str, Any], *, extra: Optional[Dict[str, str]] = None) -> int:
    headers = dict(supabase_service.service_headers)
    headers["Prefer"] = "return=representation"
    async with supabase_service._client() as client:
        resp = await client.delete(
            f"{supabase_service.url}/rest/v1/{table}",
            headers=headers,
            params={**_params(filters), **(extra or {})},
        )
    if resp.status_code not in (200, 204):
        raise DbError(f"delete {table} failed: {resp.status_code} {resp.text[:200]}")
    try:
        body = resp.json()
        return len(body) if isinstance(body, list) else 0
    except ValueError:
        return 0


__all__ = ["DbError", "db_select", "db_insert", "db_update", "db_delete"]
