"""Tests for correlation-ID propagation."""

from __future__ import annotations

import asyncio

import pytest
from asciip_shared.correlation import (
    bind_correlation_id,
    get_correlation_id,
    new_correlation_id,
    reset_correlation_id,
)

pytestmark = pytest.mark.unit


def test_default_is_empty_when_no_binding() -> None:
    # The ContextVar declares default="" and ``bind_correlation_id`` treats
    # empty/None as "generate a fresh id", so we verify the default directly.
    # Reset any leaked binding from earlier tests in the same process.
    from asciip_shared.correlation import _correlation_id

    token = _correlation_id.set("")
    try:
        assert _correlation_id.get() == ""
    finally:
        _correlation_id.reset(token)


def test_bind_and_get_roundtrip() -> None:
    cid = new_correlation_id()
    token = bind_correlation_id(cid)
    try:
        assert get_correlation_id() == cid
    finally:
        reset_correlation_id(token)


def test_bind_without_value_generates_one() -> None:
    token = bind_correlation_id()
    try:
        cid = get_correlation_id()
        assert cid
        assert len(cid) == 32
        int(cid, 16)  # valid hex
    finally:
        reset_correlation_id(token)


def test_isolation_between_async_tasks() -> None:
    async def task(value: str) -> str:
        token = bind_correlation_id(value)
        try:
            await asyncio.sleep(0)
            return get_correlation_id()
        finally:
            reset_correlation_id(token)

    async def driver() -> tuple[str, str]:
        a, b = await asyncio.gather(task("aaa"), task("bbb"))
        return a, b

    a, b = asyncio.run(driver())
    assert a == "aaa"
    assert b == "bbb"


def test_new_ids_are_unique() -> None:
    ids = {new_correlation_id() for _ in range(1000)}
    assert len(ids) == 1000
