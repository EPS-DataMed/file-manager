from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import file

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(file.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the file manager API"}