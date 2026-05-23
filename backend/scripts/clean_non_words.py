"""One-shot script: remove non-letter tokens (numbers, symbols) from the vocabulary database.

Run from backend/:
    python -m scripts.clean_non_words
"""

import asyncio
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, update, delete, func
from app.database import async_session
from app.models.article import Article, ArticleWord
from app.models.word import Word

_HAS_LETTER = re.compile(r'[a-zA-Z]')


async def clean():
    async with async_session() as db:
        # 1. Find words that contain no ASCII letter
        all_words = await db.execute(select(Word))
        all_words = all_words.scalars().all()

        invalid_ids = []
        for w in all_words:
            if not _HAS_LETTER.search(w.word_lower):
                invalid_ids.append(w.id)

        if not invalid_ids:
            print("No invalid words found. Database is clean.")
            return

        print(f"Found {len(invalid_ids)} invalid words (no letters):")
        for w in all_words:
            if w.id in invalid_ids:
                print(f"  id={w.id}  word='{w.word}'  word_lower='{w.word_lower}'")

        # 2. Update ArticleWord: set word_id=NULL, is_punctuation=True for invalid words
        result = await db.execute(
            update(ArticleWord)
            .where(ArticleWord.word_id.in_(invalid_ids))
            .values(word_id=None, is_punctuation=True, is_unknown_at_import=False)
        )
        print(f"\nUpdated {result.rowcount} ArticleWord entries (word_id -> NULL, is_punctuation=True)")

        # 3. Delete invalid Word records
        result = await db.execute(
            delete(Word).where(Word.id.in_(invalid_ids))
        )
        print(f"Deleted {result.rowcount} Word records")

        # 4. Recalculate word_count for all affected articles
        # Count non-punctuation, letter-containing tokens per article
        recalc = await db.execute(
            select(
                ArticleWord.article_id,
                func.count().label("cnt"),
            )
            .where(
                ArticleWord.is_punctuation == False,
                ArticleWord.word_id.isnot(None),
            )
            .group_by(ArticleWord.article_id)
        )
        recalc_map = {row.article_id: row.cnt for row in recalc}

        updated_articles = 0
        for article_id, new_count in recalc_map.items():
            await db.execute(
                update(Article)
                .where(Article.id == article_id)
                .values(word_count=new_count, unknown_word_count=None, i_plus_one_score=None)
            )
            updated_articles += 1

        print(f"Recalculated word_count for {updated_articles} articles (analysis reset — re-import or re-analyze to refresh)")

        await db.commit()
        print("\nCleanup complete.")


if __name__ == "__main__":
    asyncio.run(clean())
