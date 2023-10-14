from __future__ import annotations

import pytest

from fpx import transport


class TestAioHttpTransport:
    @pytest.fixture()
    def transport_name(self):
        return "aiohttp"

    @pytest.mark.asyncio()
    async def test_stream(self, faker, rmock):
        url = faker.uri()
        rmock(url=url, body=f"hello world, {url}")

        tp = transport.AioHttpTransport()
        async for _path, _name, content, _response in tp.stream([url]):
            result = b""
            async for chunk in content:
                result += chunk

            assert result == bytes(f"hello world, {url}", "utf8")


class TestHttpxTransport:
    @pytest.fixture()
    def transport_name(self):
        return "httpx"

    @pytest.mark.asyncio()
    async def test_stream(self, faker, rmock):
        url = faker.uri()
        rmock(url=url, body=f"hello world, {url}")

        tp = transport.HttpxTransport()
        async for _path, _name, content, _response in tp.stream([url]):
            result = b""
            async for chunk in content:
                result += chunk

            assert result == bytes(f"hello world, {url}", "utf8")
