"""
Anthropic Claude Skills SDK


to add usage tokens from obervability layer
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic
from agents.model.gateway import ModelGateway, get_default_gateway, MissingAPIKeyError

logger = logging.getLogger(__name__)

CODE_EXECUTION_TOOL = {"type": "code_execution_20250825", "name": "code_execution"}

#client connection to the model gateway
def _resolve_gateway(gateway: ModelGateway | None) -> ModelGateway:
    return gateway if gateway is not None else get_default_gateway()

#----------------------------skill publishing----------------------------
async def _prefix_bundle_files(
    bundle_name: str,
    files: list[tuple[str, str]],
) -> list[tuple[str, bytes, str]]:
    result: list[tuple[str, bytes, str]] = []
    for name, content in files:
        path = name if name.startswith(f"{bundle_name}/") else f"{bundle_name}/{name}"
        result.append((path, content.encode("utf-8"), "text/plain"))
    return result

 
#to check if the skill is already published and not create duplicates
async def find_remote_skill_by_name(
    display_name: str,
    *,
    gateway: ModelGateway | None = None,
) -> tuple[str, str] | None:
    client = _resolve_gateway(gateway).require_client()
    next_page: str | None = None
    try:
        while True:
            kwargs: dict[str, Any] = dict(source="custom", limit=100)
            if next_page:
                kwargs["page"] = next_page
            page = await client.skills.list(**kwargs)
            for item in page.data:
                if item.display_name != display_name:
                    continue
                version_id = item.latest_version_id
                if item.id and version_id:
                    return item.id, version_id
            next_page = getattr(page, "next_page", None)
            if not next_page:
                break
    except Exception as exc:
        logger.warning("Could not list remote skills: %s", exc)
    return None

 
#publishing the skill to the anthropic platform
async def publish_bundle(
    display_name: str,
    bundle_name: str,
    files: list[tuple[str, str]],
    *,
    gateway: ModelGateway | None = None,
) -> tuple[str, str]:
    client = _resolve_gateway(gateway).require_client()
    upload_files = await _prefix_bundle_files(bundle_name, files)
    response = await client.skills.create(
        display_name=display_name,
        files=upload_files,
    )
    skill_id = response.id
    version_id = response.latest_version_id
    if not skill_id or not version_id:
        raise RuntimeError(f"Unexpected Skills API response — missing IDs: {response}")
    logger.info("Published '%s' → skill_id=%s version_id=%s", display_name, skill_id, version_id)
    return skill_id, version_id


#publishing a new version of the skill
async def publish_bundle_version(
    claude_skill_id: str,
    bundle_name: str,
    files: list[tuple[str, str]],
    *,
    gateway: ModelGateway | None = None,
) -> str:
    client = _resolve_gateway(gateway).require_client()
    response = await client.skills.versions.create(
        skill_id=claude_skill_id,
        files=_prefix_bundle_files(bundle_name, files),
    )
    version_id = response.id  # skver_... — no more epoch/prefix disambiguation needed
    logger.info("New version for %s → version_id=%s", claude_skill_id, version_id)
    return version_id
 


#----------------------------skill execution----------------------------
"""Run a published skill. Returns the model text. Raises on API failure."""

async def run_skill(
    claude_skill_id: str,
    claude_version_id: str,
    input_text: str,
    *,
    model: str,
    max_tokens: int,
    additional_instructions: str | None = None,
    gateway: ModelGateway | None = None,
) -> dict[str, Any]:
    client = _resolve_gateway(gateway).require_client()
 
    user_content = input_text
    if additional_instructions:
        user_content = f"{additional_instructions}\n\n{input_text}"
 
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        container={
            "skills": [
                {
                    "type": "custom",
                    "skill_id": claude_skill_id,
                    "version": claude_version_id,  #version id of the skill
                }
            ]
        },
        messages=[{"role": "user", "content": user_content}],
        tools=[CODE_EXECUTION_TOOL],
    )
    raw_response = await _collect_text(response)
    return {"raw_response": raw_response}
 
async def _collect_text(response: Any) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        if isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
        elif getattr(block, "type", None) == "text":
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
    return "\n".join(parts).strip()
 