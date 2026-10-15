# 과제 제출 주의 사항

아래 사항을 확인하여 제출해 주세요. 오해를 줄이기 위해 예시와 함께 간단한 검증 방법을 함께 제공합니다.

## 제출 형식

- 반드시 .tar.gz 형식으로 압축하여 제출합니다. 파일명은 `{팀명}.tar.gz` 형식이어야 합니다. 예: `ABC팀.tar.gz`.

## 필수 파일 및 위치(가장 중요)

- 압축을 풀었을 때 "최상위(루트) 디렉터리"에 `main.py` 파일이 바로 존재해야 합니다. 즉, 압축을 푼 폴더를 열었을 때 곧바로 `main.py`가 보여야 합니다. 서브폴더(`src/`, `app/` 등) 안에 들어가 있으면 안 됩니다.

- 또한 `requirements.txt` 파일을 프로젝트 루트에 반드시 포함해야 합니다. 심사 시 의존성 설치는 `pip install -r requirements.txt` 명령으로 이루어집니다.

### 잘된 예

- my-project/
  - main.py
  - README.md
  - requirements.txt

### 잘못된 예 (NG)

- my-project/
  - src/
    - main.py
  - README.md

## 압축(예시)

프로젝트 폴더가 `my-project/` 라면 아래처럼 압축합니다:

```bash
tar -czf {팀명}.tar.gz -C my-project/ .
```

예: 팀명이 "team-rocket"이라면 `tar -czf team-rocket.tar.gz -C my-project/ .`

## 제출 전 자동검사(간단)

로컬에서 압축을 풀고 `main.py`와 `requirements.txt`가 루트에 있는지 확인하는 간단한 커맨드:

```bash
if [ -f /tmp/extract_check/main.py ] && [ -f /tmp/extract_check/requirements.txt ]; then
  echo "OK: main.py and requirements.txt found at archive root"
else
  echo "ERROR: main.py or requirements.txt NOT found at archive root" && exit 1
fi
```

## 실행 환경

- 제출물은 Python 3.11 환경에서 동작해야 합니다.
- 실행 전 의존성 설치 예시:

```bash
python -m venv venv
source venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
python main.py
```

## 추가 권장사항

- `main.py`는 UTF-8로 인코딩되어 있어야 하며(한글 포함 시 인코딩 문제 방지)

## 평가/검증 기준(요약)

- 압축 해제 루트에 `main.py` 존재 여부 (필수)
- `requirements.txt`가 프로젝트 루트에 포함되어 있는지 (필수)
- Python 3.11에서 `python main.py`로 동작하는지 (필수)
