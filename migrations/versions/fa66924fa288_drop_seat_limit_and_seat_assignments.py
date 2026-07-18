"""drop seat limit and seat assignments

An organization license entitles every active member of the organization
to the product/edition for its validity window -- there is no per-user
seat cap or seat-claiming step (device_limit_per_user, unaffected by this
migration, still limits devices per individual user).

Revision ID: fa66924fa288
Revises: 26ce5ddc18e1
Create Date: 2026-07-18 14:43:45.136378

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fa66924fa288'
down_revision: Union[str, None] = '26ce5ddc18e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(
        'ix_seat_assignments_active_unique',
        table_name='license_seat_assignments',
        postgresql_where=sa.text("status = 'active'"),
    )
    op.drop_index(
        op.f('ix_license_seat_assignments_user_id'), table_name='license_seat_assignments'
    )
    op.drop_index(
        op.f('ix_license_seat_assignments_organization_license_id'),
        table_name='license_seat_assignments',
    )
    op.drop_table('license_seat_assignments')
    op.drop_constraint(
        'ck_org_license_seat_limit_nonneg', 'organization_licenses', type_='check'
    )
    op.drop_column('organization_licenses', 'seat_limit')
    postgresql.ENUM(name='seat_assignment_status').drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    postgresql.ENUM('active', 'removed', name='seat_assignment_status').create(
        op.get_bind(), checkfirst=True
    )
    op.add_column(
        'organization_licenses',
        sa.Column('seat_limit', sa.Integer(), nullable=False, server_default='0'),
    )
    op.alter_column('organization_licenses', 'seat_limit', server_default=None)
    op.create_check_constraint(
        'ck_org_license_seat_limit_nonneg', 'organization_licenses', 'seat_limit >= 0'
    )
    op.create_table(
        'license_seat_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_license_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'status',
            sa.Enum('active', 'removed', name='seat_assignment_status'),
            nullable=False,
        ),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assigned_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_license_id'], ['organization_licenses.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['assigned_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_license_seat_assignments_organization_license_id'),
        'license_seat_assignments',
        ['organization_license_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_license_seat_assignments_user_id'),
        'license_seat_assignments',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        'ix_seat_assignments_active_unique',
        'license_seat_assignments',
        ['organization_license_id', 'user_id'],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
