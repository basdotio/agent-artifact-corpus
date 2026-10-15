"""4단계 - 토큰 발급

터미널에서 돌리면 관리자 발급, 5단계에서는 로그인 흐름이 이 함수를 부릅니다.
저장소에는 해시만 남고 원본은 한 번만 보여 줍니다.
"""

import secrets, sys, json, hashlib, os, pathlib
from datetime import datetime, timedelta, timezone

DATA_DIR = pathlib.Path(os.environ.get("DATA_DIR", "."))
STORE = DATA_DIR / "tokens.json"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(user: str, *, ttl: int | None = None, resource: str | None = None) -> str:
    """user에게 새 토큰을 발급합니다. 원본을 돌려주고 저장소에는 해시만 남깁니다.

    ttl 은 수명(초)입니다. 안 주면 만료가 없습니다 - 관리자가 손으로 발급하고
    손으로 취소하는 4단계가 그렇습니다. 5단계의 로그인은 한 시간짜리를 냅니다.
    주려면 양의 정수여야 합니다. 0 은 "수명 없음"이 아니라 잘못된 값입니다.
    resource 는 이 토큰을 쓸 수 있는 서버입니다. 안 주면 제한이 없습니다.
    """
    if ttl is not None and ttl <= 0:
        raise ValueError("ttl 은 양의 정수(초)입니다. 수명을 안 둘 거면 빼세요")
    token = f"tok-{user}-{secrets.token_urlsafe(24)}"
    now = datetime.now(timezone.utc)

    tokens = json.loads(STORE.read_text(encoding="utf-8")) if STORE.exists() else []
    tokens.append({
        "token_hash": _hash(token),
        "user": user,
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl)).isoformat()
                      if ttl is not None else None,
        "resource": resource,
        "revoked": False,
    })

    tmp = STORE.with_suffix(".tmp")
    tmp.write_text(json.dumps(tokens, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STORE)          # 원자적 쓰기 - 1단계에서 만든 그 방식

    return token


def token_info(token: str) -> dict | None:
    """토큰의 저장 행을 돌려줍니다. 없거나 취소됐거나 만료됐으면 None.

    토큰을 거절하는 자리는 이 함수 하나입니다.
    """
    if not token or not STORE.exists():
        return None
    digest = _hash(token)
    now = datetime.now(timezone.utc)
    for row in json.loads(STORE.read_text(encoding="utf-8")):
        if row.get("token_hash") != digest or row.get("revoked"):
            continue
        if "expires_at" not in row or "resource" not in row:
            return None                      # 옛 형식 행 - 다시 발급받아야 합니다
        expires_at = row["expires_at"]
        if expires_at is not None:
            try:
                deadline = datetime.fromisoformat(expires_at)
            except (TypeError, ValueError):
                return None                  # 읽을 수 없는 시각은 거절합니다
            if deadline.tzinfo is None:      # 시간대가 없으면 UTC 로 봅니다
                deadline = deadline.replace(tzinfo=timezone.utc)
            if deadline <= now:
                return None                  # 수명이 다한 토큰
        return row
    return None


def resolve_token(token: str) -> str | None:
    """토큰을 사용자 이름으로 바꿉니다. 못 찾으면 None."""
    row = token_info(token)
    return row["user"] if row else None


if __name__ == "__main__":
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        sys.exit("사용법: python issue_token.py <사용자>")
    issued = issue_token(sys.argv[1])
    print(f"{sys.argv[1]} 에게 전달하세요 (한 번만 표시됩니다):\n{issued}")
