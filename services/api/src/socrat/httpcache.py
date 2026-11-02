"""Cache headers for responses that are the same for every visitor.

The API answers ``no-store`` by default (``main.boundary``). A route that serves identical
bytes to everyone, such as the lists of domains, renderers and locales, can use ``shared`` so a
CDN or browser keeps it for a few minutes and revalidates with the ETag after that.
"""

import hashlib
import json

from fastapi import Request, Response
from fastapi.responses import JSONResponse

MAX_AGE = 300


def shared(request: Request, payload: dict, max_age: int = MAX_AGE) -> Response:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    tag = '"' + hashlib.sha256(body.encode()).hexdigest()[:24] + '"'
    headers = {"ETag": tag, "Cache-Control": f"public, max-age={max_age}"}
    if request.headers.get("if-none-match") == tag:
        return Response(status_code=304, headers=headers)
    return JSONResponse(payload, headers=headers)
