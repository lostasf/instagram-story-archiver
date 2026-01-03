from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExternalServiceError(Exception):
    component: str
    message: str
    status_code: Optional[int] = None
    response_text: Optional[str] = None

    def __str__(self) -> str:
        parts = [f"{self.component}: {self.message}"]
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")
        if self.response_text:
            parts.append(f"response={self.response_text}")
        return " | ".join(parts)


class InstagramAPIError(ExternalServiceError):
    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
    ):
        super().__init__(
            component="InstagramAPI",
            message=message,
            status_code=status_code,
            response_text=response_text,
        )


class TwitterAPIError(ExternalServiceError):
    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
    ):
        super().__init__(
            component="TwitterAPI",
            message=message,
            status_code=status_code,
            response_text=response_text,
        )
