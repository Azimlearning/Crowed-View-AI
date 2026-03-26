
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
)

print(f"User middleware: {app.user_middleware}")
for m in app.user_middleware:
    print(f"Middleware item: {m}")
    try:
        cls, options = m
        print(f"Unpacked: {cls}, {options}")
    except ValueError as e:
        print(f"Failed to unpack: {e}")
        # Inspect what's inside
        import inspect
        print(f"Type: {type(m)}")
        if hasattr(m, '__iter__'):
             print(f"Elements: {list(m)}")
