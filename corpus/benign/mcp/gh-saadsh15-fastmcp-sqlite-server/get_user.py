from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr, model_validator
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, DateTime, Index, select, func
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional

router = APIRouter()
engine = create_engine("sqlite:///arzonama.db")
metadata = MetaData()
users_table = Table(
    "user",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("full_name", String, nullable=False),
    Column("email", String, nullable=False),
    Column("password", String(255), nullable=False),
    Column("created_at", DateTime, server_default=func.now()),
    Column("is_premium", Boolean, nullable=False, default=False)
)
Index("ix_user_email", users_table.c.email)
metadata.create_all(engine, checkfirst=True)

class UserFilterParams(BaseModel):
    user_id: Optional[int] = Query(None, description="Filter by user ID", ge =1)
    name: Optional[str] = Query(None, description="Filter by user name", min_length=2)
    email: Optional[EmailStr] = Query(None, description="Filter by user email")
    limit: int = Query(100, description="Maximum number of users to return", ge=1, le=500)
    offset: int = Query(0, description="Number of matching users to skip", ge=0)
    
    #Automatically Validate that at at least one search feild is provided
    @model_validator(mode="after")
    def check_at_least_one_filter_provided(self):
        if self.user_id is None and self.name is None and self.email is None:
            raise ValueError("At least one filter parameter must be provided")
        return self
    
@router.get("/get_user")                                                                                                            
def get_user(params: UserFilterParams = Depends()):                                                                           
    query = select(
        users_table.c.id,
        users_table.c.full_name,
        users_table.c.email,
        users_table.c.created_at,
        users_table.c.is_premium,
    )
                                                                                                                                        
    if params.user_id is not None:
        query = query.where(users_table.c.id == params.user_id)
    if params.name:
        query = query.where(users_table.c.full_name.ilike(f"%{params.name}%"))
    if params.email:
        query = query.where(users_table.c.email == params.email)

    query = query.order_by(users_table.c.id).limit(params.limit).offset(params.offset)
  
    try:
        with engine.connect() as connection:
            result = connection.execute(query).fetchall()
            if not result:
                raise HTTPException(status_code=200, detail="No users found matching the provided criteria")

            return [dict(row._mapping) for row in result]

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")