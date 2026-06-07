from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


class ApiError(RuntimeError):
    pass


def _parse_response(raw: bytes) -> dict[str, Any]:
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def request_json(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{BACKEND_URL}{path}"
    if params:
        filtered = {key: value for key, value in params.items() if value not in (None, "")}
        if filtered:
            url = f"{url}?{urllib.parse.urlencode(filtered)}"
    data = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            return _parse_response(response.read())
    except urllib.error.HTTPError as exc:
        body = exc.read()
        detail = _parse_response(body)
        raise ApiError(detail.get("error") or detail.get("detail") or str(exc)) from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"Backend nem elérhető ({BACKEND_URL}): {exc}") from exc


def post_ocr(case_id: str, filename: str, content: bytes) -> dict[str, Any]:
    boundary = "----aszfqna边界"
    parts: list[bytes] = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(f'Content-Disposition: form-data; name="case_id"\r\n\r\n{case_id}\r\n'.encode())
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        (
            f'Content-Disposition: form-data; name="pdf_file"; filename="{filename}"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode()
    )
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    url = f"{BACKEND_URL}/ocr"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return _parse_response(response.read())
    except urllib.error.HTTPError as exc:
        raise ApiError(exc.read().decode("utf-8", errors="replace")) from exc


def login(username: str, password: str) -> dict[str, Any]:
    return request_json("POST", "/auth/login", {"username": username, "password": password})


def list_inbox(**filters: Any) -> dict[str, Any]:
    return request_json("GET", "/inbox", params=filters)


def get_case(case_id: str) -> dict[str, Any]:
    return request_json("GET", f"/cases/{case_id}")


def create_case(**payload: Any) -> dict[str, Any]:
    return request_json("POST", "/cases/create", payload)


def process_case(**payload: Any) -> dict[str, Any]:
    return request_json("POST", "/cases/process", payload)


def save_draft(**payload: Any) -> dict[str, Any]:
    return request_json("POST", "/cases/draft", payload)


def approve_draft(**payload: Any) -> dict[str, Any]:
    return request_json("POST", "/cases/approve", payload)


def get_audit_record(case_id: str, role: str) -> dict[str, Any]:
    return request_json("GET", f"/audit/cases/{case_id}", params={"role": role})


def get_audit_completeness(case_id: str, role: str) -> dict[str, Any]:
    return request_json("GET", f"/audit/completeness/{case_id}", params={"role": role})


def list_audit_events(case_id: str | None = None, role: str = "ui", limit: int = 50) -> dict[str, Any]:
    return request_json("GET", "/audit/events", params={"case_id": case_id, "role": role, "limit": limit})


def governance_purge(dry_run: bool, username: str, role: str) -> dict[str, Any]:
    return request_json("POST", "/governance/purge", {"dry_run": dry_run, "username": username, "role": role})


def submit_feedback(**payload: Any) -> dict[str, Any]:
    return request_json("POST", "/cases/feedback", payload)


def get_history(address: str) -> dict[str, Any]:
    return request_json("GET", "/history", params={"address": address})


def customer_lookup(address: str) -> dict[str, Any]:
    return request_json("GET", "/customer-lookup", params={"address": address})


def run_reindex(force: bool = False) -> dict[str, Any]:
    return request_json("POST", "/reindex", {"force": force})


def run_eval(
    limit: int = 10,
    category: str | None = None,
    service_provider: str | None = None,
    include_edge: bool = True,
) -> dict[str, Any]:
    return request_json(
        "POST",
        "/eval/run",
        {
            "limit": limit,
            "category": category,
            "service_provider": service_provider,
            "include_edge": include_edge,
        },
    )


def save_eval_baseline(run_id: str) -> dict[str, Any]:
    return request_json("POST", "/eval/baseline", {"run_id": run_id})


def save_human_score(run_id: str, email_id: str, score: int) -> dict[str, Any]:
    return request_json("POST", "/eval/human-score", {"run_id": run_id, "email_id": email_id, "score": score})


def supervisor_queue() -> dict[str, Any]:
    return request_json("GET", "/supervisor/queue")


def supervisor_stats() -> dict[str, Any]:
    return request_json("GET", "/supervisor/stats")
