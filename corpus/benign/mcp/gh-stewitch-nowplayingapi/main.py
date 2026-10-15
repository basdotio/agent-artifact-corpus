import uvicorn
from typing import List
from fastapi import FastAPI, HTTPException

from src.nowplayingapi.models import SongInfo
from src.nowplayingapi.services import get_now_playing_info
from src.nowplayingapi.config import settings

app = FastAPI(
    title="NowPlayingAPI",
    description="A simple API to get the current playing song from various music players on Windows.",
    version="0.2.1",
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the NowPlayingAPI!"}

@app.get(
    "/now_playing",
    response_model=List[SongInfo],
    tags=["Music"],
    summary="Get currently playing song information",
)
def get_currently_playing():
    try:
        song_info_list = get_now_playing_info()
        return song_info_list
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred while fetching song information."
        )

if __name__ == "__main__":
    
    print(f"Starting server at http://{settings.API_HOST}:{settings.API_PORT}")
    
    uvicorn.run(
        "main:app", 
        host=settings.API_HOST, 
        port=settings.API_PORT, 
        reload=True  # Set reload=False for production
    )