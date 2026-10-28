"""add_interview_tables

Revision ID: 6f4e2d8c1b3a
Revises: 8b7d4e2f1a90
Create Date: 2026-10-28 12:00:00.000000

Phase 9 stores AI mock interview sessions, sequential questions,
candidate answers with rubric-based evaluations, and final session summaries.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f4e2d8c1b3a'
down_revision: Union[str, Sequence[str], None] = '8b7d4e2f1a90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'interview_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('resume_id', sa.Integer(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('in_progress', 'completed', name='interviewstatus', native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('difficulty', sa.String(length=20), nullable=False, server_default='mixed'),
        sa.Column('focus_areas', sa.JSON(), nullable=False),
        sa.Column('target_question_count', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_follow_ups', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('generation_model', sa.String(length=100), nullable=True),
        sa.Column('generation_prompt_version', sa.String(length=50), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_interview_sessions_id'), 'interview_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_interview_sessions_job_id'), 'interview_sessions', ['job_id'], unique=False)
    op.create_index(op.f('ix_interview_sessions_candidate_id'), 'interview_sessions', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_interview_sessions_resume_id'), 'interview_sessions', ['resume_id'], unique=False)
    op.create_index(op.f('ix_interview_sessions_status'), 'interview_sessions', ['status'], unique=False)

    op.create_table(
        'interview_questions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('parent_question_id', sa.Integer(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('is_follow_up', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('skill_tag', sa.String(length=120), nullable=True),
        sa.Column('difficulty', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_question_id'], ['interview_questions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'order_index', name='uq_interview_question_order'),
    )
    op.create_index(op.f('ix_interview_questions_id'), 'interview_questions', ['id'], unique=False)
    op.create_index(op.f('ix_interview_questions_session_id'), 'interview_questions', ['session_id'], unique=False)
    op.create_index(op.f('ix_interview_questions_parent_question_id'), 'interview_questions', ['parent_question_id'], unique=False)

    op.create_table(
        'interview_answers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('technical_correctness', sa.Float(), nullable=False),
        sa.Column('relevance', sa.Float(), nullable=False),
        sa.Column('clarity', sa.Float(), nullable=False),
        sa.Column('reasoning', sa.Float(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=False),
        sa.Column('evaluation_details', sa.JSON(), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['interview_questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('question_id', name='uq_interview_answer_question'),
    )
    op.create_index(op.f('ix_interview_answers_id'), 'interview_answers', ['id'], unique=False)
    op.create_index(op.f('ix_interview_answers_session_id'), 'interview_answers', ['session_id'], unique=False)
    op.create_index(op.f('ix_interview_answers_question_id'), 'interview_answers', ['question_id'], unique=False)

    op.create_table(
        'interview_evaluations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('technical_correctness', sa.Float(), nullable=False),
        sa.Column('relevance', sa.Float(), nullable=False),
        sa.Column('clarity', sa.Float(), nullable=False),
        sa.Column('reasoning', sa.Float(), nullable=False),
        sa.Column('overall_summary', sa.Text(), nullable=False),
        sa.Column('strengths', sa.JSON(), nullable=False),
        sa.Column('weaknesses', sa.JSON(), nullable=False),
        sa.Column('improvement_suggestions', sa.JSON(), nullable=False),
        sa.Column('recommended_topics', sa.JSON(), nullable=False),
        sa.Column('disclaimer', sa.Text(), nullable=False),
        sa.Column('rubric_version', sa.String(length=50), nullable=False),
        sa.Column('generation_model', sa.String(length=100), nullable=True),
        sa.Column('generation_status', sa.String(length=20), server_default='llm', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', name='uq_interview_evaluation_session'),
    )
    op.create_index(op.f('ix_interview_evaluations_id'), 'interview_evaluations', ['id'], unique=False)
    op.create_index(op.f('ix_interview_evaluations_session_id'), 'interview_evaluations', ['session_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_interview_evaluations_session_id'), table_name='interview_evaluations')
    op.drop_index(op.f('ix_interview_evaluations_id'), table_name='interview_evaluations')
    op.drop_table('interview_evaluations')

    op.drop_index(op.f('ix_interview_answers_question_id'), table_name='interview_answers')
    op.drop_index(op.f('ix_interview_answers_session_id'), table_name='interview_answers')
    op.drop_index(op.f('ix_interview_answers_id'), table_name='interview_answers')
    op.drop_table('interview_answers')

    op.drop_index(op.f('ix_interview_questions_parent_question_id'), table_name='interview_questions')
    op.drop_index(op.f('ix_interview_questions_session_id'), table_name='interview_questions')
    op.drop_index(op.f('ix_interview_questions_id'), table_name='interview_questions')
    op.drop_table('interview_questions')

    op.drop_index(op.f('ix_interview_sessions_status'), table_name='interview_sessions')
    op.drop_index(op.f('ix_interview_sessions_resume_id'), table_name='interview_sessions')
    op.drop_index(op.f('ix_interview_sessions_candidate_id'), table_name='interview_sessions')
    op.drop_index(op.f('ix_interview_sessions_job_id'), table_name='interview_sessions')
    op.drop_index(op.f('ix_interview_sessions_id'), table_name='interview_sessions')
    op.drop_table('interview_sessions')
