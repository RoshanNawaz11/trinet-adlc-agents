"""
Publish skill bundles to anthropic and cache skills 

"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TypedDict

from agents.model.gateway import ModelGateway
from agents.skills.client import publish_bundle, publish_bundle_version, find_remote_skill_by_name
from agents.skills.loader import SKILLS_DIR, read_bundle_files

logger = logging.getLogger(__name__)

_REGISTRY_FILE = "registry.json"


class CachedSkill(TypedDict):
    bundle_name: str
    display_title: str
    claude_skill_id: str
    claude_version_id: str
    content_hash: str
 
 
def _registry_path() -> Path:
    cache_dir = SKILLS_DIR / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / _REGISTRY_FILE
 
 
def _load_registry() -> dict[str, CachedSkill]:
    path = _registry_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("registry.json unreadable — starting fresh")
        return {}
 
 
def _save_registry(data: dict[str, CachedSkill]) -> None:
    _registry_path().write_text(json.dumps(data, indent=2), encoding="utf-8")
 
 
def _content_hash(files: list[tuple[str, str]]) -> str:
    parts = [f"{name}:{content}" for name, content in sorted(files, key=lambda x: x[0])]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()
 
 
async def ensure_bundle_published(
    bundle_name: str,
    *,
    gateway: ModelGateway | None = None,
) -> tuple[str, str]:
    files = await read_bundle_files(bundle_name)
    digest = _content_hash(files)
    display_title = bundle_name.replace("-", " ").title()
 
    registry = _load_registry()
    cached: CachedSkill | None = registry.get(bundle_name)
 
    if cached and cached.get("content_hash") == digest:
        logger.debug("Bundle '%s' unchanged — reusing cached IDs", bundle_name)
        return cached["claude_skill_id"], cached["claude_version_id"]
 
    skill_id = cached.get("claude_skill_id") if cached else None
 
    # Cache-loss safety net: local cache says "no skill_id on record" —
    # before assuming this is a genuine first publish, check whether
    # Anthropic already has one under this display_name (e.g. the cache
    # file was wiped by a redeploy, but the Skill itself still exists).
    if not skill_id:
        remote = await find_remote_skill_by_name(display_title, gateway=gateway)
        if remote:
            skill_id = remote[0]
            logger.info(
                "Bundle '%s' has no local cache entry but a remote Skill "
                "already exists (skill_id=%s) — versioning it instead of "
                "creating a duplicate",
                bundle_name,
                skill_id,
            )
 
    if skill_id:
        logger.info("Bundle '%s' changed — uploading new version", bundle_name)
        version_id = await publish_bundle_version(skill_id, bundle_name, files, gateway=gateway)
    else:
        logger.info("Publishing bundle '%s' for the first time", bundle_name)
        skill_id, version_id = await publish_bundle(display_title, bundle_name, files, gateway=gateway)
 
    registry[bundle_name] = CachedSkill(
        bundle_name=bundle_name,
        display_title=display_title,
        claude_skill_id=skill_id,
        claude_version_id=version_id,
        content_hash=digest,
    )
    _save_registry(registry)
    return skill_id, version_id