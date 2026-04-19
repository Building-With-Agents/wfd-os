# Deprecated — this file exists only for one-off migration scripts that
# import it by direct file path. All services use:
#
#     from wfdos_common.config import PG_CONFIG
#
# Pre-#27, every service did `sys.path.insert(0, "../scripts")` to find
# this module. #27 eliminated all those sys.path.insert calls by moving
# the `PG_CONFIG` dict into wfdos_common.config. Remaining file-path
# callers in scripts/ keep working because this re-exports the canonical
# dict.
from wfdos_common.config import PG_CONFIG  # noqa: F401
