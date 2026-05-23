from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..services import analysis_service
from .deps import get_db

router = APIRouter(tags=["analysis"])


@router.get("/articles/{article_id}/analysis")
async def get_analysis(article_id: int, db: AsyncSession = Depends(get_db)):
    analysis = await analysis_service.get_analysis(db, article_id)
    return {"status": "ok", "data": analysis}


@router.post("/articles/{article_id}/analysis/reanalyze")
async def reanalyze_article(article_id: int, db: AsyncSession = Depends(get_db)):
    results = await analysis_service.reanalyze(db, article_id)
    return {
        "status": "ok",
        "data": {
            "results": [
                {
                    "algorithm_name": r.algorithm_name,
                    "score": r.score,
                    "label": r.label,
                    "details": r.details,
                }
                for r in results
            ]
        },
    }
