from sqlalchemy import Column, String, Float, Integer, Date, DateTime, Boolean, Text, JSON
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class MonthlySnapshot(Base):
    __tablename__ = "monthly_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(7), nullable=False)  # YYYY-MM
    created_at = Column(DateTime, default=datetime.utcnow)

    # Budget remaining per category
    gjc_contractors_budget = Column(Float, default=2315623)
    gjc_contractors_spent = Column(Float, default=0)
    cfa_contractors_budget = Column(Float, default=1020823)
    cfa_contractors_spent = Column(Float, default=0)
    personnel_salaries_budget = Column(Float, default=1097662)
    personnel_salaries_spent = Column(Float, default=0)
    personnel_benefits_budget = Column(Float, default=173170)
    personnel_benefits_spent = Column(Float, default=0)
    other_direct_budget = Column(Float, default=88921)
    other_direct_spent = Column(Float, default=0)
    indirect_costs_budget = Column(Float, default=178799)
    indirect_costs_spent = Column(Float, default=0)

    raw_data = Column(JSON)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(7), nullable=False)
    source = Column(String(50))  # quickbooks, bank, credit_card
    date = Column(Date)
    description = Column(Text)
    vendor = Column(String(255))
    amount = Column(Float)
    budget_category = Column(String(100))
    matched = Column(Boolean, default=False)
    match_source = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class ProviderPayment(Base):
    __tablename__ = "provider_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(7), nullable=False)
    provider = Column(String(255), nullable=False)
    invoice_amount = Column(Float)
    placements_reported = Column(Integer)
    expected_amount = Column(Float)
    rate_per_placement = Column(Float)
    variance = Column(Float)
    flagged = Column(Boolean, default=False)
    flag_reason = Column(Text)
    cumulative_paid = Column(Float, default=0)
    cumulative_placements = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(7), nullable=False)
    anomaly_type = Column(String(100))
    description = Column(Text)
    severity = Column(String(20))  # warning, critical
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class BaselineData(Base):
    __tablename__ = "baseline_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(String(255), nullable=False)
    data_type = Column(String(100), nullable=False)  # provider_reconciliation, contractors, outcomes
    sheet_name = Column(String(255))
    row_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConversationState(Base):
    __tablename__ = "conversation_state"

    conversation_id = Column(String(255), primary_key=True)
    user_id = Column(String(255))
    history = Column(JSON, default=list)
    updated_at = Column(DateTime, default=datetime.utcnow)
