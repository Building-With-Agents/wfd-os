# PostgreSQL connection config — imported by migration scripts.
#
# Historical note (#19): this file used to hardcode a password literal. It now
# sources values from wfdos_common.config.settings, which reads from .env /
# environment. Scripts that `from pgconfig import PG_CONFIG` continue to work
# unchanged — only the source of the values has moved.
#
# The hardcoded literal was rotated in Azure Postgres as part of #19 rotation.
from wfdos_common.config import settings

PG_CONFIG = {
    "host": settings.pg.host,
    "database": settings.pg.database,
    "user": settings.pg.user,
    "password": settings.pg.password or "",
    "port": settings.pg.port,
}
