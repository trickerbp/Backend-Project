from __future__ import annotations

from typing import Any


def success_response(data: Any = None, message: str = 'OK') -> dict[str, Any]:
    return {'success': True, 'message': message, 'data': data}


def error_response(message: str, detail: Any = None) -> dict[str, Any]:
    return {'success': False, 'message': message, 'detail': detail}
