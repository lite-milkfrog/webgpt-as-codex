from __future__ import annotations

import base64
import hashlib
import urllib.parse
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class OAuthTokens:
    access_token: str
    refresh_token: str
    client_id: str
    resource: str


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _localize(url: str, local_base: str) -> str:
    parsed = urllib.parse.urlparse(url)
    suffix = parsed.path or "/"
    if parsed.query:
        suffix += "?" + parsed.query
    return local_base.rstrip("/") + suffix


def _cookie_header(session: requests.Session) -> dict[str, str]:
    value = "; ".join(f"{cookie.name}={cookie.value}" for cookie in session.cookies)
    return {"Cookie": value} if value else {}


def password_pkce_flow(
    local_base: str,
    password: str,
    *,
    redirect_uri: str = "https://chatgpt.com/connector/oauth/webgpt-codex-stage5-probe",
    timeout: float = 15.0,
) -> tuple[requests.Session, OAuthTokens]:
    session = requests.Session()
    resource_meta = session.get(
        local_base.rstrip("/") + "/.well-known/oauth-protected-resource",
        timeout=timeout,
    ).json()
    auth_meta = session.get(
        local_base.rstrip("/") + "/.well-known/oauth-authorization-server",
        timeout=timeout,
    ).json()

    registration = session.post(
        _localize(auth_meta["registration_endpoint"], local_base),
        json={
            "client_name": "WebGPT-as-Codex Stage5 Probe",
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
        timeout=timeout,
    )
    registration.raise_for_status()
    client_id = registration.json()["client_id"]

    verifier = "WebGPTCodexStage5Verifier0123456789abcdefghijklmnopqrstuvwxyz-._~"
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    state = "webgpt_codex_stage5_state_20260919"
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "resource": resource_meta["resource"],
    }
    auth_page = session.get(
        _localize(auth_meta["authorization_endpoint"], local_base),
        params=params,
        allow_redirects=True,
        timeout=timeout,
    )
    auth_page.raise_for_status()
    if "password" not in auth_page.text.lower():
        raise RuntimeError("OAuth password page was not presented")

    login = session.post(
        local_base.rstrip("/") + "/.auth/login",
        data={"password": password},
        headers=_cookie_header(session),
        allow_redirects=False,
        timeout=timeout,
    )
    if login.status_code == 401:
        raise RuntimeError("OAuth password was rejected")
    location = login.headers.get("Location", "")
    consent_status: int | None = None
    consent_excerpt = ""
    if location and not location.startswith(redirect_uri):
        consent = session.post(
            _localize(location, local_base),
            data={},
            headers=_cookie_header(session),
            allow_redirects=False,
            timeout=timeout,
        )
        consent_status = consent.status_code
        consent_excerpt = consent.text[:240].replace("\n", " ")
        location = consent.headers.get("Location", "")

    if not location.startswith(redirect_uri):
        login_excerpt = login.text[:240].replace("\n", " ")
        raise RuntimeError(
            "OAuth did not return to redirect URI; "
            f"login_status={login.status_code} login_location={login.headers.get('Location','')[:160]!r} "
            f"login_body={login_excerpt!r} consent_status={consent_status} "
            f"consent_body={consent_excerpt!r} final_location={location[:180]!r}"
        )
    query = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)
    if query.get("state", [None])[0] != state:
        raise RuntimeError("OAuth state mismatch")
    code = query["code"][0]

    token = session.post(
        _localize(auth_meta["token_endpoint"], local_base),
        headers=_cookie_header(session),
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
            "resource": resource_meta["resource"],
        },
        timeout=timeout,
    )
    token.raise_for_status()
    body = token.json()
    refresh = body.get("refresh_token")
    if not refresh:
        raise RuntimeError("OAuth server did not issue a refresh token")
    return session, OAuthTokens(
        access_token=body["access_token"],
        refresh_token=refresh,
        client_id=client_id,
        resource=resource_meta["resource"],
    )


def refresh_access_token(
    session: requests.Session,
    local_base: str,
    tokens: OAuthTokens,
    *,
    timeout: float = 15.0,
) -> str:
    auth_meta = session.get(
        local_base.rstrip("/") + "/.well-known/oauth-authorization-server",
        timeout=timeout,
    ).json()
    response = session.post(
        _localize(auth_meta["token_endpoint"], local_base),
        headers=_cookie_header(session),
        data={
            "grant_type": "refresh_token",
            "client_id": tokens.client_id,
            "refresh_token": tokens.refresh_token,
            "resource": tokens.resource,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["access_token"]
