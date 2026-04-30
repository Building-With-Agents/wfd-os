"""Tests for the Contracts inventory feature.

Exercises:
  - Bootstrap loader against the sample workbook (loader.py)
  - Importer end-to-end with audit_log discipline (importer.py)
  - Amendment 1 reconciliation drift detection (reconciliation.py)
  - API list/detail/create/update/reconciliation routes (routes/contracts.py)
  - The procurement_method field flows correctly through every layer

Spec: agents/grant-compliance/docs/contracts_inventory_spec.md
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from grant_compliance.contracts_bootstrap.importer import (
    ImporterError,
    import_bundle,
)
from grant_compliance.contracts_bootstrap.loader import load_workbook_bundle
from grant_compliance.contracts_bootstrap.reconciliation import (
    CFA_CONTRACTORS_LINE_CENTS,
    GJC_CONTRACTORS_LINE_CENTS,
    compute_reconciliation,
)
from grant_compliance.db.models import (
    AuditLog,
    Base,
    Contract,
    ContractAmendment,
    ContractStatus,
    ContractTerminationDetail,
    ContractType,
    Funder,
    FunderType,
    Grant,
    PaymentBasis,
    ProcurementMethod,
)
from grant_compliance.db.session import get_db
from grant_compliance.main import app


SAMPLE_WORKBOOK = (
    Path(__file__).parent.parent
    / "data"
    / "contracts_bootstrap"
    / "K8341_Contracts_sample.xlsx"
)


@pytest.fixture
def grant_id(db) -> str:
    """Create a Funder + Grant fixture, return the grant_id."""
    funder = Funder(
        name="ESD",
        funder_type=FunderType.federal,
        federal_pass_through=True,
    )
    db.add(funder)
    db.flush()
    grant = Grant(
        funder_id=funder.id,
        name="K8341",
        award_number="K8341",
        period_start=date(2024, 1, 1),
        period_end=date(2026, 9, 30),
        total_award_cents=400_000_000,
    )
    db.add(grant)
    db.flush()
    db.commit()
    return grant.id


# ---------- loader ----------


def test_loader_reads_sample_workbook():
    bundle = load_workbook_bundle(SAMPLE_WORKBOOK)
    assert len(bundle.contracts) == 3
    assert len(bundle.amendments) == 1
    assert len(bundle.terminations) == 1


def test_loader_validates_cross_references():
    bundle = load_workbook_bundle(SAMPLE_WORKBOOK)
    # All amendments and terminations reference real contracts
    assert bundle.validate_cross_references() == []


def test_loader_dollars_to_cents_conversion():
    bundle = load_workbook_bundle(SAMPLE_WORKBOOK)
    # Ada: $500,000.00 → 50_000_000 cents
    ada = next(c for c in bundle.contracts if c.record_key == "ada")
    assert ada.original_contract_value_cents == 50_000_000
    assert ada.current_contract_value_cents == 50_000_000
    # AI Engage: original $300K, current $375K (after amendment)
    aie = next(c for c in bundle.contracts if c.record_key == "ai_engage")
    assert aie.original_contract_value_cents == 30_000_000
    assert aie.current_contract_value_cents == 37_500_000


def test_loader_procurement_method_parsed():
    bundle = load_workbook_bundle(SAMPLE_WORKBOOK)
    by_key = {c.record_key: c.procurement_method for c in bundle.contracts}
    assert by_key["ada"] == ProcurementMethod.competitive_proposals
    assert by_key["wabs"] == ProcurementMethod.sole_source
    assert by_key["ai_engage"] == ProcurementMethod.competitive_rfp


def test_loader_pipe_delimited_qb_names():
    bundle = load_workbook_bundle(SAMPLE_WORKBOOK)
    aie = next(c for c in bundle.contracts if c.record_key == "ai_engage")
    assert aie.vendor_qb_names == [
        "AI Engage",
        "AIE",
        "Jason Mangold",
        "AI Engage Group LLC",
    ]


# ---------- importer ----------


def test_importer_persists_contracts_amendments_terminations(db, grant_id):
    bundle = load_workbook_bundle(SAMPLE_WORKBOOK)
    result = import_bundle(
        db,
        bundle=bundle,
        grant_id=grant_id,
        actor="ritu@computingforall.org",
        source_path=str(SAMPLE_WORKBOOK),
    )
    db.commit()

    assert result.contracts_created == 3
    assert result.amendments_created == 1
    assert result.terminations_created == 1

    contracts = list(db.execute(select(Contract)).scalars())
    assert {c.vendor_name_display for c in contracts} == {
        "Ada Developers Academy",
        "WABS",
        "AI Engage",
    }
    amendments = list(db.execute(select(ContractAmendment)).scalars())
    assert len(amendments) == 1
    assert amendments[0].previous_value_cents == 30_000_000
    assert amendments[0].new_value_cents == 37_500_000

    terms = list(db.execute(select(ContractTerminationDetail)).scalars())
    assert len(terms) == 1
    assert terms[0].terminated_by.value == "funder"


def test_importer_writes_audit_log_per_row(db, grant_id):
    bundle = load_workbook_bundle(SAMPLE_WORKBOOK)
    import_bundle(
        db,
        bundle=bundle,
        grant_id=grant_id,
        actor="ritu@computingforall.org",
        source_path=str(SAMPLE_WORKBOOK),
    )
    db.commit()

    audits = list(
        db.execute(select(AuditLog).where(AuditLog.action.like("contract%"))).scalars()
    )
    actions = [a.action for a in audits]
    # 3 contracts + 1 amendment + 1 termination = 5 audit entries
    assert actions.count("contract.create.bootstrap") == 3
    assert actions.count("contract_amendment.create.bootstrap") == 1
    assert actions.count("contract_termination.create.bootstrap") == 1
    # Provenance: source_path captured on every create
    for a in audits:
        if a.action.endswith(".bootstrap"):
            assert a.inputs.get("source_path") == str(SAMPLE_WORKBOOK)
            assert a.actor == "ritu@computingforall.org"
            assert a.actor_kind == "human"


def test_importer_rejects_unknown_grant(db):
    bundle = load_workbook_bundle(SAMPLE_WORKBOOK)
    with pytest.raises(ImporterError, match="Grant not found"):
        import_bundle(
            db,
            bundle=bundle,
            grant_id="00000000-0000-0000-0000-000000000000",
            actor="ritu@computingforall.org",
            source_path=str(SAMPLE_WORKBOOK),
        )


# ---------- reconciliation ----------


def test_reconciliation_detects_drift_against_amendment_1(db, grant_id):
    bundle = load_workbook_bundle(SAMPLE_WORKBOOK)
    import_bundle(
        db,
        bundle=bundle,
        grant_id=grant_id,
        actor="ritu@computingforall.org",
        source_path=str(SAMPLE_WORKBOOK),
    )
    db.commit()

    report = compute_reconciliation(db, grant_id=grant_id)
    # Sample data is not designed to reconcile — drift is expected.
    assert report.overall_reconciles is False
    assert len(report.lines) == 2
    assert len(report.warnings) >= 1

    gjc = next(line for line in report.lines if "GJC" in line.budget_line)
    cfa = next(line for line in report.lines if "CFA" in line.budget_line)
    # GJC line covers training_provider + strategic_partner_subrecipient.
    # Sample: Ada $500K + WABS $850K = $1.35M actual.
    assert gjc.actual_cents == 50_000_000 + 85_000_000
    assert gjc.expected_cents == GJC_CONTRACTORS_LINE_CENTS
    assert gjc.contract_count == 2
    # CFA contractors: AI Engage $375K alone.
    assert cfa.actual_cents == 37_500_000
    assert cfa.expected_cents == CFA_CONTRACTORS_LINE_CENTS
    assert cfa.contract_count == 1


def test_reconciliation_passes_when_sums_match(db, grant_id):
    """Construct contracts whose sums exactly match Amendment 1.
    Verifies the reconciles=True path."""
    db.add(
        Contract(
            grant_id=grant_id,
            vendor_name_display="GJC Total Stand-In",
            vendor_legal_entity="GJC Total Stand-In",
            contract_type=ContractType.training_provider,
            original_contract_value_cents=GJC_CONTRACTORS_LINE_CENTS,
            current_contract_value_cents=GJC_CONTRACTORS_LINE_CENTS,
            status=ContractStatus.active,
            payment_basis=PaymentBasis.other,
        )
    )
    db.add(
        Contract(
            grant_id=grant_id,
            vendor_name_display="CFA Total Stand-In",
            vendor_legal_entity="CFA Total Stand-In",
            contract_type=ContractType.cfa_contractor,
            original_contract_value_cents=CFA_CONTRACTORS_LINE_CENTS,
            current_contract_value_cents=CFA_CONTRACTORS_LINE_CENTS,
            status=ContractStatus.active,
            payment_basis=PaymentBasis.other,
        )
    )
    db.commit()
    report = compute_reconciliation(db, grant_id=grant_id)
    assert report.overall_reconciles is True
    assert report.warnings == []


# ---------- API routes ----------


@pytest.fixture
def api_db_pair():
    """Engine + session factory using StaticPool so the FastAPI TestClient
    (which runs handlers in a separate thread, with a separate connection)
    sees the same in-memory schema as the test code.

    The base conftest `db` fixture uses a default pool with one connection
    per session, which works for direct test code but not for the
    TestClient-spawned thread. StaticPool forces a single shared connection.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _attach(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("ATTACH DATABASE ':memory:' AS grant_compliance")
        cursor.close()

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session, SessionLocal
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def api_grant_id(api_db_pair) -> str:
    """Grant fixture for API tests — uses the StaticPool engine."""
    session, _ = api_db_pair
    funder = Funder(
        name="ESD",
        funder_type=FunderType.federal,
        federal_pass_through=True,
    )
    session.add(funder)
    session.flush()
    grant = Grant(
        funder_id=funder.id,
        name="K8341",
        award_number="K8341",
        period_start=date(2024, 1, 1),
        period_end=date(2026, 9, 30),
        total_award_cents=400_000_000,
    )
    session.add(grant)
    session.flush()
    session.commit()
    return grant.id


@pytest.fixture
def client(api_db_pair):
    """FastAPI TestClient bound to the same engine as api_db_pair.

    Route handlers use a fresh Session-per-request from the same engine,
    so cross-thread access works because StaticPool guarantees a single
    underlying SQLite connection.
    """
    _, SessionLocal = api_db_pair

    def _override():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_contracts_endpoint(client, api_db_pair, api_grant_id):
    db, _ = api_db_pair
    bundle = load_workbook_bundle(SAMPLE_WORKBOOK)
    import_bundle(
        db,
        bundle=bundle,
        grant_id=api_grant_id,
        actor="ritu@computingforall.org",
        source_path=str(SAMPLE_WORKBOOK),
    )
    db.commit()

    r = client.get("/contracts", params={"grant_id": api_grant_id})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 3
    # Sorted by current_contract_value_cents desc — WABS $850K is first.
    assert rows[0]["vendor_name_display"] == "WABS"
    # Computed honesty fields surface
    assert "is_above_simplified_acquisition_threshold" in rows[0]
    assert "requires_cost_or_price_analysis" in rows[0]
    assert "procurement_method" in rows[0]


def test_list_contracts_filter_by_procurement_method(
    client, api_db_pair, api_grant_id
):
    db, _ = api_db_pair
    bundle = load_workbook_bundle(SAMPLE_WORKBOOK)
    import_bundle(
        db,
        bundle=bundle,
        grant_id=api_grant_id,
        actor="ritu@computingforall.org",
        source_path=str(SAMPLE_WORKBOOK),
    )
    db.commit()

    r = client.get(
        "/contracts",
        params={"grant_id": api_grant_id, "procurement_method": "sole_source"},
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["vendor_name_display"] == "WABS"
    assert rows[0]["procurement_method"] == "sole_source"


def test_get_contract_detail_includes_amendments_and_termination(
    client, api_db_pair, api_grant_id
):
    db, _ = api_db_pair
    bundle = load_workbook_bundle(SAMPLE_WORKBOOK)
    import_bundle(
        db,
        bundle=bundle,
        grant_id=api_grant_id,
        actor="ritu@computingforall.org",
        source_path=str(SAMPLE_WORKBOOK),
    )
    db.commit()

    aie = next(
        c
        for c in db.execute(select(Contract)).scalars()
        if c.vendor_name_display == "AI Engage"
    )
    r = client.get(f"/contracts/{aie.id}")
    assert r.status_code == 200
    data = r.json()
    assert len(data["amendments"]) == 1
    assert data["amendments"][0]["amendment_number"] == 1
    assert data["amendments"][0]["new_value_cents"] == 37_500_000
    # AI Engage isn't terminated → no termination detail
    assert data["termination_detail"] is None

    wabs = next(
        c
        for c in db.execute(select(Contract)).scalars()
        if c.vendor_name_display == "WABS"
    )
    r2 = client.get(f"/contracts/{wabs.id}")
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["termination_detail"] is not None
    assert data2["termination_detail"]["terminated_by"] == "funder"


def test_create_contract_via_api_writes_audit_log(
    client, api_db_pair, api_grant_id
):
    db, _ = api_db_pair
    body = {
        "vendor_name_display": "Code Day",
        "vendor_legal_entity": "Code Day Inc.",
        "vendor_qb_names": ["Code Day", "CodeDay"],
        "contract_type": "training_provider",
        "compliance_classification": "contractor_200_331b",
        "procurement_method": "competitive_rfp",
        "original_contract_value_cents": 12_500_000,
        "current_contract_value_cents": 12_500_000,
        "status": "active",
        "payment_basis": "per_placement",
        "actor": "ritu@computingforall.org",
        "grant_id": api_grant_id,
    }
    r = client.post("/contracts", json=body)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["vendor_name_display"] == "Code Day"
    assert data["procurement_method"] == "competitive_rfp"
    # $125K is above MPT but below SAT
    assert data["is_above_micro_purchase_threshold"] is True
    assert data["is_above_simplified_acquisition_threshold"] is False
    assert data["requires_cost_or_price_analysis"] is False
    # Audit log entry created
    audits = list(
        db.execute(
            select(AuditLog).where(AuditLog.action == "contract.create.api")
        ).scalars()
    )
    assert len(audits) == 1


def test_update_contract_via_api_records_before_after(
    client, api_db_pair, api_grant_id
):
    db, _ = api_db_pair
    body = {
        "vendor_name_display": "Code Day",
        "vendor_legal_entity": "Code Day Inc.",
        "vendor_qb_names": [],
        "contract_type": "training_provider",
        "compliance_classification": "contractor_200_331b",
        "procurement_method": "competitive_rfp",
        "original_contract_value_cents": 12_500_000,
        "current_contract_value_cents": 12_500_000,
        "status": "active",
        "payment_basis": "per_placement",
        "actor": "ritu@computingforall.org",
        "grant_id": api_grant_id,
    }
    r = client.post("/contracts", json=body)
    assert r.status_code == 201
    contract_id = r.json()["id"]

    body["procurement_method"] = "sole_source"
    body["current_contract_value_cents"] = 30_000_000
    r2 = client.put(f"/contracts/{contract_id}", json=body)
    assert r2.status_code == 200
    assert r2.json()["procurement_method"] == "sole_source"
    assert r2.json()["current_contract_value_cents"] == 30_000_000
    # $300K is above SAT now → requires cost/price analysis
    assert r2.json()["is_above_simplified_acquisition_threshold"] is True
    assert r2.json()["requires_cost_or_price_analysis"] is True

    update_audit = (
        db.execute(
            select(AuditLog).where(AuditLog.action == "contract.update.api")
        ).scalars().one()
    )
    assert update_audit.inputs["before"]["procurement_method"] == "competitive_rfp"
    assert update_audit.inputs["before"]["current_contract_value_cents"] == 12_500_000


def test_reconciliation_endpoint(client, api_db_pair, api_grant_id):
    db, _ = api_db_pair
    bundle = load_workbook_bundle(SAMPLE_WORKBOOK)
    import_bundle(
        db,
        bundle=bundle,
        grant_id=api_grant_id,
        actor="ritu@computingforall.org",
        source_path=str(SAMPLE_WORKBOOK),
    )
    db.commit()

    r = client.get("/contracts/reconciliation", params={"grant_id": api_grant_id})
    assert r.status_code == 200
    data = r.json()
    assert data["overall_reconciles"] is False
    assert len(data["lines"]) == 2
    assert len(data["warnings"]) == 2
