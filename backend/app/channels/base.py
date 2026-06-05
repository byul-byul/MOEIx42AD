# /backend/app/channels/base.py
from abc import ABC, abstractmethod

from app.schemas import AgentResponse, IncomingMessage


class BaseChannel(ABC):
    @abstractmethod
    async def parse_incoming(self, raw: dict) -> IncomingMessage | None:
        """Parse raw channel payload into IncomingMessage. Return None to skip silently."""
        ...

    @abstractmethod
    async def send_response(self, response: AgentResponse, raw: dict) -> None:
        """Deliver AgentResponse back to the user on this channel."""
        ...
