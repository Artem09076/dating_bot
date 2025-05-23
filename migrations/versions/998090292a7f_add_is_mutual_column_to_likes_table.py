"""Add is_mutual column to likes table

Revision ID: 998090292a7f
Revises: 1c821254e678
Create Date: 2025-04-18 10:35:30.037252

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "998090292a7f"
down_revision: Union[str, None] = "1c821254e678"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        "fk_behavior_ratings_user_id_user", "behavior_ratings", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_behavior_ratings_user_id_user"),
        "behavior_ratings",
        "user",
        ["user_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
    )
    op.drop_constraint(
        "fk_combined_ratings_user_id_user", "combined_ratings", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_combined_ratings_user_id_user"),
        "combined_ratings",
        "user",
        ["user_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
    )
    op.drop_constraint(
        "fk_conversation_user1_id_user", "conversation", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_conversation_user2_id_user", "conversation", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_conversation_user2_id_user"),
        "conversation",
        "user",
        ["user2_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
    )
    op.create_foreign_key(
        op.f("fk_conversation_user1_id_user"),
        "conversation",
        "user",
        ["user1_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
    )
    op.add_column("likes", sa.Column("is_mutual", sa.Boolean(), nullable=True))
    op.drop_constraint("fk_likes_to_user_id_user", "likes", type_="foreignkey")
    op.drop_constraint("fk_likes_from_user_id_user", "likes", type_="foreignkey")
    op.create_foreign_key(
        op.f("fk_likes_to_user_id_user"),
        "likes",
        "user",
        ["to_user_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
    )
    op.create_foreign_key(
        op.f("fk_likes_from_user_id_user"),
        "likes",
        "user",
        ["from_user_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
    )
    op.drop_constraint(
        "fk_primary_ratings_user_id_user", "primary_ratings", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_primary_ratings_user_id_user"),
        "primary_ratings",
        "user",
        ["user_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
    )
    op.drop_constraint("fk_user_invited_by_user_id_user", "user", type_="foreignkey")
    op.create_foreign_key(
        op.f("fk_user_invited_by_user_id_user"),
        "user",
        "user",
        ["invited_by_user_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        op.f("fk_user_invited_by_user_id_user"),
        "user",
        schema="public",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_user_invited_by_user_id_user",
        "user",
        "user",
        ["invited_by_user_id"],
        ["id"],
    )
    op.drop_constraint(
        op.f("fk_primary_ratings_user_id_user"),
        "primary_ratings",
        schema="public",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_primary_ratings_user_id_user",
        "primary_ratings",
        "user",
        ["user_id"],
        ["id"],
    )
    op.drop_constraint(
        op.f("fk_likes_from_user_id_user"), "likes", schema="public", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("fk_likes_to_user_id_user"), "likes", schema="public", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_likes_from_user_id_user", "likes", "user", ["from_user_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_likes_to_user_id_user", "likes", "user", ["to_user_id"], ["id"]
    )
    op.drop_column("likes", "is_mutual")
    op.drop_constraint(
        op.f("fk_conversation_user1_id_user"),
        "conversation",
        schema="public",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_conversation_user2_id_user"),
        "conversation",
        schema="public",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_conversation_user2_id_user", "conversation", "user", ["user2_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_conversation_user1_id_user", "conversation", "user", ["user1_id"], ["id"]
    )
    op.drop_constraint(
        op.f("fk_combined_ratings_user_id_user"),
        "combined_ratings",
        schema="public",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_combined_ratings_user_id_user",
        "combined_ratings",
        "user",
        ["user_id"],
        ["id"],
    )
    op.drop_constraint(
        op.f("fk_behavior_ratings_user_id_user"),
        "behavior_ratings",
        schema="public",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_behavior_ratings_user_id_user",
        "behavior_ratings",
        "user",
        ["user_id"],
        ["id"],
    )
    # ### end Alembic commands ###
