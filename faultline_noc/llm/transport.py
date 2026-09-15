"""Model transports: live Anthropic calls, recording to cassettes, and fail-closed replay."""

import hashlib
import json
from pathlib import Path
from typing import Any, Protocol, cast

import anthropic

Request = dict[str, Any]
Response = dict[str, Any]
KEY_HEX_CHARS = 24
CASSETTE_INDENT = 1


class CassetteMissingError(LookupError):
    """Raised in replay when no recorded response matches a request."""


class Transport(Protocol):
    """Sends one Messages API request and returns the response as a plain dict."""

    def create(self, request: Request) -> Response:
        """Return the response for a request."""
        ...


def request_key(request: Request) -> str:
    """Return a stable hash of a request, independent of dict key order."""
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:KEY_HEX_CHARS]


class CassetteStore:
    """Recorded responses for one agent run, one JSON file per request hash."""

    def __init__(self, directory: Path) -> None:
        """Use a directory, created on the first save."""
        self._directory = directory

    def save(self, request: Request, response: Response) -> Path:
        """Write the response for a request to disk straight away and return its path."""
        self._directory.mkdir(parents=True, exist_ok=True)
        path = self._directory / f"{request_key(request)}.json"
        text = json.dumps(response, sort_keys=True, indent=CASSETTE_INDENT, ensure_ascii=False)
        path.write_bytes((text + "\n").encode("utf-8"))
        return path

    def load(self, request: Request) -> Response:
        """Return the recorded response for a request, or raise CassetteMissingError."""
        path = self._directory / f"{request_key(request)}.json"
        if not path.exists():
            raise CassetteMissingError(f"no recorded response at {path}")
        return cast(Response, json.loads(path.read_text(encoding="utf-8")))


class AnthropicTransport:
    """Calls the Messages API through the official SDK, with credentials from the environment."""

    def __init__(self) -> None:
        """Create the SDK client."""
        self._messages: Any = anthropic.Anthropic().messages

    def create(self, request: Request) -> Response:
        """Send a request and return the response as a dict."""
        return cast(Response, self._messages.create(**request).to_dict())


class RecordingTransport:
    """Sends live requests and saves every response before returning it."""

    def __init__(self, inner: Transport, store: CassetteStore) -> None:
        """Wrap a live transport with a cassette store."""
        self._inner = inner
        self._store = store

    def create(self, request: Request) -> Response:
        """Send the request, persist the response, then return it."""
        response = self._inner.create(request)
        self._store.save(request, response)
        return response


class ReplayTransport:
    """Answers only from recorded responses, so a changed prompt or tool fails closed."""

    def __init__(self, store: CassetteStore) -> None:
        """Replay from a cassette store."""
        self._store = store

    def create(self, request: Request) -> Response:
        """Return the recorded response for the request."""
        return self._store.load(request)
