"""Create materialized views gsm_count_by_carrier
    and gsm_signal_statistic_by_carrier

Revision ID: ac3945a94529
Revises: 5f118b507d55
Create Date: 2017-04-12 16:07:33.602993

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ac3945a94529'
down_revision = '5f118b507d55'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("""
        CREATE MATERIALIZED VIEW gsm_count_by_carrier AS
        SELECT  carriers.name as carrier_name,
                network_type.type as network_type,
                SUM(gsm_count.quantity) as quantity,
                year,
                month
        FROM gsm_count
        JOIN carriers ON carriers.id=gsm_count.carrier_id
        JOIN network_type ON network_type.id=gsm_count.network_type
        GROUP BY network_type.type, carriers.name, year, month
        WITH DATA
    """)

    op.execute("""
        CREATE MATERIALIZED VIEW gsm_signal_statistic_by_carrier AS
        SELECT carrier_name, perc[1] as p25, perc[2] as p50, perc[3] as p75, year, month
        FROM
           (SELECT carriers.name as carrier_name,
                   percentile_cont(array[0.25, 0.5, 0.75]) WITHIN GROUP (ORDER BY signal) as perc,
                   year,
                   month
           FROM gsm_signal JOIN carriers on gsm_signal.carrier_id=carriers.id
           WHERE signal IS NOT NULL AND signal<80 and quantity>0
           GROUP BY carriers.name, year, month) as query
        WITH DATA
    """)
    pass
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("DROP MATERIALIZED VIEW gsm_signal_statistic_by_carrier")
    op.execute("DROP MATERIALIZED VIEW gsm_count_by_carrier")
    # ### end Alembic commands ###