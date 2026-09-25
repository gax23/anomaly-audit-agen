"""initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2023-10-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Crear tablas
    op.create_table(
        'transactions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('amount', sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType(), nullable=True),
        sa.Column('account_debit', sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType(), nullable=True),
        sa.Column('account_credit', sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType(), nullable=True),
        sa.Column('vendor_id', sqlalchemy_utils.types.encrypted.encrypted_type.EncryptedType(), nullable=True),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('employee_id', sa.String(length=100), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('source_system', sa.String(length=50), nullable=False),
        sa.Column('log_amount', sa.Float(), nullable=True),
        sa.Column('hour_of_day', sa.Integer(), nullable=True),
        sa.Column('day_of_week', sa.Integer(), nullable=True),
        sa.Column('is_weekend', sa.Boolean(), nullable=True),
        sa.Column('vendor_risk_score', sa.Float(), nullable=True),
        sa.Column('amount_deviation', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('is_processed', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_date'), 'transactions', ['date'], unique=False)
    op.create_index('idx_transactions_date_source', 'transactions', ['date', 'source_system'], unique=False)

    op.create_table(
        'anomalies',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('transaction_id', sa.String(length=36), nullable=False),
        sa.Column('detected_at', sa.DateTime(), nullable=True),
        sa.Column('anomaly_score', sa.Float(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('rules_triggered', sa.JSON(), nullable=True),
        sa.Column('ml_score', sa.Float(), nullable=True),
        sa.Column('shap_values', sa.JSON(), nullable=True),
        sa.Column('narrative', sa.Text(), nullable=True),
        sa.Column('shap_plot_path', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=True),
        sa.Column('reviewer_id', sa.String(length=100), nullable=True),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_anomalies_detected_at'), 'anomalies', ['detected_at'], unique=False)
    op.create_index(op.f('ix_anomalies_transaction_id'), 'anomalies', ['transaction_id'], unique=False)

    op.create_table(
        'model_metrics',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('trained_at', sa.DateTime(), nullable=True),
        sa.Column('auc_roc', sa.Float(), nullable=True),
        sa.Column('precision', sa.Float(), nullable=True),
        sa.Column('recall', sa.Float(), nullable=True),
        sa.Column('f1_score', sa.Float(), nullable=True),
        sa.Column('train_samples', sa.Integer(), nullable=True),
        sa.Column('train_time_seconds', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('artifact_path', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'alerts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Crear hypertable en TimescaleDB
    op.execute("SELECT create_hypertable('transactions', 'date', if_not_exists => TRUE);")

def downgrade() -> None:
    op.drop_index(op.f('ix_anomalies_transaction_id'), table_name='anomalies')
    op.drop_index(op.f('ix_anomalies_detected_at'), table_name='anomalies')
    op.drop_table('anomalies')
    op.drop_index('idx_transactions_date_source', table_name='transactions')
    op.drop_index(op.f('ix_transactions_date'), table_name='transactions')
    op.drop_table('transactions')
    op.drop_table('model_metrics')
    op.drop_table('alerts')
