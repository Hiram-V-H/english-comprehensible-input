from __future__ import annotations

from fastapi import APIRouter

from .analysis import router as analysis_router
from .annotation import router as annotation_router
from .article import router as article_router
from .books import router as books_router
from .health import router as health_router
from .import_ import router as import_router
from .reader import router as reader_router
from .tags import router as tags_router
from .vocabulary import router as vocabulary_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(vocabulary_router, tags=["vocabulary"])
api_router.include_router(article_router, tags=["articles"])
api_router.include_router(import_router, tags=["import"])
api_router.include_router(analysis_router, tags=["analysis"])
api_router.include_router(reader_router, tags=["reader"])
api_router.include_router(annotation_router, tags=["annotations"])
api_router.include_router(tags_router, tags=["tags"])
api_router.include_router(books_router, tags=["books"])
