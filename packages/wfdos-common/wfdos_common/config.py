"""wfdos_common.config — centralized Pydantic Settings for all services.

STATUS: STUB — implementation lands in Building-With-Agents/wfd-os#18.

Target scope (from #18):
- Pydantic BaseSettings grouping all ~37 vars from .env.example by domain
  (pg, azure, graph, llm, blob, apollo, dynamics, teams, org).
- Fail-fast on missing required vars at startup.
- Pluggable secret backends (wfdos_common.config.secrets): EnvBackend default;
  KeyVault / 1Password / Doppler / Infisical / HashiVault as opt-in extras.
- CFA-identity audit: no hardcoded computingforall.org or CFA tenant GUIDs.

Per the migration invariant (comment on #18), services currently continue to
use os.getenv() directly; this module will coexist with those reads until each
service is flipped over one at a time.
"""
