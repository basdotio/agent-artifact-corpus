from fastapi import FastAPI
from app.api.orders import router
app = FastAPI()
app.include_router(router)
