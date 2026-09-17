---
name: new-domain
description: This skill should be used when the user asks to "create a new domain", "add new domain", "새로운 도메인 생성", "도메인 추가", or mentions creating a new business module in the FastAPI project.
version: 1.0.0
---

# New Domain Generator

FastAPI 프로젝트에 새로운 도메인을 추가할 때 프로젝트 컨벤션을 따르는 표준 구조를 자동 생성합니다.

## 사용 시점

- 새로운 비즈니스 도메인 추가 시
- CRUD 기능이 필요한 새 엔티티 생성 시
- 예: "상품(Product) 도메인 추가해줘", "댓글(Comment) 도메인 만들어줘"

## 실행 플로우

### 1단계: 도메인 정보 수집

다음 정보를 사용자에게 질문합니다:

```yaml
질문 1: 도메인 이름은?
  - 예: product, comment, order, payment
  - 영문 소문자, 단수형 권장

질문 2: 주요 필드는?
  - 예: title:String, content:Text, price:Integer
  - 형식: 필드명:타입

질문 3: CRUD 엔드포인트 생성?
  - 선택: 전체(list/detail/create/update/delete) | 기본(list/detail/create) | 커스텀

질문 4: 인증 필요 여부?
  - create/update/delete에 get_current_user_with_async 의존성 추가 여부

질문 5: 추가 기능?
  - 투표(vote) 기능
  - Many-to-Many 관계 (예: voter)
  - 검색(keyword) 기능
```

### 2단계: 파일 생성

#### 2.1 디렉토리 생성
```bash
src/domains/{domain_name}/
├── __init__.py
├── router.py
├── service.py
├── models.py
├── schemas.py
└── (선택) dependencies.py
```

#### 2.2 models.py 생성

```python
# 템플릿 기반 생성
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from src.database.database import Base

# Many-to-Many가 필요한 경우
{domain}_voter = Table(
    '{domain}_voter',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('{domain}_id', Integer, ForeignKey('{domain}.id'), primary_key=True)
)

class {Domain}(Base):
    __tablename__ = "{domain}"

    id = Column(Integer, primary_key=True)
    # 사용자 입력 필드 추가
    create_date = Column(DateTime, nullable=False)
    modify_date = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", backref="{domain}_users")
    # voter가 필요한 경우
    voter = relationship('User', secondary={domain}_voter, backref='{domain}_voters')
```

**컨벤션 적용 포인트:**
- ✅ `__tablename__` = 소문자 단수형
- ✅ `create_date`, `modify_date` 자동 추가
- ✅ `user_id` + `user` relationship 자동 추가
- ✅ voter 패턴 선택적 추가

#### 2.3 schemas.py 생성

```python
from __future__ import annotations
import datetime
from typing import Union
from pydantic import BaseModel, field_validator
from src.domains.user.schemas import User

class {Domain}(BaseModel):
    id: int
    # 사용자 입력 필드
    create_date: datetime.datetime
    modify_date: Union[datetime.datetime, None] = None
    user: Union[User, None]
    voter: list[User] = []

class {Domain}List(BaseModel):
    total: int = 0
    {domain}_list: list[{Domain}] = []

class {Domain}Create(BaseModel):
    # 사용자 입력 필드 (id, 날짜 제외)

    @field_validator("필드명들")
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("필드를 입력해주세요")
        return v

class {Domain}Update({Domain}Create):
    {domain}_id: int

class {Domain}Delete(BaseModel):
    {domain}_id: int

# 투표 기능이 필요한 경우
class {Domain}Vote(BaseModel):
    {domain}_id: int
```

**컨벤션 적용 포인트:**
- ✅ 응답: `{Domain}`, 리스트: `{Domain}List`
- ✅ 요청: `{Domain}Create/Update/Delete/Vote`
- ✅ `field_validator` + 한글 에러 메시지
- ✅ `Union[Type, None]` 타입 힌팅

#### 2.4 service.py 생성

```python
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.domains.{domain}.models import {Domain}
from src.domains.{domain}.schemas import {Domain}Create, {Domain}Update
from src.domains.user.models import User
from src.common.events import DomainEvent, EventType, event_bus

async def get_{domain}_list(
    db: AsyncSession,
    offset: int = 0,
    limit: int = 10,
    keyword: str = ''
):
    query = select({Domain})
    if keyword:
        search = f'%%{keyword}%%'
        query = query.filter({Domain}.필드명.ilike(search))

    total = await db.execute(select(func.count()).select_from(query))
    result = await db.execute(
        query.offset(offset).limit(limit)
        .order_by({Domain}.create_date.desc())
        .options(selectinload({Domain}.user))
        .options(selectinload({Domain}.voter))
    )
    return total.scalar_one(), result.scalars().fetchall()

async def get_{domain}(db: AsyncSession, {domain}_id: int):
    stmt = (
        select({Domain})
        .where({Domain}.id == {domain}_id)
        .options(
            selectinload({Domain}.user),
            selectinload({Domain}.voter)
        )
    )
    result = await db.execute(stmt)
    return result.scalars().one_or_none()

async def create_{domain}(
    db: AsyncSession,
    {domain}_create: {Domain}Create,
    user: User
):
    db_{domain} = {Domain}(
        # 필드 매핑
        create_date=datetime.now(),
        user=user
    )
    db.add(db_{domain})
    await db.commit()

async def update_{domain}(
    db: AsyncSession,
    {domain}_model: {Domain},
    {domain}_update: {Domain}Update
):
    # 필드 업데이트
    {domain}_model.modify_date = datetime.now()
    db.add({domain}_model)
    await db.commit()

async def delete_{domain}(db: AsyncSession, {domain}_model: {Domain}):
    await db.delete({domain}_model)
    await db.commit()

async def vote_{domain}(
    db: AsyncSession,
    {domain}_model: {Domain},
    db_user: User
):
    {domain}_model.voter.append(db_user)
    await db.commit()
    await event_bus.publish(DomainEvent(
        event_type=EventType.{DOMAIN}_VOTED,
        actor_user_id=db_user.id,
        target_user_id={domain}_model.user_id,
        resource_id={domain}_model.id,
        resource_type="{domain}",
        message=f"{db_user.username}님이 회원님의 {domain}에 투표했습니다.",
    ))
```

**컨벤션 적용 포인트:**
- ✅ 함수명: `{action}_{domain}` 패턴
- ✅ `async/await` 사용
- ✅ `selectinload`로 관계 로딩
- ✅ 명시적 `await db.commit()`
- ✅ 이벤트 발행 (vote 시)

#### 2.5 router.py 생성

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from src.database.database import get_async_db
from src.domains.{domain} import schemas as {domain}_schema, service as {domain}_service
from src.domains.user.schemas import User
from src.domains.user.router import get_current_user_with_async

router = APIRouter(
    prefix="/api/{domain}",
)

@router.get("/list", response_model={domain}_schema.{Domain}List)
async def {domain}_list(
    db: AsyncSession = Depends(get_async_db),
    page: int = 0,
    size: int = 10,
    keyword: str = ''
):
    total, _{domain}_list = await {domain}_service.get_{domain}_list(
        db, offset=page * size, limit=size, keyword=keyword
    )
    return {"total": total, "{domain}_list": _{domain}_list}

@router.get("/detail/{{id}}", response_model={domain}_schema.{Domain})
async def {domain}_detail(
    {domain}_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    {domain} = await {domain}_service.get_{domain}(db, {domain}_id)
    if {domain} is None:
        raise HTTPException(status_code=404, detail="{Domain}을 찾을 수 없습니다")
    return {domain}

@router.post("/create", status_code=status.HTTP_204_NO_CONTENT)
async def {domain}_create(
    _{domain}_create: {domain}_schema.{Domain}Create,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async)
):
    await {domain}_service.create_{domain}(
        db=db,
        {domain}_create=_{domain}_create,
        user=current_user
    )

@router.put("/update", status_code=status.HTTP_204_NO_CONTENT)
async def {domain}_update(
    _{domain}_update: {domain}_schema.{Domain}Update,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async)
):
    {domain}_model = await {domain}_service.get_{domain}(
        db, {domain}_id=_{domain}_update.{domain}_id
    )
    if not {domain}_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="데이터를 찾을 수 없습니다."
        )

    if current_user.id != {domain}_model.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정 권한이 없습니다."
        )

    await {domain}_service.update_{domain}(
        db=db,
        {domain}_model={domain}_model,
        {domain}_update=_{domain}_update
    )

@router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def {domain}_delete(
    _{domain}_delete: {domain}_schema.{Domain}Delete,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async)
):
    {domain}_model = await {domain}_service.get_{domain}(
        db, {domain}_id=_{domain}_delete.{domain}_id
    )
    if not {domain}_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="데이터를 찾을 수 없습니다."
        )

    if current_user.id != {domain}_model.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="삭제 권한이 없습니다."
        )

    await {domain}_service.delete_{domain}(db=db, {domain}_model={domain}_model)

@router.post("/vote", status_code=status.HTTP_204_NO_CONTENT)
async def {domain}_vote(
    _{domain}_vote: {domain}_schema.{Domain}Vote,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user_with_async)
):
    {domain}_model = await {domain}_service.get_{domain}(
        db, {domain}_id=_{domain}_vote.{domain}_id
    )
    if not {domain}_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="데이터를 찾을 수 없습니다."
        )

    await {domain}_service.vote_{domain}(
        db, {domain}_model={domain}_model, db_user=current_user
    )
```

**컨벤션 적용 포인트:**
- ✅ `prefix="/api/{domain}"`
- ✅ 함수명: `{domain}_{action}`
- ✅ 파라미터: `_{domain}_create` (언더스코어 접두사)
- ✅ 한글 에러 메시지
- ✅ 권한 검증 패턴 (`current_user.id != model.user_id`)
- ✅ `status.HTTP_204_NO_CONTENT` for CUD 작업

### 3단계: main.py에 라우터 등록

```python
# main.py 자동 수정
from src.domains.{domain} import router as {domain}_router

app.include_router({domain}_router.router)
```

### 4단계: Alembic 마이그레이션 (선택)

사용자에게 물어보기:
```
"DB 마이그레이션을 생성하고 적용할까요?"
→ Yes: alembic revision --autogenerate -m "Add {domain} table"
       alembic upgrade head
→ No: 나중에 /db-migrate 사용 안내
```

### 5단계: 완료 리포트

```markdown
✅ {Domain} 도메인 생성 완료!

생성된 파일:
- src/domains/{domain}/router.py (5개 엔드포인트)
- src/domains/{domain}/service.py (6개 함수)
- src/domains/{domain}/models.py ({Domain} 모델)
- src/domains/{domain}/schemas.py (6개 스키마)

등록된 라우터:
- GET /api/{domain}/list
- GET /api/{domain}/detail/{id}
- POST /api/{domain}/create
- PUT /api/{domain}/update
- DELETE /api/{domain}/delete
- POST /api/{domain}/vote

다음 단계:
1. 서버 재시작: docker-compose restart
2. API 문서 확인: http://localhost:7777/docs
3. 테스트 생성: /test-gen {domain}
```

## 컨벤션 체크리스트

생성된 코드가 다음 컨벤션을 따르는지 자동 검증:

- [ ] 함수명이 snake_case인가?
- [ ] 라우터 함수명이 `{domain}_{action}`인가?
- [ ] 서비스 함수명이 `{action}_{domain}`인가?
- [ ] 한글 에러 메시지를 사용하는가?
- [ ] create_date, modify_date가 있는가?
- [ ] async/await를 사용하는가?
- [ ] selectinload로 관계를 로딩하는가?
- [ ] 권한 검증이 있는가? (update/delete)
- [ ] 명시적 db.commit()을 호출하는가?

## 참고사항

- 생성 후 즉시 사용 가능한 완전한 CRUD API가 제공됩니다
- 프로젝트의 기존 패턴과 100% 일치하는 코드가 생성됩니다
- 필요시 생성 후 수동으로 커스터마이징 가능합니다
