"""Sanity tests — confirm every wfdos_common module imports without error.

These tests pass when the package skeleton (issue #17) is in place, even
before the module implementations land. Each implementation-owning issue
(#18, #20, #21, #22, #23, #24, #26, #28) will add module-specific tests.
"""


def test_package_imports():
    import wfdos_common

    assert wfdos_common.__version__ == "0.0.1"


def test_all_stub_modules_importable():
    import wfdos_common.agent  # noqa: F401
    import wfdos_common.auth  # noqa: F401
    import wfdos_common.config  # noqa: F401
    import wfdos_common.db  # noqa: F401
    import wfdos_common.email  # noqa: F401
    import wfdos_common.graph  # noqa: F401
    import wfdos_common.llm  # noqa: F401
    import wfdos_common.logging  # noqa: F401
    import wfdos_common.models  # noqa: F401
    import wfdos_common.testing  # noqa: F401
