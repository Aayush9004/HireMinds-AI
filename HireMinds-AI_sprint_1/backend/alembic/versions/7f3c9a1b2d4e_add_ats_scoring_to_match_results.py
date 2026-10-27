"""add_ats_scoring_to_match_results

Revision ID: 7f3c9a1b2d4e
Revises: 0e72ba8e5bf5
Create Date: 2026-10-27 12:00:00.000000

Phase 7 stores an explainable ATS score and its full component breakdown on the
existing cached match result row. This avoids a second per-pair table and keeps
the Phase 6 and Phase 7 scores together.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f3c9a1b2d4e'
down_revision: Union[str, Sequence[str], None] = '0e72ba8e5bf5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'match_results',
        sa.Column(
            'ats_score',
            sa.Float(),
            nullable=True,
            comment='Explainable ATS score (0-100); null when no component could be assessed',
        ),
    )
    op.add_column(
        'match_results',
        sa.Column(
            'ats_breakdown',
            sa.JSON(),
            nullable=True,
            comment='Full component breakdown: scores, weights, rationales, evidence, missing data',
        ),
    )
    op.add_column(
        'match_results',
        sa.Column(
            'ats_weights',
            sa.JSON(),
            nullable=True,
            comment='Snapshot of weights used when this ATS score was computed',
        ),
    )
    op.add_column(
        'match_results',
        sa.Column(
            'ats_version',
            sa.String(length=50),
            nullable=True,
            comment='ATS scoring model/version identifier',
        ),
    )
    op.add_column(
        'match_results',
        sa.Column(
            'ats_confidence',
            sa.String(length=20),
            nullable=True,
            comment='high, medium, low, or none',
        ),
    )
    op.add_column(
        'match_results',
        sa.Column(
            'ats_status',
            sa.String(length=30),
            nullable=True,
            comment='scored, partial, or insufficient_data',
        ),
    )
    op.create_index(
        op.f('ix_match_results_ats_score'),
        'match_results',
        ['ats_score'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_match_results_ats_score'), table_name='match_results')
    op.drop_column('match_results', 'ats_status')
    op.drop_column('match_results', 'ats_confidence')
    op.drop_column('match_results', 'ats_version')
    op.drop_column('match_results', 'ats_weights')
    op.drop_column('match_results', 'ats_breakdown')
    op.drop_column('match_results', 'ats_score')
