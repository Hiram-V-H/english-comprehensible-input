"""merge duplicate Word records by lemma, update ArticleWord references

Revision ID: 009
Revises: 008
Create Date: 2026-05-31
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge existing Word records that share the same lemma.

    For each lemma group, keep the record with the highest encounter_count,
    sum all encounter_counts, update ArticleWord.word_id to point to the
    survivor, then delete the redundant records.
    """
    conn = op.get_bind()

    # Test nltk availability before importing lemmatizer.
    # The lemmatize import always succeeds (nltk import is lazy),
    # so we test nltk directly to provide a real safety net.
    try:
        import nltk  # noqa: F401
    except ImportError:
        # NLTK not available during migration — skip data merge.
        # The analysis layer will still work correctly for future imports.
        return

    from app.services.lemmatizer import lemmatize

    # Fetch all Word records
    result = conn.execute(
        sa.text("SELECT id, word, word_lower, status, encounter_count, notes FROM words")
    )
    rows = list(result.mappings().all())

    if not rows:
        return

    # Group by lemma, persisting the computed lemma for each word
    lemma_groups: dict[str, list[dict]] = {}
    for row in rows:
        lemma = lemmatize(row["word_lower"])
        lemma_groups.setdefault(lemma, []).append(dict(row))
        conn.execute(
            sa.text("UPDATE words SET lemma = :lemma WHERE id = :id"),
            {"lemma": lemma, "id": row["id"]},
        )

    # Process groups with >1 member
    merged = 0
    merged_groups = 0
    for lemma, group in lemma_groups.items():
        if len(group) <= 1:
            continue
        merged_groups += 1

        # Sort: keep the one with highest encounter_count, then oldest id
        group.sort(key=lambda r: (-r["encounter_count"], r["id"]))
        survivor = group[0]

        # Update survivor's word_lower to the lemma so future lookups work
        if survivor["word_lower"] != lemma:
            conn.execute(
                sa.text("UPDATE words SET word_lower = :lemma WHERE id = :id"),
                {"lemma": lemma, "id": survivor["id"]},
            )

        for duplicate in group[1:]:
            dup_id = duplicate["id"]

            # Update ArticleWord references to point to survivor
            conn.execute(
                sa.text(
                    "UPDATE article_words SET word_id = :new_id "
                    "WHERE word_id = :old_id"
                ),
                {"new_id": survivor["id"], "old_id": dup_id},
            )

            # Sum encounter counts into survivor
            conn.execute(
                sa.text(
                    "UPDATE words SET encounter_count = encounter_count + :dup_encounters "
                    "WHERE id = :survivor_id"
                ),
                {"dup_encounters": duplicate["encounter_count"], "survivor_id": survivor["id"]},
            )

            # Fix annotated_html: replace old word-id with survivor id
            # SQLite REPLACE handles the string substitution inside the HTML blob
            conn.execute(
                sa.text(
                    "UPDATE articles SET annotated_html = REPLACE("
                    "annotated_html, 'data-word-id=\"' || :old || '\"', "
                    "'data-word-id=\"' || :new || '\"') "
                    "WHERE annotated_html IS NOT NULL"
                ),
                {"old": str(dup_id), "new": str(survivor["id"])},
            )

            # If duplicate has notes and survivor doesn't, copy them
            if duplicate.get("notes") and not survivor.get("notes"):
                conn.execute(
                    sa.text("UPDATE words SET notes = :notes WHERE id = :sid"),
                    {"notes": duplicate["notes"], "sid": survivor["id"]},
                )
                survivor["notes"] = duplicate["notes"]

            # Delete the duplicate WordNote records first
            conn.execute(
                sa.text("DELETE FROM word_notes WHERE word_id = :wid"),
                {"wid": dup_id},
            )

            # Delete the duplicate Word record
            conn.execute(
                sa.text("DELETE FROM words WHERE id = :wid"),
                {"wid": dup_id},
            )
            merged += 1

    if merged:
        print(f"Merged {merged} duplicate Word records across {merged_groups} lemma groups")


def downgrade() -> None:
    """Cannot unmerge — this is a data compaction migration."""
    pass
