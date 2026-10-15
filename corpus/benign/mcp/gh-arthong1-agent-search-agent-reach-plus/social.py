"""Fixed, read-only social routes; no login, cookie discovery or arbitrary CLI.

Search returns one {platform, backend, data} record per successful platform
and {platform, code, message} records in errors. Read returns a single record
or raises ReachError. CLI JSON is preserved; legacy plain-text output stays
a string. Limits apply per platform.

Twitter CLI execution additionally requires run_cli.twitter_env_only is True:
the transport must enforce that no browser extraction is possible, including
after invalid-token verification. Stock twitter-cli cannot guarantee this.
"""

from __future__ import annotations

import asyncio
import json
import re
from urllib.parse import parse_qs, urlsplit

from agent_reach.backends.opencli import opencli_status
from agent_reach.config import Config

from .transport import ReachError, has_cli, run_cli, validate_limit, validate_query

_PLATFORMS = frozenset({
    "github", "youtube", "bilibili", "twitter", "reddit", "xiaohongshu",
    "facebook", "instagram",
})
_READ_PLATFORMS = frozenset({"github", "bilibili", "twitter", "reddit", "xiaohongshu"})
_REPO = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?/[A-Za-z0-9_.-]{1,100}")
_BV = re.compile(r"BV1[A-Za-z0-9]{9}")
_POST_ID = re.compile(r"(?:t3_)?([a-z0-9]{1,20})")


def _decode(raw: str, *, strict: bool = True):
    try:
        data = json.loads(raw)
        if isinstance(data, (dict, list)):
            if isinstance(data, dict) and data.get("ok") is False:
                error = data.get("error")
                code = error.get("code") if isinstance(error, dict) else data.get("code")
                if not isinstance(code, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code):
                    code = "backend_error"
                # Raw errors can contain tokens, URLs and request headers.
                raise ReachError(code, "Backend reported a failure; check login/configuration or retry later")
            return data
    except (ValueError, TypeError):
        pass
    if strict:
        raise ReachError("invalid_response", "Backend did not return a JSON object or list")
    return raw


def _limit_data(data, limit: int):
    if isinstance(data, list):
        return data[:limit]
    if isinstance(data, dict):
        return {key: value[:limit] if key in {"entries", "results", "data", "items"} and isinstance(value, list) else value for key, value in data.items()}
    return data


async def _opencli_ready() -> bool:
    if not has_cli("opencli"):
        return False
    try:
        # Upstream probes --version and loopback /status; never doctor or login.
        return (await asyncio.to_thread(opencli_status)).ready is True
    except Exception:
        return False


def _twitter_env():
    try:
        config = Config(read_only=True)
        values = [config.get("twitter_auth_token"), config.get("twitter_ct0")]
    except Exception:
        return None
    if not all(
        isinstance(value, str) and value and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
        for value in values
    ):
        return None
    return dict(zip(("TWITTER_AUTH_TOKEN", "TWITTER_CT0"), values))


async def _opencli(platform: str, operation: str, value: str, limit=None):
    if not await _opencli_ready():
        raise ReachError("setup_required", f"{platform} requires OpenCLI with a connected browser extension and an existing login")
    args = [platform, operation, value]
    if limit is not None:
        args += ["--limit", str(limit)]
    args += ["-f", "json"]
    return "opencli", _decode(await run_cli("opencli", args))


async def _twitter(operation: str, target: str, limit=None):
    primary_error = None
    if has_cli("twitter"):
        env = _twitter_env()
        if env is not None and getattr(run_cli, "twitter_env_only", False) is True:
            args = [operation, target]
            if limit is not None:
                args += ["-n", str(limit)]
            args += ["--json"]
            try:
                return "twitter", _decode(await run_cli("twitter", args, env=env))
            except ReachError as exc:
                primary_error = exc
        elif env is not None:
            primary_error = ReachError("setup_required", "Twitter CLI requires an environment-only transport that disables browser cookie extraction; use connected OpenCLI")
    try:
        # OpenCLI calls its single-tweet reader 'thread', not 'tweet' or 'read'.
        return await _opencli("twitter", "thread" if operation == "tweet" else operation, target, limit)
    except ReachError as exc:
        if primary_error is not None and exc.code == "setup_required":
            raise primary_error
        raise


async def _reddit(operation: str, target: str, limit=None):
    try:
        return await _opencli("reddit", operation, target, limit)
    except ReachError:
        if not has_cli("rdt"):
            raise
    args = [operation, target]
    if limit is not None:
        args += ["--limit", str(limit)]
    return "rdt", _decode(await run_cli("rdt", args), strict=False)


async def _bilibili(operation: str, target: str, limit=None):
    if has_cli("bili"):
        args = [operation, target]
        if limit is not None:
            args += ["--type", "video", "-n", str(limit)]
        args += ["--json"]
        return "bili", _decode(await run_cli("bili", args), strict=False)
    return await _opencli("bilibili", operation, target, limit)


async def _search(platform: str, query: str, limit: int):
    if platform == "github":
        if not has_cli("gh"):
            raise ReachError("setup_required", "GitHub CLI is not installed")
        args = ["search", "repos", query, "--limit", str(limit), "--visibility", "public", "--json", "fullName,url,description,stargazersCount"]
        return "gh", _decode(await run_cli("gh", args))
    if platform == "youtube":
        if not has_cli("yt-dlp"):
            raise ReachError("setup_required", "yt-dlp is not installed")
        args = ["--ignore-config", "--flat-playlist", "--dump-single-json", f"ytsearch{limit}:{query}"]
        return "yt-dlp", _decode(await run_cli("yt-dlp", args))
    if platform == "bilibili":
        return await _bilibili("search", query, limit)
    if platform == "twitter":
        return await _twitter("search", query, limit)
    if platform == "reddit":
        return await _reddit("search", query, limit)
    return await _opencli(platform, "search", query, limit)


async def social_search(query: str, platforms: list[str], limit: int = 5) -> dict:
    """Search 1–5 distinct supported platforms, retaining per-platform failures."""
    # Check raw controls too: transport normalizes whitespace before validating.
    if isinstance(query, str) and any(ord(c) < 32 or ord(c) == 127 for c in query):
        raise ReachError("invalid_input", "query must not contain control characters")
    query = validate_query(query)
    limit = validate_limit(limit, max_value=20)
    if (
        not isinstance(platforms, list) or not 1 <= len(platforms) <= 5
        or any(not isinstance(p, str) or p not in _PLATFORMS for p in platforms)
        or len(set(platforms)) != len(platforms)
    ):
        raise ReachError("invalid_input", "platforms must contain 1–5 distinct supported platform names")
    async def search_one(platform):
        try:
            backend, data = await _search(platform, query, limit)
            return {"platform": platform, "backend": backend, "data": _limit_data(data, limit)}, None
        except ReachError as exc:
            return None, {"platform": platform, "code": exc.code, "message": exc.message}
        except Exception:
            return None, {"platform": platform, "code": "backend_error", "message": "Social backend failed; check configuration or retry later"}

    outcomes = await asyncio.gather(*(search_one(platform) for platform in platforms))
    results = [result for result, error in outcomes if result is not None]
    errors = [error for result, error in outcomes if error is not None]
    return {"query": query, "limit": limit, "results": results, "errors": errors}


def _platform_url(target: str, hosts: set[str], *, https_only=False):
    try:
        url = urlsplit(target)
        if (
            url.scheme not in ({"https"} if https_only else {"http", "https"})
            or url.hostname not in hosts or url.username is not None or url.password is not None
            or url.port not in (None, 443 if url.scheme == "https" else 80)
            or "\\" in target
        ):
            raise ValueError()
        return url
    except ValueError:
        raise ReachError("invalid_target", "Use a valid URL on the requested platform") from None


def _read_target(platform: str, target: str) -> str:
    if not isinstance(platform, str) or platform not in _READ_PLATFORMS:
        raise ReachError("invalid_input", "Supported readers: github, twitter, reddit, bilibili, xiaohongshu")
    if not isinstance(target, str) or not target or len(target) > 4096 or any(ord(c) < 33 or ord(c) == 127 for c in target):
        raise ReachError("invalid_target", "Provide a nonempty target without whitespace or controls")
    if platform == "github":
        if not _REPO.fullmatch(target) or target.split("/")[1] in {".", ".."}:
            raise ReachError("invalid_target", "GitHub target must be owner/repo")
    elif platform == "bilibili":
        if not _BV.fullmatch(target):
            raise ReachError("invalid_target", "Bilibili target must be a complete BV video ID")
    elif platform == "twitter":
        url = _platform_url(target, {"x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"})
        if not re.fullmatch(r"/(?:[A-Za-z0-9_]{1,15}|i/web)/status/[0-9]{1,30}/?", url.path):
            raise ReachError("invalid_target", "Twitter target must be a tweet status URL")
    elif platform == "reddit":
        match = _POST_ID.fullmatch(target)
        if match:
            return match[1]
        url = _platform_url(target, {"reddit.com", "www.reddit.com", "old.reddit.com", "new.reddit.com", "m.reddit.com", "redd.it"})
        pattern = r"/([a-z0-9]{1,20})/?" if url.hostname == "redd.it" else r"/(?:r/[A-Za-z0-9_]+/)?comments/([a-z0-9]{1,20})(?:/.*)?"
        match = re.fullmatch(pattern, url.path)
        if not match:
            raise ReachError("invalid_target", "Reddit target must be a post ID or post URL")
        return match[1]
    else:
        url = _platform_url(target, {"xiaohongshu.com", "www.xiaohongshu.com"}, https_only=True)
        tokens = parse_qs(url.query, keep_blank_values=True).get("xsec_token", [])
        if not re.fullmatch(r"/(?:explore|discovery/item)/[a-fA-F0-9]{24}/?", url.path) or len(tokens) != 1 or not tokens[0].strip():
            raise ReachError("invalid_target", "Xiaohongshu requires the complete note URL with a nonempty xsec_token")
    return target


async def social_read(platform: str, target: str) -> dict:
    """Read a public repo, tweet, Reddit post, BV video or signed XHS note URL."""
    target = _read_target(platform, target)
    try:
        if platform == "github":
            if not has_cli("gh"):
                raise ReachError("setup_required", "GitHub CLI is not installed")
            backend = "gh"
            data = _decode(await run_cli("gh", ["api", f"repos/{target}", "--method", "GET"]))
            if not isinstance(data, dict) or "private" not in data:
                raise ReachError("invalid_response", "GitHub did not return repository visibility")
            if data["private"] is not False:
                raise ReachError("invalid_target", "Only public GitHub repositories are supported")
        elif platform == "twitter":
            backend, data = await _twitter("tweet", target)
        elif platform == "reddit":
            backend, data = await _reddit("read", target)
        elif platform == "bilibili":
            backend, data = await _bilibili("video", target)
        else:
            backend, data = await _opencli("xiaohongshu", "note", target)
    except ReachError:
        raise
    except Exception:
        raise ReachError("backend_error", "Social backend failed; check configuration or retry later") from None
    return {"platform": platform, "backend": backend, "data": data}
