# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import sys
from typing import Any, List

import pytest


def test_default(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.asyncio
        async def test_default(page, browser_name):
            assert browser_name == "chromium"
            user_agent = await page.evaluate("window.navigator.userAgent")
            assert "HeadlessChrome" in user_agent
            await page.set_content('<span id="foo">bar</span>')
            assert await page.query_selector("#foo")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_slowmo(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        from time import monotonic
        import pytest
        @pytest.mark.asyncio
        async def test_slowmo(page):
            email = "test@test.com"
            await page.set_content("<input type='text'/>")
            start_time = monotonic()
            await page.type("input", email)
            end_time = monotonic()
            assert end_time - start_time >= 1
            assert end_time - start_time < 2
    """
    )
    result = testdir.runpytest("--browser", "chromium", "--slowmo", "1000")
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    "channel",
    [
        "chrome",
        "msedge",
    ],
)
def test_browser_channel(channel: str, testdir: pytest.Testdir) -> None:
    if channel == "msedge" and sys.platform == "linux":
        pytest.skip("msedge not supported on linux")
    testdir.makepyfile(
        f"""
        import pytest

        @pytest.mark.asyncio
        async def test_browser_channel(page, browser_name, browser_channel):
            assert browser_name == "chromium"
            assert browser_channel == "{channel}"
    """
    )
    result = testdir.runpytest("--browser-channel", channel)
    result.assert_outcomes(passed=1)


def test_invalid_browser_channel(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.asyncio
        async def test_browser_channel(page, browser_name, browser_channel):
            assert browser_name == "chromium"
    """
    )
    result = testdir.runpytest("--browser-channel", "not-exists")
    result.assert_outcomes(errors=1)
    assert "Unsupported chromium channel" in "\n".join(result.outlines)


def test_multiple_browsers(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_multiple_browsers(page):
            await page.set_content('<span id="foo">bar</span>')
            assert await page.query_selector("#foo")
    """
    )
    result = testdir.runpytest(
        "--browser", "chromium", "--browser", "firefox", "--browser", "webkit"
    )
    result.assert_outcomes(passed=3)


def test_browser_context_args(testdir: pytest.Testdir) -> None:
    testdir.makeconftest(
        """
        import pytest

        @pytest.fixture(scope="session")
        def browser_context_args():
            return {"user_agent": "foobar"}
    """
    )
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_browser_context_args(page):
            assert await page.evaluate("window.navigator.userAgent") == "foobar"
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_user_defined_browser_context_args(testdir: pytest.Testdir) -> None:
    testdir.makeconftest(
        """
        import pytest

        @pytest.fixture(scope="session")
        def browser_context_args():
            return {"user_agent": "foobar"}
    """
    )
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.browser_context_args(user_agent="overwritten", locale="new-locale")
        @pytest.mark.asyncio
        async def test_browser_context_args(page):
            assert await page.evaluate("window.navigator.userAgent") == "overwritten"
            assert await page.evaluate("window.navigator.languages") == ["new-locale"]
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_chromium(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_is_chromium(page, browser_name, is_chromium, is_firefox, is_webkit):
            assert browser_name == "chromium"
            assert is_chromium
            assert is_firefox is False
            assert is_webkit is False
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_firefox(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_is_firefox(page, browser_name, is_chromium, is_firefox, is_webkit):
            assert browser_name == "firefox"
            assert is_chromium is False
            assert is_firefox
            assert is_webkit is False
    """
    )
    result = testdir.runpytest("--browser", "firefox")
    result.assert_outcomes(passed=1)


def test_webkit(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_is_webkit(page, browser_name, is_chromium, is_firefox, is_webkit):
            assert browser_name == "webkit"
            assert is_chromium is False
            assert is_firefox is False
            assert is_webkit
    """
    )
    result = testdir.runpytest("--browser", "webkit")
    result.assert_outcomes(passed=1)


def test_goto(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_base_url(page, base_url):
            assert base_url == "https://example.com"
            await page.goto("/foobar")
            assert page.url == "https://example.com/foobar"
            await page.goto("https://example.org")
            assert page.url == "https://example.org/"
    """
    )
    result = testdir.runpytest("--base-url", "https://example.com")
    result.assert_outcomes(passed=1)


def test_base_url_via_fixture(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.fixture(scope="session")
        def base_url():
            return "https://example.com"

        @pytest.mark.asyncio
        async def test_base_url(page, base_url):
            assert base_url == "https://example.com"
            await page.goto("/foobar")
            assert page.url == "https://example.com/foobar"
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_skip_browsers(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.skip_browser("firefox")
        @pytest.mark.asyncio
        async def test_base_url(page, browser_name):
            assert browser_name in ["chromium", "webkit"]
    """
    )
    result = testdir.runpytest(
        "--browser", "chromium", "--browser", "firefox", "--browser", "webkit"
    )
    result.assert_outcomes(passed=2, skipped=1)


def test_only_browser(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.only_browser("firefox")
        @pytest.mark.asyncio
        async def test_base_url(page, browser_name):
            assert browser_name == "firefox"
    """
    )
    result = testdir.runpytest(
        "--browser", "chromium", "--browser", "firefox", "--browser", "webkit"
    )
    result.assert_outcomes(passed=1, skipped=2)


def test_parameterization(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.asyncio
        async def test_all_browsers(page):
            pass

        @pytest.mark.asyncio
        async def test_without_browser():
            pass
    """
    )
    result = testdir.runpytest(
        "--verbose",
        "--browser",
        "chromium",
        "--browser",
        "firefox",
        "--browser",
        "webkit",
    )
    result.assert_outcomes(passed=4)
    assert "test_without_browser PASSED" in "\n".join(result.outlines)


def test_xdist(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.asyncio
        async def test_a(page):
            await page.set_content('<span id="foo">a</span>')
            await page.wait_for_timeout(200)
            assert await page.query_selector("#foo")

        @pytest.mark.asyncio
        async def test_b(page):
            await page.wait_for_timeout(2000)
            await page.set_content('<span id="foo">a</span>')
            assert await page.query_selector("#foo")

        @pytest.mark.asyncio
        async def test_c(page):
            await page.set_content('<span id="foo">a</span>')
            await page.wait_for_timeout(200)
            assert await page.query_selector("#foo")

        @pytest.mark.asyncio
        async def test_d(page):
            await page.set_content('<span id="foo">a</span>')
            await page.wait_for_timeout(200)
            assert await page.query_selector("#foo")
    """
    )
    result = testdir.runpytest(
        "--verbose",
        "--browser",
        "chromium",
        "--browser",
        "firefox",
        "--browser",
        "webkit",
        "--numprocesses",
        "2",
    )
    result.assert_outcomes(passed=12)
    assert "gw0" in "\n".join(result.outlines)
    assert "gw1" in "\n".join(result.outlines)


def test_headed(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_base_url(page, browser_name):
            user_agent = await page.evaluate("window.navigator.userAgent")
            assert "HeadlessChrome" not in user_agent
    """
    )
    result = testdir.runpytest("--browser", "chromium", "--headed")
    result.assert_outcomes(passed=1)


def test_invalid_browser_name(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_base_url(page):
            pass
    """
    )
    result = testdir.runpytest("--browser", "test123")
    assert any(["--browser: invalid choice" in line for line in result.errlines])


def test_django(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
    from django.test import TestCase
    import pytest
    class Proj1Test(TestCase):
        @pytest.mark.asyncio
        async def test_one(self):
            self.assertTrue(True)

    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_browser_context_args_device(testdir: pytest.Testdir) -> None:
    testdir.makeconftest(
        """
        import pytest

        @pytest.fixture(scope="session")
        def browser_context_args(browser_context_args, playwright):
            iphone_11 = playwright.devices['iPhone 11 Pro']
            return {**browser_context_args, **iphone_11}
    """
    )
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_browser_context_args(page):
            assert "iPhone" in await page.evaluate("window.navigator.userAgent")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_launch_persistent_context_session(testdir: pytest.Testdir) -> None:
    testdir.makeconftest(
        """
        import pytest
        from playwright.async_api import BrowserType
        from typing import Dict
        import pytest_asyncio

        @pytest_asyncio.fixture(scope="session")
        async def context(
            browser_type: BrowserType,
            browser_type_launch_args: Dict,
            browser_context_args: Dict
        ):
            context = await browser_type.launch_persistent_context("./foobar", **{
                **browser_type_launch_args,
                **browser_context_args,
                "locale": "de-DE",
            })
            yield context
            await context.close()
    """
    )
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_browser_context_args(page):
            assert await page.evaluate("navigator.language") == "de-DE"
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_context_page_on_session_level(testdir: pytest.Testdir) -> None:
    testdir.makeconftest(
        """
        import pytest
        from playwright.async_api import Browser, BrowserContext
        from typing import Dict
        import pytest_asyncio

        @pytest_asyncio.fixture(scope="session")
        async def context(
            browser: Browser,
            browser_context_args: Dict
        ):
            context = await browser.new_context(**{
                **browser_context_args,
            })
            yield context
            await context.close()

        @pytest_asyncio.fixture(scope="session")
        async def page(
            context: BrowserContext,
        ):
            page = await context.new_page()
            yield page
    """
    )
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_a(page):
            await page.goto("data:text/html,<div>B</div>")
            assert await page.text_content("div") == "B"

        @pytest.mark.asyncio
        async def test_b(page):
            assert await page.text_content("div") == "B"
        """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=2)


def test_launch_persistent_context_function(testdir: pytest.Testdir) -> None:
    testdir.makeconftest(
        """
        import pytest
        from playwright.async_api import BrowserType
        from typing import Dict
        import pytest_asyncio

        @pytest_asyncio.fixture()
        async def context(
            browser_type: BrowserType,
            browser_type_launch_args: Dict,
            browser_context_args: Dict
        ):
            context = await browser_type.launch_persistent_context("./foobar", **{
                **browser_type_launch_args,
                **browser_context_args,
                "locale": "de-DE",
            })
            yield context
            await context.close()
    """
    )
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_browser_context_args(page):
            assert await page.evaluate("navigator.language") == "de-DE"
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_device_emulation(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_device_emulation(page, device):
            assert device == 'iPhone 11 Pro'
            assert "iPhone" in await page.evaluate("window.navigator.userAgent")
    """
    )
    result = testdir.runpytest("--device", "iPhone 11 Pro")
    result.assert_outcomes(passed=1)


def test_rep_call_keyboard_interrupt(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.asyncio
        async def test_rep_call(page):
            assert await page.evaluate("1 + 1") == 2
            raise KeyboardInterrupt
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=0, failed=0, skipped=0)


def test_artifacts_by_default_it_should_not_store_anything(
    testdir: pytest.Testdir,
) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.asyncio
        async def test_passing(page):
            assert 2 == await page.evaluate("1 + 1")

        @pytest.mark.asyncio
        async def test_failing(page):
            raise Exception("Failed")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1, failed=1)
    for dir in testdir.tmpdir.listdir():
        assert dir.basename != "test-results"


def test_artifacts_new_folder_on_run(
    testdir: pytest.Testdir,
) -> None:
    test_results_dir = os.path.join(testdir.tmpdir, "test-results")
    os.mkdir(os.path.join(test_results_dir))
    with open(os.path.join(test_results_dir, "example.json"), "w") as f:
        f.write("foo")

    testdir.makepyfile(
        """
        import pytest
        @pytest.mark.asyncio
        async def test_passing(page):
            assert 2 == await page.evaluate("1 + 1")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)
    for dir in testdir.tmpdir.listdir():
        assert dir.basename != "test-results"


def test_artifacts_should_store_everything_if_on(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.asyncio
        async def test_passing(page):
            assert 2 == await page.evaluate("1 + 1")

        @pytest.mark.asyncio
        async def test_failing(page):
            raise Exception("Failed")
    """
    )
    result = testdir.runpytest("--screenshot", "on", "--video", "on", "--tracing", "on")
    result.assert_outcomes(passed=1, failed=1)
    test_results_dir = os.path.join(testdir.tmpdir, "test-results")
    expected = [
        {
            "name": "test-artifacts-should-store-everything-if-on-py-test-failing-chromium",
            "children": [
                {
                    "name": re.compile(r".*webm"),
                },
                {
                    "name": "test-failed-1.png",
                },
                {
                    "name": "trace.zip",
                },
            ],
        },
        {
            "name": "test-artifacts-should-store-everything-if-on-py-test-passing-chromium",
            "children": [
                {
                    "name": re.compile(r".*webm"),
                },
                {
                    "name": "test-finished-1.png",
                },
                {
                    "name": "trace.zip",
                },
            ],
        },
    ]
    _assert_folder_tree(test_results_dir, expected)


def test_artifacts_retain_on_failure(testdir: pytest.Testdir) -> None:
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.asyncio
        async def test_passing(page):
            assert 2 == await page.evaluate("1 + 1")

        @pytest.mark.asyncio
        async def test_failing(page):
            raise Exception("Failed")
    """
    )
    result = testdir.runpytest(
        "--screenshot",
        "only-on-failure",
        "--video",
        "retain-on-failure",
        "--tracing",
        "retain-on-failure",
    )
    result.assert_outcomes(passed=1, failed=1)
    test_results_dir = os.path.join(testdir.tmpdir, "test-results")
    expected = [
        {
            "name": "test-artifacts-retain-on-failure-py-test-failing-chromium",
            "children": [
                {
                    "name": re.compile(r".*webm"),
                },
                {
                    "name": "test-failed-1.png",
                },
                {
                    "name": "trace.zip",
                },
            ],
        }
    ]
    _assert_folder_tree(test_results_dir, expected)


def test_should_work_with_test_names_which_exceeds_256_characters(
    testdir: pytest.Testdir,
) -> None:
    long_test_name = "abcdefghijklmnopqrstuvwxyz" * 100
    testdir.makepyfile(
        f"""
        import pytest
        @pytest.mark.asyncio
        async def test_{long_test_name}(page):
            pass
    """
    )
    result = testdir.runpytest("--tracing", "on")
    result.assert_outcomes(passed=1, failed=0)
    test_results_dir = os.path.join(testdir.tmpdir, "test-results")
    expected = [
        {
            "name": "test-should-work-with-test-names-which-exceeds-256-characters-py-test-abcdefghijklmnopqrstuvwxyzabcd-23f2441-nopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz-chromium/",
            "children": [
                {
                    "name": "trace.zip",
                },
            ],
        },
    ]
    _assert_folder_tree(test_results_dir, expected)


def _assert_folder_tree(root: str, expected_tree: List[Any]) -> None:
    assert len(os.listdir(root)) == len(expected_tree)
    for file in expected_tree:
        if isinstance(file["name"], str):
            if "children" in file:
                assert os.path.isdir(os.path.join(root, file["name"]))
            else:
                assert os.path.isfile(os.path.join(root, file["name"]))
        if isinstance(file["name"], re.Pattern):
            assert any([file["name"].match(item) for item in os.listdir(root)])
            assert "children" not in file
        if "children" in file:
            _assert_folder_tree(os.path.join(root, file["name"]), file["children"])


def test_is_able_to_set_expect_timeout_via_conftest(testdir: pytest.Testdir) -> None:
    testdir.makeconftest(
        """
        from playwright.async_api import expect
        expect.set_options(timeout=1111)
    """
    )
    testdir.makepyfile(
        """
        from playwright.async_api import expect
        import pytest

        @pytest.mark.asyncio
        async def test_small_timeout(page):
            await page.goto("data:text/html,")
            await expect(page.locator("#A")).to_be_visible()
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=0, failed=1, skipped=0)
    result.stdout.fnmatch_lines("*AssertionError: Locator expected to be visible*")
    result.stdout.fnmatch_lines("*LocatorAssertions.to_be_visible with timeout 1111ms*")
