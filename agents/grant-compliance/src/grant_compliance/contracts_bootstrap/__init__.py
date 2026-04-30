"""Contracts inventory bootstrap module.

One-time Excel-driven import path for populating the Contract,
ContractAmendment, and ContractTerminationDetail tables. Spec:
agents/grant-compliance/docs/contracts_inventory_spec.md.

Modules:
  - schemas.py        Pydantic record shapes loaded from Excel
  - loader.py         Excel parser (openpyxl), validates schema, returns records
  - importer.py       DB persistence with audit_log discipline (the service
                      layer per CLAUDE.md — every Contract mutation logged)
  - reconciliation.py Amendment 1 reconciliation against per-contract-type sums
  - __main__.py       CLI entrypoint:
                          python -m grant_compliance.contracts_bootstrap import \\
                              --file <path> --grant-id <uuid> --actor <email>

The bootstrap is meant to run once per grant for initial population.
Subsequent updates happen through the API (`POST /contracts`,
`PUT /contracts/{id}`) — or, in v1.1, through cockpit UI.
"""
