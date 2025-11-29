"""
Rule-Based Trading Server.

Entry point for the trading application.
All functionality is in src/api/app.py and its routers.

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

:copyright: (c) 2025
:license: MIT
"""

from src.api.app import create_app


app = create_app(
    title="Rule-Based Trading API",
    description="Multi-user rule-based automated trading system",
    version="1.0.0",
    debug=True,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
