"""added region/gau/bezirk

Revision ID: d586336b456e
Revises: 686b76b51444
Create Date: 2022-06-07 10:42:53.660713

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd586336b456e'
down_revision = '686b76b51444'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('group', sa.Column('region_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'group', 'region', ['region_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'group', type_='foreignkey')
    op.drop_column('group', 'region_id')
    # ### end Alembic commands ###