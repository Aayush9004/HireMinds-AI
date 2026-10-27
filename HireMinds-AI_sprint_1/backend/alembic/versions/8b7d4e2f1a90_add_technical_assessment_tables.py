"""add_technical_assessment_tables

Revision ID: 8b7d4e2f1a90
Revises: 7f3c9a1b2d4e
Create Date: 2026-10-27 15:00:00.000000

Phase 8 stores generated technical assessments, their questions, candidate
attempts and deterministic per-question answers/results.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b7d4e2f1a90'
down_revision: Union[str, Sequence[str], None] = '7f3c9a1b2d4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'assessments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('active', 'archived', name='assessmentstatus', native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('passing_score', sa.Float(), nullable=False),
        sa.Column('generation_model', sa.String(length=100), nullable=True),
        sa.Column('generation_prompt_version', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_assessments_id'), 'assessments', ['id'], unique=False)
    op.create_index(op.f('ix_assessments_job_id'), 'assessments', ['job_id'], unique=False)
    op.create_index(op.f('ix_assessments_created_by_id'), 'assessments', ['created_by_id'], unique=False)
    op.create_index(op.f('ix_assessments_status'), 'assessments', ['status'], unique=False)

    op.create_table(
        'assessment_questions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=False),
        sa.Column(
            'question_type',
            sa.Enum('mcq', 'coding', name='questiontype', native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('skill_tag', sa.String(length=120), nullable=True),
        sa.Column('difficulty', sa.String(length=20), nullable=False),
        sa.Column('points', sa.Float(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('correct_answer', sa.String(length=255), nullable=True),
        sa.Column('language', sa.String(length=30), nullable=True),
        sa.Column('function_name', sa.String(length=120), nullable=True),
        sa.Column('starter_code', sa.Text(), nullable=True),
        sa.Column('test_cases', sa.JSON(), nullable=True),
        sa.Column('time_limit_ms', sa.Integer(), nullable=True),
        sa.Column('memory_limit_mb', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_assessment_questions_id'), 'assessment_questions', ['id'], unique=False)
    op.create_index(
        op.f('ix_assessment_questions_assessment_id'),
        'assessment_questions',
        ['assessment_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_assessment_questions_question_type'),
        'assessment_questions',
        ['question_type'],
        unique=False,
    )

    op.create_table(
        'assessment_attempts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            sa.Enum(
                'in_progress',
                'submitted',
                'evaluated',
                'partially_evaluated',
                name='attemptstatus',
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('mcq_score', sa.Float(), nullable=True),
        sa.Column('coding_score', sa.Float(), nullable=True),
        sa.Column('earned_points', sa.Float(), nullable=True),
        sa.Column('total_points', sa.Float(), nullable=True),
        sa.Column('result_details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'assessment_id',
            'candidate_id',
            name='uq_assessment_candidate_attempt',
        ),
    )
    op.create_index(op.f('ix_assessment_attempts_id'), 'assessment_attempts', ['id'], unique=False)
    op.create_index(
        op.f('ix_assessment_attempts_assessment_id'),
        'assessment_attempts',
        ['assessment_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_assessment_attempts_candidate_id'),
        'assessment_attempts',
        ['candidate_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_assessment_attempts_status'),
        'assessment_attempts',
        ['status'],
        unique=False,
    )

    op.create_table(
        'assessment_answers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('attempt_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('selected_option', sa.String(length=255), nullable=True),
        sa.Column('answer_text', sa.Text(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('points_awarded', sa.Float(), nullable=False),
        sa.Column('evaluation_details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['attempt_id'], ['assessment_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['assessment_questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('attempt_id', 'question_id', name='uq_attempt_question_answer'),
    )
    op.create_index(op.f('ix_assessment_answers_id'), 'assessment_answers', ['id'], unique=False)
    op.create_index(
        op.f('ix_assessment_answers_attempt_id'),
        'assessment_answers',
        ['attempt_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_assessment_answers_question_id'),
        'assessment_answers',
        ['question_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_assessment_answers_question_id'), table_name='assessment_answers')
    op.drop_index(op.f('ix_assessment_answers_attempt_id'), table_name='assessment_answers')
    op.drop_index(op.f('ix_assessment_answers_id'), table_name='assessment_answers')
    op.drop_table('assessment_answers')

    op.drop_index(op.f('ix_assessment_attempts_status'), table_name='assessment_attempts')
    op.drop_index(op.f('ix_assessment_attempts_candidate_id'), table_name='assessment_attempts')
    op.drop_index(op.f('ix_assessment_attempts_assessment_id'), table_name='assessment_attempts')
    op.drop_index(op.f('ix_assessment_attempts_id'), table_name='assessment_attempts')
    op.drop_table('assessment_attempts')

    op.drop_index(op.f('ix_assessment_questions_question_type'), table_name='assessment_questions')
    op.drop_index(op.f('ix_assessment_questions_assessment_id'), table_name='assessment_questions')
    op.drop_index(op.f('ix_assessment_questions_id'), table_name='assessment_questions')
    op.drop_table('assessment_questions')

    op.drop_index(op.f('ix_assessments_status'), table_name='assessments')
    op.drop_index(op.f('ix_assessments_created_by_id'), table_name='assessments')
    op.drop_index(op.f('ix_assessments_job_id'), table_name='assessments')
    op.drop_index(op.f('ix_assessments_id'), table_name='assessments')
    op.drop_table('assessments')
