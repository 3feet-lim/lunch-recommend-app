import hashlib
import logging
from dataclasses import dataclass
from typing import Annotated
from urllib.parse import parse_qs

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status

from app.config import Settings, get_settings
from app.services.slack_response import (
    already_processing_ack,
    command_ack,
    unsupported_interaction_ack,
)
from app.services.slack_signature import SlackSignatureVerifier

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/slack", tags=["slack"])

_SEEN_REQUESTS: set[str] = set()


@dataclass(frozen=True)
class SlackCommand:
    team_id: str
    channel_id: str
    user_id: str
    text: str
    response_url: str
    command: str
    trigger_id: str | None = None

    @property
    def conversation_key(self) -> str:
        return f"{self.team_id}/{self.channel_id}/{self.user_id}"


def parse_slash_command(raw_body: bytes) -> SlackCommand:
    form = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)

    def first(name: str) -> str:
        values = form.get(name, [""])
        return values[0]

    return SlackCommand(
        team_id=first("team_id"),
        channel_id=first("channel_id"),
        user_id=first("user_id"),
        text=first("text").strip(),
        response_url=first("response_url"),
        command=first("command"),
        trigger_id=first("trigger_id") or None,
    )


def fingerprint_command(command: SlackCommand) -> str:
    material = "\x1f".join(
        [command.team_id, command.channel_id, command.user_id, command.command, command.text]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def verify_slack_request(
    *,
    raw_body: bytes,
    timestamp: str | None,
    signature: str | None,
    settings: Settings,
) -> None:
    result = SlackSignatureVerifier(settings.slack_signing_secret).verify(
        raw_body=raw_body, timestamp=timestamp, signature=signature
    )
    if not result.ok:
        logger.warning("Rejected Slack request: %s", result.reason)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_slack_signature",
        )


async def process_lunch_command(command: SlackCommand) -> None:
    """Background seam for recommendation workflow owned by downstream service lanes."""
    logger.info(
        "Accepted Slack lunch command",
        extra={
            "team_id": command.team_id,
            "channel_id": command.channel_id,
            "user_id": command.user_id,
            "has_text": bool(command.text),
        },
    )


@router.post("/commands/lunch")
async def lunch_command(
    request: Request,
    background_tasks: BackgroundTasks,
    x_slack_request_timestamp: Annotated[str | None, Header()] = None,
    x_slack_signature: Annotated[str | None, Header()] = None,
    x_slack_retry_num: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    raw_body = await request.body()
    verify_slack_request(
        raw_body=raw_body,
        timestamp=x_slack_request_timestamp,
        signature=x_slack_signature,
        settings=settings,
    )
    command = parse_slash_command(raw_body)
    fingerprint = fingerprint_command(command)
    if x_slack_retry_num and fingerprint in _SEEN_REQUESTS:
        return already_processing_ack()

    _SEEN_REQUESTS.add(fingerprint)
    background_tasks.add_task(process_lunch_command, command)
    return command_ack()


@router.post("/interactions")
async def slack_interactions(
    request: Request,
    x_slack_request_timestamp: Annotated[str | None, Header()] = None,
    x_slack_signature: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    raw_body = await request.body()
    verify_slack_request(
        raw_body=raw_body,
        timestamp=x_slack_request_timestamp,
        signature=x_slack_signature,
        settings=settings,
    )
    return unsupported_interaction_ack()
