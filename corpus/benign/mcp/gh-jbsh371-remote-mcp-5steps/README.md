# 다중 사용자 원격 MCP 서버 만들기

책 『다중 사용자 원격 MCP 서버 만들기 - OAuth로 Claude와 연동하는 5단계』의 예제 코드입니다.

할 일 관리 서버 하나를 다섯 번 고쳐 갑니다. 내 PC에서만 도는 stdio 서버로 시작해서, 고객이 claude.ai에서 로그인해 쓰는 원격 MCP 서버까지 갑니다. 단계마다 서버 파일이 하나씩 들어 있습니다. 4·5단계 서버는 공통 파일 `issue_token.py` 를 같은 폴더에 두어야 실행됩니다.

- **책**: [교보문고 전자책](https://ebook-product.kyobobook.co.kr/dig/epd/ebook/E000013636679) · [YES24 전자책](https://www.yes24.com/product/goods/197087831) · [교보문고 종이책](https://product.kyobobook.co.kr/detail/S000221567577)
- **정오표**: [ERRATA.md](ERRATA.md)

책 본문은 여기 없습니다. 이 저장소가 담는 것은 예제 코드뿐입니다.

## 요구 사항

파이썬 3.10 이상이면 됩니다. 라이브러리는 FastMCP 하나이고, 점검 스크립트와 최종 장 코드가 `httpx`를 함께 씁니다.

## 설치

저장소를 받은 폴더에서 가상환경을 만들고, `requirements.txt`에 고정한 버전을 설치합니다.

```
python -m venv .venv
source .venv/bin/activate        # 윈도우 PowerShell 은 .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

설치가 끝나면 `pip show fastmcp mcp`로 `fastmcp` 4.0.3과 `mcp` 2.1.1이 깔렸는지 확인합니다.

## 파일

| 파일 | 단계 | 내용 |
|---|---|---|
| `todo_v1.py` | 1 | stdio. 사용자 개념이 없습니다 |
| `todo_v2.py` | 2 | `user` 필드. 사용자가 자기 이름을 인자로 댑니다 |
| `todo_v3.py` | 3 | HTTP. 요청 헤더에 실린 토큰으로 사용자를 확인합니다 |
| `todo_v4.py` | 4 | 배포용. 토큰 저장소가 파일로 바뀝니다 |
| `todo_v5.py` | 5 | OAuth. 로그인 화면과 토큰 발급이 서버 안에 들어옵니다 |
| `issue_token.py` | 4·5 | 토큰 발급과 조회 |
| `check_v3.py` | 3·4 | Inspector 없이 돌려 보는 점검 스크립트 |
| `todo_adapter.py` | 최종 장 | v5에서 도구 몸통만 서비스 API 호출로 바꾼 것 |
| `service_api.py` | 최종 장 | "여러분의 서비스 API" 자리에 서는 예제 API |
| `test_smoke.py` | - | 다섯 단계와 경계 상황을 한 번에 돌려 보는 점검 |

## 실행

아래는 파일별 실행 예입니다. 위에서 아래로 다 치는 순서가 아닙니다. 실습할 단계의 서버 하나를 골라 띄우고, 최종 장은 `service_api.py` 와 `todo_adapter.py` 를 각각 다른 터미널에서 띄웁니다.

```
(.venv) $ python todo_v1.py                # stdio. Claude Desktop 이 실행합니다
(.venv) $ python todo_v3.py                # http://127.0.0.1:8000/mcp
(.venv) $ python check_v3.py <토큰>        # 3단계 점검. MCP_URL 로 배포 주소를 줄 수 있습니다
(.venv) $ python issue_token.py kim        # 토큰 발급
(.venv) $ python todo_v4.py                # 0.0.0.0:8000
(.venv) $ python todo_v5.py                # OAuth
(.venv) $ python service_api.py            # 최종 장. 예제 서비스 API :8001 (먼저 띄웁니다)
(.venv) $ python todo_adapter.py           # 최종 장. 몸통 교체판 :8000
```

`(.venv) $` 는 가상환경이 켜진 터미널이라는 표시입니다. 입력하지 않습니다.

`todo_v5.py` 는 띄우기 전에 `BASE_URL` 을 실제 접속 주소로 맞춰 주세요. 로그인 화면 주소가 이 값에서 나옵니다.

```
(.venv) $ BASE_URL=https://내주소 python todo_v5.py
# 윈도우 PowerShell: $env:BASE_URL="https://내주소"; python todo_v5.py
```

## 점검

```
(.venv) $ python test_smoke.py
```

다섯 단계를 순서대로 돌립니다. 5단계는 등록·인가·로그인·코드 교환·도구 호출까지 전 과정을 왕복합니다. 마지막에는 **두 계정이 서로의 데이터를 못 본다**는 것까지 확인합니다. 53개 항목입니다.

## 실습 계정 (5단계)

| 아이디 | 비밀번호 |
|---|---|
| kim | `kim-pw` |
| lee | `lee-pw` |
| park | `park-pw` |

코드에 적혀 있는 실습용 계정입니다. 실전에서는 이 자리에 여러분의 회원 데이터베이스가 섭니다.

## 코드에서 눈여겨볼 세 곳

아래 세 곳은 읽다 보면 없어도 될 것처럼 보이지만, 빼면 서버가 동작하지 않습니다.

**`get_http_headers(include={"authorization"})`** - 3·4단계입니다. 인자 없이 부르면 FastMCP가 `authorization` 헤더를 지웁니다. 토큰이 늘 빈 문자열이 되어 도구 실행이 모두 실패하는데, 증상은 "토큰이 잘못됐다"로 보입니다.

**`ClientRegistrationOptions(enabled=True)`** - 5단계입니다. 동적 등록(DCR)은 기본이 꺼져 있어서, 안 켜면 `/register` 가 404입니다. 그러면 클라이언트 정보 문서(CIMD)가 없는 클라이언트는 등록할 방법이 없습니다. 이 서버는 동적 등록과 클라이언트 정보 문서를 모두 받습니다.

**`claims={"sub": user}`** - 5단계입니다. 인가 코드는 `subject` 에, 접근 토큰은 `claims` 에 사용자를 싣습니다. 도구에서는 `claims["sub"]` 로 꺼냅니다. `sub` 는 JWT 표준에서 "누구"를 담는 이름을 빌려 온 것이고, 이 예제에서 정한 규칙입니다.

데이터 파일 경로도 하나 덧붙입니다. 1~3단계는 `todos.json` 의 경로를 스크립트 기준(`Path(__file__).parent`)으로 잡았습니다. stdio 서버의 작업 폴더는 클라이언트가 정하기 때문에, 상대 경로로 쓰면 엉뚱한 곳에 파일이 생기거나 권한 오류가 납니다. 4·5단계는 `DATA_DIR` 환경변수로 저장 폴더를 정하고, 없으면 실행한 작업 폴더를 씁니다.

## 1단계 실습 3에서 붙여 넣는 줄

책의 1단계 실습 3에서 `todo_v1.py`를 띄운 터미널에 통째로 붙여 넣는 줄입니다. 책에서는 쪽 폭 때문에 여러 줄로 꺾여 보이지만 실제로는 한 줄입니다. 아래 칸의 복사 버튼으로 복사해 붙이세요.

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"add_todo","arguments":{"text":"책 반납하기"},"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}
```

## 버전

`requirements.txt` 는 `fastmcp==4.0.3` 과, 그 아래에서 도는 기반 SDK `mcp==2.1.1` 을 함께 고정합니다. `fastmcp` 만 고정하면 딸려 오는 `mcp` 버전이 설치 시점에 따라 달라지기 때문입니다. 책이 이 버전을 기준으로 삼은 이유는 **2026년 7월 28일 MCP 개정에 대응하는 세대**이기 때문입니다. 그 이전 세대(3.4.x)에서도 이 코드는 실행됩니다. 다만 규격이 개정 이전이라, 책의 설명과 어긋나는 곳이 생깁니다.

파이썬은 3.10과 3.13에서 확인했고 3.10 이상이면 됩니다.

### 기준 버전 뒤에 확인한 버전

| 날짜 | 조합 | 결과 |
|---|---|---|
| 2026-09-28 | `fastmcp` 4.0.10 + `mcp` 2.2.0 | `test_smoke.py` 53개 모두 통과. 고칠 것 없음 |

책과 같게 따라 하시려면 `requirements.txt`에 고정한 버전을 쓰세요. 책의 코드나 절차를 고쳐야 하는 변경이 생기면 이 표에 적고 무엇을 고치는지 함께 안내합니다.

이 저장소 맨 위 폴더의 파일은 책에 실린 코드와 같게 둡니다. 책을 낼 때의 코드는 태그 `book-1.0`으로도 남겨 두었습니다 - https://github.com/jbsh371/remote-mcp-5steps/tree/book-1.0

## 라이선스

MIT입니다. 쓰시고 고치시고 여러분 서비스에 넣으셔도 됩니다. 코드를 복사해 배포하실 때는 저작권 표시와 허가문을 함께 남겨 주세요. [LICENSE](LICENSE) 파일을 같이 두시면 됩니다.
