---
name: add-triton-to-rayworker
description: kuberay_worker에 새로운 Triton 모델을 위한 Ray Serve app/deployment를 등록합니다. 인터랙티브하게 모델 선택, 참조 파일 선택, 주의사항 확인 후 작업을 진행합니다.
disable-model-invocation: true
---

# Kuberay Worker에 Triton 모델 등록

이 skill은 Triton Inference Server 모델을 kuberay_worker에서 사용할 수 있도록 Ray Serve deployment와 app을 등록합니다.

## 작업 흐름

### 1단계: 추가 가능한 모델 목록 표시

다음 경로에서 Triton 모델 목록을 확인합니다:
- `submodules/Toonkit-Triton-heavy/models/`
- `submodules/Toonkit-Triton-light/models/`

그리고 `src/kuberay_worker/models/`에 이미 등록된 모델을 확인합니다.

**Triton에는 있지만 kuberay_worker에는 없는 모델만** 목록으로 표시하고, 사용자에게 어떤 모델을 추가할지 질문합니다.

### 2단계: 참조할 기존 모델 선택

`src/kuberay_worker/schemas/`와 `src/kuberay_worker/models/`에 있는 기존 모델 파일들을 나열하고, 사용자에게 다음을 질문합니다:

- 어떤 기존 모델의 패턴을 참고할 것인지? (예: zimage, inpaint, sam2 등)
- 추가로 참고해야 할 파일이나 문서가 있는지?

### 3단계: 추가 주의사항 확인

사용자에게 다음을 질문합니다:

- 특별히 주의할 점이 있는지? (예: 특정 입력 처리 방식, LoRA 지원 여부, 이미지 다운로드/업로드 필요 여부 등)
- 네이밍 규칙에 대한 특별한 요구사항이 있는지?

### 4단계: 최종 작업 계획 수립

수집한 정보를 바탕으로 다음 내용을 포함한 작업 계획을 작성합니다:

1. **분석할 파일 목록**
   - 선택한 Triton 모델의 `config.pbtxt`
   - 참조할 기존 모델의 schema, model 파일
   - 베이스 클래스 파일들

2. **생성할 파일 목록**
   - `src/kuberay_worker/schemas/{모델명}.py`
   - `src/kuberay_worker/models/{모델명}.py`

3. **수정할 파일 목록**
   - `src/kuberay_worker/schemas/__init__.py`
   - `src/kuberay_worker/models/__init__.py`

4. **네이밍 규칙**
   - 파일명, 클래스명, 함수명, MODEL_NAME 등

5. **주요 구현 사항**
   - Triton input/output 매핑
   - LoRA 지원 여부
   - 이미지 처리 방식

작업 계획을 사용자에게 보여주고 승인을 받은 후 구현을 진행합니다.

### 5단계: 구현 진행

승인된 계획에 따라 파일들을 생성하고 수정합니다.

### 6단계: 문서화

작업 완료 후 다음 문서를 작성/수정합니다:

1. **작업 기록 문서 생성**: `docs/YYYY-MM-DD-{모델명}.md`
   - 작업 일자 (오늘 날짜)
   - 추가한 모델 이름
   - 생성/수정한 파일 목록
   - Triton input/output 스펙 요약
   - 주요 구현 사항 및 특이사항
   - 사용 예시

2. **README.md 업데이트**
   - 지원 모델 목록에 새 모델 추가
   - 필요시 사용법 섹션 업데이트

## 참고: 기본 네이밍 규칙

| 항목 | 규칙 | 예시 |
|------|------|------|
| 파일명 | 언더스코어 제거, 소문자 | `flux_klein_i2i` → `fluxkleini2i.py` |
| Schema 클래스명 | PascalCase + Schema | `FluxKleinI2iSchema` |
| Deployment 클래스명 | PascalCase + Deployment | `FluxKleinI2iDeployment` |
| App 함수명 | 파일명 + `_app` | `fluxkleini2i_app` |
| MODEL_NAME | Triton config의 `name`과 동일 | `"flux_klein_i2i"` |

## 참고: Triton 데이터 타입 매핑

| Triton 타입 | NumPy 변환 |
|-------------|-----------|
| TYPE_STRING | `np.array([값.encode("utf-8")])` |
| TYPE_INT32 | `np.array([값], dtype=np.int32)` |
| TYPE_INT64 | `np.array([값], dtype=np.int64)` |
| TYPE_FP32 | `np.array([값], dtype=np.float32)` |
| TYPE_UINT8 (이미지) | `np.asarray(이미지, dtype=np.uint8)` |
