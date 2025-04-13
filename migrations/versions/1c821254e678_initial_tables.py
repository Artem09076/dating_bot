"""Initial tables

Revision ID: 1c821254e678
Revises: 
Create Date: 2025-04-12 14:31:25.900040

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1c821254e678"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column(
            "gender",
            sa.Enum("male", "female", "other", name="genderenum"),
            nullable=False,
        ),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("interests", sa.String(), nullable=True),
        sa.Column("profile_filled", sa.Boolean(), nullable=False),
        sa.Column("photo", sa.String(length=255), nullable=False),
        sa.Column("preferred_age_min", sa.Integer(), nullable=False),
        sa.Column("preferred_age_max", sa.Integer(), nullable=False),
        sa.Column(
            "preferred_gender",
            sa.Enum("male", "female", "other", name="genderenum"),
            nullable=False,
        ),
        sa.Column("preferred_city", sa.String(), nullable=True),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"],
            ["public.user.id"],
            name=op.f("fk_user_invited_by_user_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user")),
        schema="public",
    )
    op.create_table(
        "behavior_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("likes_received", sa.Integer(), nullable=False),
        sa.Column("likes_skipped_ratio", sa.Float(), nullable=False),
        sa.Column("mutual_likes", sa.Integer(), nullable=False),
        sa.Column("post_match_conversations", sa.Integer(), nullable=False),
        sa.Column("active_hours_score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["public.user.id"],
            name=op.f("fk_behavior_ratings_user_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_behavior_ratings")),
        sa.UniqueConstraint("user_id", name=op.f("uq_behavior_ratings_user_id")),
        schema="public",
    )
    op.create_table(
        "combined_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["public.user.id"],
            name=op.f("fk_combined_ratings_user_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_combined_ratings")),
        sa.UniqueConstraint("user_id", name=op.f("uq_combined_ratings_user_id")),
        schema="public",
    )
    op.create_table(
        "conversation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user1_id", sa.Integer(), nullable=False),
        sa.Column("user2_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user1_id"], ["public.user.id"], name=op.f("fk_conversation_user1_id_user")
        ),
        sa.ForeignKeyConstraint(
            ["user2_id"], ["public.user.id"], name=op.f("fk_conversation_user2_id_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversation")),
        schema="public",
    )
    op.create_table(
        "likes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("from_user_id", sa.Integer(), nullable=False),
        sa.Column("to_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["from_user_id"],
            ["public.user.id"],
            name=op.f("fk_likes_from_user_id_user"),
        ),
        sa.ForeignKeyConstraint(
            ["to_user_id"], ["public.user.id"], name=op.f("fk_likes_to_user_id_user")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_likes")),
        schema="public",
    )
    op.create_table(
        "primary_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("completeness_score", sa.Float(), nullable=False),
        sa.Column("photo_score", sa.Float(), nullable=False),
        sa.Column("preference_match_score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["public.user.id"],
            name=op.f("fk_primary_ratings_user_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_primary_ratings")),
        sa.UniqueConstraint("user_id", name=op.f("uq_primary_ratings_user_id")),
        schema="public",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("primary_ratings", schema="public")
    op.drop_table("likes", schema="public")
    op.drop_table("conversation", schema="public")
    op.drop_table("combined_ratings", schema="public")
    op.drop_table("behavior_ratings", schema="public")
    op.drop_table("user", schema="public")
    # ### end Alembic commands ###
