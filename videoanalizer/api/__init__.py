"""FastAPI Application for VideoAnalyzer and Quiz Shorts Generator."""

from fastapi import FastAPI

from videoanalizer.api.routes_quiz import hardware_router
from videoanalizer.api.routes_quiz import router as quiz_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="VideoAnalyzer & Quiz Shorts Generator API",
        version="0.1.0",
        description=(
            "Automated viral vertical shorts generator including "
            "QuizyPeasy 9-question trivia challenges."
        ),
    )

    app.include_router(quiz_router)
    app.include_router(hardware_router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
