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
from typing import Any, Callable, Dict, Generator, List
import pytest
from playwright.sync_api import (
    Browser,
    BrowserContext,
    BrowserType,
    Error,
    Page,
    Playwright,
    sync_playwright,
)
from slugify import slugify

from pytest_playwright.base import PytestPlaywright


class PytestPlaywrightSync(PytestPlaywright):
    @pytest.fixture(scope="session")
    def playwright(self) -> Generator[Playwright, None, None]:
        pw = sync_playwright().start()
        yield pw
        pw.stop()

    @pytest.fixture(scope="session")
    def launch_browser(
        self,
        browser_type_launch_args: Dict,
        browser_type: BrowserType,
    ) -> Callable[..., Browser]:
        def launch(**kwargs: Dict) -> Browser:
            launch_options = {**browser_type_launch_args, **kwargs}
            browser = browser_type.launch(**launch_options)
            return browser

        return launch

    @pytest.fixture(scope="session")
    def browser(
        self, launch_browser: Callable[[], Browser]
    ) -> Generator[Browser, None, None]:
        browser = launch_browser()
        yield browser
        browser.close()
        self.artifacts_folder.cleanup()

    @pytest.fixture
    def context(
        self,
        browser: Browser,
        browser_context_args: Dict,
        pytestconfig: Any,
        request: pytest.FixtureRequest,
    ) -> Generator[BrowserContext, None, None]:
        pages: List[Page] = []

        context_args_marker = next(
            request.node.iter_markers("browser_context_args"), None
        )
        additional_context_args = (
            context_args_marker.kwargs if context_args_marker else {}
        )
        browser_context_args.update(additional_context_args)

        context = browser.new_context(**browser_context_args)
        context.on("page", lambda page: pages.append(page))

        tracing_option = pytestconfig.getoption("--tracing")
        capture_trace = tracing_option in ["on", "retain-on-failure"]
        if capture_trace:
            context.tracing.start(
                title=slugify(request.node.nodeid),
                screenshots=True,
                snapshots=True,
                sources=True,
            )

        yield context

        # If request.node is missing rep_call, then some error happened during execution
        # that prevented teardown, but should still be counted as a failure
        failed = (
            request.node.rep_call.failed if hasattr(request.node, "rep_call") else True
        )

        if capture_trace:
            retain_trace = tracing_option == "on" or (
                failed and tracing_option == "retain-on-failure"
            )
            if retain_trace:
                trace_path = self._build_artifact_test_folder(
                    pytestconfig, request, "trace.zip"
                )
                context.tracing.stop(path=trace_path)
            else:
                context.tracing.stop()

        screenshot_option = pytestconfig.getoption("--screenshot")
        capture_screenshot = screenshot_option == "on" or (
            failed and screenshot_option == "only-on-failure"
        )
        if capture_screenshot:
            for index, page in enumerate(pages):
                human_readable_status = "failed" if failed else "finished"
                screenshot_path = self._build_artifact_test_folder(
                    pytestconfig, request, f"test-{human_readable_status}-{index+1}.png"
                )
                try:
                    page.screenshot(
                        timeout=5000,
                        path=screenshot_path,
                        full_page=pytestconfig.getoption("--full-page-screenshot"),
                    )
                except Error:
                    pass

        context.close()

        video_option = pytestconfig.getoption("--video")
        preserve_video = video_option == "on" or (
            failed and video_option == "retain-on-failure"
        )
        if preserve_video:
            for page in pages:
                video = page.video
                if not video:
                    continue
                try:
                    video_path = video.path()
                    file_name = os.path.basename(video_path)
                    video.save_as(
                        path=self._build_artifact_test_folder(
                            pytestconfig, request, file_name
                        )
                    )
                except Error:
                    # Silent catch empty videos.
                    pass

    @pytest.fixture
    def page(self, context: BrowserContext) -> Generator[Page, None, None]:
        page = context.new_page()
        yield page
