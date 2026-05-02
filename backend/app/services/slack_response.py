from typing import Any


def ephemeral_text(text: str) -> dict[str, Any]:
    return {"response_type": "ephemeral", "text": text}


def command_ack() -> dict[str, Any]:
    return ephemeral_text("점심 추천 요청을 확인했어요. 잠시만 기다려 주세요.")


def already_processing_ack() -> dict[str, Any]:
    return ephemeral_text("이미 같은 점심 추천 요청을 처리 중입니다.")


def unsupported_interaction_ack() -> dict[str, Any]:
    return ephemeral_text("아직 지원하지 않는 Slack 상호작용입니다.")
