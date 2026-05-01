"""/transactions — list, classify, and inspect transactions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.agents.classifier import TransactionClassifier
from grant_compliance.api.schemas import AllocationOut, TransactionOut
from grant_compliance.db.models import Transaction
from grant_compliance.db.session import get_db

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[Transaction]:
    stmt = select(Transaction).order_by(Transaction.txn_date.desc()).limit(limit)
    return list(db.execute(stmt).scalars())


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.post("/{transaction_id}/classify", response_model=list[AllocationOut])
def classify_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """Run the Classifier on a single transaction. Returns proposed allocations."""
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    classifier = TransactionClassifier(db)
    allocations = classifier.classify(txn)
    db.commit()
    return allocations


@router.get("/{transaction_id}/allocations", response_model=list[AllocationOut])
def get_allocations(transaction_id: str, db: Session = Depends(get_db)):
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn.allocations
