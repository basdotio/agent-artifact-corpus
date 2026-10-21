from __future__ import annotations

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import unittest
from collections.abc import Callable, Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ejryan89-skill-core" / "scripts"))

import github_activity_report as report
from bounded_process import Finished
from github_activity_report import (
    MAX_INTERVAL,
    SEARCH_INTERVAL,
    Activity,
    GitHubSearchClient,
    collect_activity,
    main,
    months_window,
    render_report,
)
from github_client import BACKOFF, CommandResult, GitHubError, subprocess_runner

SPAN = re.compile(r"(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})")
SECONDARY_LIMIT = "gh: You have exceeded a secondary rate limit. (HTTP 403)"
TODAY = date(2026, 5, 20)


def ok(payload: Any, headers: str = "") -> CommandResult:
    body = json.dumps(payload)
    return CommandResult(0, f"HTTP/2.0 200 OK\n{headers}\n{body}" if headers else body, "")


def failed(stderr: str, head: str = "") -> CommandResult:
    return CommandResult(1, head, stderr)


def search_page(items: list[Any], total: object = None) -> dict[str, Any]:
    return {"total_count": len(items) if total is None else total, "incomplete_results": False, "items": items}


class Recorder:
    """A sleeper that records waits and advances a fake clock instead of sleeping."""

    def __init__(self, now: float = 1000.0) -> None:
        self.waits: list[float] = []
        self.now = now

    def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.now += seconds

    def clock(self) -> float:
        return self.now


def scripted(*responses: CommandResult) -> tuple[Callable[[Sequence[str]], CommandResult], list[list[str]]]:
    queue = list(responses)
    calls: list[list[str]] = []

    def run(arguments: Sequence[str]) -> CommandResult:
        calls.append(list(arguments))
        return queue.pop(0)

    return run, calls


def bounded(*answers: CommandResult) -> tuple[Callable[[Sequence[str]], CommandResult], list[list[str]]]:
    """A runner that answers with `answers` in turn, repeating the last, and fails a test that pages without end."""
    calls: list[list[str]] = []

    def run(arguments: Sequence[str]) -> CommandResult:
        calls.append(list(arguments))
        if len(calls) > 5:
            raise AssertionError("pagination did not stop")
        return answers[min(len(calls), len(answers)) - 1]

    return run, calls


KEY = ("id",)


def rows(count: int, start: int = 0) -> list[dict[str, str]]:
    return [{"id": f"i{index}"} for index in range(start, start + count)]


def fetch(client: GitHubSearchClient) -> int:
    return len(client.search_all("search/issues", "q", KEY)[0])


def client_for(
    run: Callable[[Sequence[str]], CommandResult], clock: float = 1000.0
) -> tuple[GitHubSearchClient, Recorder]:
    sleeper = Recorder(clock)
    return GitHubSearchClient(run, sleeper, sleeper.clock), sleeper


class WindowTests(unittest.TestCase):
    def test_window_is_calendar_aligned_and_ends_with_the_current_month(self) -> None:
        window = months_window(date(2026, 9, 30), 12)
        self.assertEqual(12, len(window))
        self.assertEqual(date(2025, 10, 1), window[0])
        self.assertEqual(date(2026, 9, 1), window[-1])

    def test_window_rolls_over_the_year(self) -> None:
        self.assertEqual([date(2025, 11, 1), date(2025, 12, 1), date(2026, 1, 1)], months_window(date(2026, 1, 15), 3))


class SearchTests(unittest.TestCase):
    def test_pagination_stops_at_a_short_page(self) -> None:
        run, calls = scripted(ok(search_page(rows(100), 150)), ok(search_page(rows(50, 100), 150)))
        client, sleeper = client_for(run)
        items, capped = client.search_all("search/issues", "org:acme author:octo", KEY)
        self.assertEqual((150, False), (len(items), capped))
        self.assertEqual(2, len(calls))
        self.assertEqual([SEARCH_INTERVAL], sleeper.waits)
        query = parse_qs(urlsplit(calls[1][-1]).query)
        self.assertEqual(["org:acme author:octo"], query["q"])
        self.assertEqual((["100"], ["2"]), (query["per_page"], query["page"]))
        self.assertEqual(["gh", "api", "-i"], calls[0][:3])

    def test_pagination_stops_when_the_total_is_reached_on_a_full_page(self) -> None:
        run, calls = scripted(ok(search_page(rows(100), 200)), ok(search_page(rows(100, 100), 200)))
        client, _ = client_for(run)
        self.assertEqual(200, len(client.search_all("search/issues", "q", KEY)[0]))
        self.assertEqual(2, len(calls))

    def test_pagination_stops_at_the_search_cap_and_reports_truncation(self) -> None:
        run, calls = scripted(*[ok(search_page(rows(100, index * 100), 2500)) for index in range(12)])
        client, _ = client_for(run)
        items, capped = client.search_all("search/commits", "q", KEY)
        self.assertEqual((1000, True), (len(items), capped))
        self.assertEqual(10, len(calls))

    def test_range_under_the_cap_is_fetched_with_one_query(self) -> None:
        github = DatedSearch({"q": [(date(2026, 1, day), {"id": str(day)}) for day in range(1, 31)]})
        client, _ = client_for(github)
        items, capped = client.search_range("search/issues", "q {span}", date(2026, 1, 1), date(2026, 1, 31), KEY)
        self.assertEqual((30, []), (len(items), capped))
        self.assertEqual(["q 2026-01-01..2026-01-31"], github.queries)

    def test_range_over_the_cap_is_split_until_each_part_fits(self) -> None:
        dated = [(date(2026, 1, 1) + timedelta(days=index % 60), {"id": str(index)}) for index in range(1500)]
        github = DatedSearch({"q": dated})
        client, _ = client_for(github)
        items, capped = client.search_range("search/issues", "q {span}", date(2026, 1, 1), date(2026, 3, 1), KEY)
        self.assertEqual(1500, len(items))
        self.assertEqual([], capped)
        self.assertEqual("q 2026-01-01..2026-03-01", github.queries[0])
        self.assertIn("q 2026-01-01..2026-01-30", github.queries)
        self.assertIn("q 2026-01-31..2026-03-01", github.queries)

    def test_a_single_day_over_the_cap_is_reported_as_capped(self) -> None:
        github = DatedSearch({"q": [(date(2026, 1, 5), {"id": str(index)}) for index in range(1200)]})
        client, _ = client_for(github)
        items, capped = client.search_range("search/issues", "q {span}", date(2026, 1, 1), date(2026, 1, 8), KEY)
        self.assertEqual(1000, len(items))
        self.assertEqual(["2026-01-05"], capped)

    def test_rate_limits_widen_the_spacing_between_searches(self) -> None:
        run, _ = scripted(
            ok(search_page([])),
            failed(SECONDARY_LIMIT),
            ok(search_page([])),
            failed(SECONDARY_LIMIT),
            failed(SECONDARY_LIMIT),
            failed(SECONDARY_LIMIT),
            ok(search_page([])),
            ok(search_page([])),
        )
        client, sleeper = client_for(run)
        for _ in range(4):
            fetch(client)
        expected = [SEARCH_INTERVAL, 5.0, SEARCH_INTERVAL * 1.5, 5.0, 10.0, 20.0, MAX_INTERVAL]
        self.assertEqual(len(expected), len(sleeper.waits))
        for want, got in zip(expected, sleeper.waits, strict=True):
            self.assertAlmostEqual(want, got)

    def test_spacing_recovers_after_a_run_of_clean_searches(self) -> None:
        run, _ = scripted(failed(SECONDARY_LIMIT), *[ok(search_page([]))] * 12)
        client, _ = client_for(run)
        fetch(client)
        self.assertAlmostEqual(SEARCH_INTERVAL * 1.5, client.interval)
        for _ in range(9):
            fetch(client)
        self.assertAlmostEqual(SEARCH_INTERVAL, client.interval)

    def test_spacing_is_measured_from_the_end_of_the_previous_request(self) -> None:
        sleeper = Recorder()

        def slow(arguments: Sequence[str]) -> CommandResult:
            sleeper.now += 1.5
            return ok(search_page([]))

        client = GitHubSearchClient(slow, sleeper, sleeper.clock)
        fetch(client)
        fetch(client)
        self.assertEqual([SEARCH_INTERVAL], sleeper.waits)

    def test_graphql_searches_are_paced_but_other_graphql_requests_are_not(self) -> None:
        search = {"data": {"search": {"issueCount": 0, "pageInfo": {"hasNextPage": False}, "nodes": []}}}
        run, _ = scripted(ok(search), ok({"data": {"node": {}}}), ok(search))
        client, sleeper = client_for(run)
        client.graphql_search_range("q {span}", "octo", date(2026, 1, 1), date(2026, 1, 31))
        client.graphql("query", {"id": "PR_1"})
        client.graphql_search_range("q {span}", "octo", date(2026, 1, 1), date(2026, 1, 31))
        self.assertEqual([SEARCH_INTERVAL], sleeper.waits)

    def test_underfilled_search_is_repeated_until_complete(self) -> None:
        shifted = [ok(search_page(rows(100), 150)), ok(search_page(rows(40, 100), 150))]
        complete = [ok(search_page(rows(100), 150)), ok(search_page(rows(50, 100), 150))]
        run, calls = scripted(*shifted, *complete)
        client, _ = client_for(run)
        self.assertEqual(150, fetch(client))
        self.assertEqual(4, len(calls))

    def test_repeated_pull_requests_mean_results_shifted(self) -> None:
        duplicated = [ok(search_page(rows(100), 150)), ok(search_page(rows(50, 99), 150))]
        run, _ = scripted(*duplicated * 3)
        client, _ = client_for(run)
        with self.assertRaises(GitHubError) as context:
            fetch(client)
        self.assertEqual("incomplete", context.exception.kind)
        self.assertIn("returned 149 distinct results but GitHub reported 150", str(context.exception))

    def test_commit_search_may_list_one_commit_twice(self) -> None:
        run, calls = scripted(ok(search_page(rows(2) + rows(1), 3)))
        client, _ = client_for(run)
        items, capped = client.search_all("search/commits", "q", KEY)
        self.assertEqual((2, False, 1), (len(items), capped, len(calls)))

    def test_underfilled_commit_search_fails_closed(self) -> None:
        run, calls = scripted(*[ok(search_page(rows(2), 3))] * 3)
        client, _ = client_for(run)
        with self.assertRaises(GitHubError) as context:
            client.search_all("search/commits", "q", KEY)
        self.assertEqual("incomplete", context.exception.kind)
        self.assertEqual(3, len(calls))

    def test_underfilled_graphql_search_is_repeated_then_fails_closed(self) -> None:
        def page(nodes: int, count: int) -> CommandResult:
            return ok(
                {
                    "data": {
                        "search": {
                            "issueCount": count,
                            "pageInfo": {"hasNextPage": False},
                            "nodes": [{"id": f"PR_{index}"} for index in range(nodes)],
                        }
                    }
                }
            )

        run, calls = scripted(page(2, 3), page(3, 3))
        client, _ = client_for(run)
        nodes, capped = client.graphql_search_range("q {span}", "octo", date(2026, 1, 1), date(2026, 1, 31))
        self.assertEqual((3, [], 2), (len(nodes), capped, len(calls)))
        run, calls = scripted(*[page(2, 3)] * 3)
        client, _ = client_for(run)
        with self.assertRaises(GitHubError) as context:
            client.graphql_search_range("q {span}", "octo", date(2026, 1, 1), date(2026, 1, 31))
        self.assertEqual("incomplete", context.exception.kind)
        self.assertEqual(3, len(calls))

    def test_a_search_result_must_be_an_object(self) -> None:
        client, _ = client_for(scripted(ok(search_page([{"id": "i0"}, "i1"])))[0])
        with self.assertRaises(GitHubError) as context:
            fetch(client)
        self.assertEqual("malformed", context.exception.kind)
        self.assertIn("response.items[1] must be an object", str(context.exception))

    def test_graphql_search_page_info_must_be_typed_and_advance(self) -> None:
        def page(page_info: dict[str, Any]) -> CommandResult:
            return ok({"data": {"search": {"issueCount": 5, "pageInfo": page_info, "nodes": [{"id": "PR_1"}]}}})

        cases: dict[str, dict[str, Any]] = {
            "data.search.pageInfo.hasNextPage must be a boolean": {"hasNextPage": "false", "endCursor": None},
            "data.search.pageInfo.endCursor must be a non-empty string": {"hasNextPage": True, "endCursor": None},
            "data.search.pageInfo.endCursor must be a cursor not already followed": {
                "hasNextPage": True,
                "endCursor": "c1",
            },
        }
        calls: list[list[str]] = []
        for message, page_info in cases.items():
            run, calls = bounded(page(page_info))
            client, _ = client_for(run)
            with self.subTest(message=message), self.assertRaises(GitHubError) as context:
                client.graphql_search_range("q {span}", "octo", date(2026, 1, 1), date(2026, 1, 31))
            self.assertEqual("malformed", context.exception.kind)
            self.assertIn(message, str(context.exception))
            self.assertLessEqual(len(calls), 2)
        self.assertIn("-f", calls[1])
        self.assertIn("after=c1", calls[1], "the cursor GitHub gave is followed once, then refused when it repeats")

    def test_invalid_json_fails_closed(self) -> None:
        client, _ = client_for(scripted(CommandResult(0, "not json", ""))[0])
        with self.assertRaises(GitHubError) as context:
            fetch(client)
        self.assertEqual("malformed", context.exception.kind)


class RetryTests(unittest.TestCase):
    def test_secondary_rate_limit_backs_off_then_succeeds(self) -> None:
        run, calls = scripted(failed(SECONDARY_LIMIT), ok(search_page(rows(7))))
        client, sleeper = client_for(run)
        self.assertEqual(7, fetch(client))
        self.assertEqual([5.0], sleeper.waits)
        self.assertEqual(2, len(calls))

    def test_retry_after_header_sets_the_wait(self) -> None:
        head = "HTTP/2.0 403 Forbidden\nRetry-After: 42\r\nX-Ratelimit-Remaining: 3\r\n\r\n{}"
        client, sleeper = client_for(scripted(failed(SECONDARY_LIMIT, head), ok(search_page([], 0)))[0])
        fetch(client)
        self.assertEqual([42.0], sleeper.waits)

    def test_exhausted_quota_waits_until_the_reset_time(self) -> None:
        head = "HTTP/2.0 403 Forbidden\nX-Ratelimit-Remaining: 0\r\nX-Ratelimit-Reset: 1030\r\n\r\n{}"
        client, sleeper = client_for(scripted(failed("gh: HTTP 403", head), ok(search_page([], 0)))[0], clock=1000.0)
        fetch(client)
        self.assertEqual([31.0], sleeper.waits)

    def test_http_429_is_retried(self) -> None:
        client, sleeper = client_for(scripted(failed("gh: HTTP 429"), ok(search_page([], 0)))[0])
        fetch(client)
        self.assertEqual([5.0], sleeper.waits)

    def test_a_wait_longer_than_the_limit_fails_instead_of_sleeping(self) -> None:
        head = "HTTP/2.0 403 Forbidden\nRetry-After: 3600\r\n\r\n{}"
        client, sleeper = client_for(scripted(failed(SECONDARY_LIMIT, head))[0])
        with self.assertRaises(GitHubError) as context:
            fetch(client)
        self.assertEqual("rate_limit", context.exception.kind)
        self.assertEqual([], sleeper.waits)

    def test_exhausting_retries_raises_a_rate_limit_error(self) -> None:
        run, calls = scripted(*[failed(SECONDARY_LIMIT)] * (BACKOFF.retries + 1))
        client, sleeper = client_for(run)
        with self.assertRaises(GitHubError) as context:
            fetch(client)
        self.assertEqual("rate_limit", context.exception.kind)
        self.assertEqual([5.0, 10.0, 20.0, 40.0, 80.0], sleeper.waits)
        self.assertEqual(BACKOFF.retries + 1, len(calls))

    def test_incomplete_search_results_are_retried(self) -> None:
        incomplete = dict(search_page([], 0), incomplete_results=True)
        client, sleeper = client_for(scripted(ok(incomplete), ok(search_page(rows(1))))[0])
        self.assertEqual(1, fetch(client))
        self.assertEqual([5.0], sleeper.waits)

    def test_graphql_rate_limit_is_retried_and_other_errors_fail(self) -> None:
        limited = {"errors": [{"type": "RATE_LIMITED", "message": "slow down"}]}
        client, sleeper = client_for(scripted(ok(limited), ok({"data": {"nodes": []}}))[0])
        self.assertEqual({"nodes": []}, client.graphql("query", {"id": "PR_1"}))
        self.assertEqual([5.0], sleeper.waits)
        client, _ = client_for(scripted(ok({"errors": [{"type": "FORBIDDEN", "message": "SSO"}]}))[0])
        with self.assertRaisesRegex(GitHubError, "FORBIDDEN"):
            client.graphql("query", {"id": "PR_1"})

    def test_output_that_is_not_utf8_is_replaced_instead_of_failing(self) -> None:
        body = json.dumps(search_page([{"id": "i0", "title": "TITLE"}])).replace("TITLE", "caf\xe9")
        process = Finished(0, body.encode("latin-1"), b"")
        with mock.patch("github_client.run_bounded", return_value=process):
            items, _ = GitHubSearchClient(sleeper=Recorder()).search_all("search/issues", "q", KEY)
        self.assertEqual("caf\ufffd", items[0]["title"])

    def test_missing_cli_fails_with_prerequisite_error(self) -> None:
        with (
            mock.patch("github_client.run_bounded", side_effect=FileNotFoundError("gh")),
            self.assertRaises(GitHubError) as context,
        ):
            subprocess_runner(["gh", "api", "user"])
        self.assertEqual("prerequisite", context.exception.kind)


class DatedSearch:
    """Answers searches by filtering dated items to the query's date range, then paginating."""

    def __init__(self, dated: dict[str, list[tuple[date, dict[str, Any]]]] | None = None) -> None:
        self.dated = dated or {}
        self.queries: list[str] = []

    def __call__(self, arguments: Sequence[str]) -> CommandResult:
        if arguments[3] == "graphql":
            return self.graphql(list(arguments[4:]))
        parameters = parse_qs(urlsplit(arguments[3]).query)
        query = parameters["q"][0]
        self.queries.append(query)
        match = SPAN.search(query)
        if match is None:
            raise AssertionError(query)
        key = (query[: match.start()] + query[match.end() :]).strip()
        first, last = date.fromisoformat(match[1]), date.fromisoformat(match[2])
        items = [item for day, item in self.dated.get(key, []) if first <= day <= last]
        page, size = int(parameters["page"][0]), int(parameters["per_page"][0])
        return ok(search_page(items[(page - 1) * size : page * size], len(items)))

    def graphql(self, arguments: list[str]) -> CommandResult:
        raise AssertionError("unexpected GraphQL request")


class FakeGitHub(DatedSearch):
    def __init__(self) -> None:
        super().__init__()
        self.reviews: dict[str, list[dict[str, Any]]] = {}

    def graphql(self, arguments: list[str]) -> CommandResult:
        values = dict(entry.partition("=")[::2] for entry in arguments[1::2])
        if "q" in values:
            return self.search(values["q"], int(values.get("after", "0")))
        node_id = values["id"]
        second = self.reviews[node_id][1]
        return ok(
            {
                "data": {
                    "node": {
                        "id": node_id,
                        "reviews": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": second["nodes"]},
                    }
                }
            }
        )

    def search(self, query: str, offset: int) -> CommandResult:
        """GraphQL search: pull request nodes carry the user's first page of reviews; `after` is an offset."""
        self.queries.append(query)
        match = SPAN.search(query)
        if match is None:
            raise AssertionError(query)
        key = (query[: match.start()] + query[match.end() :]).strip()
        first, last = date.fromisoformat(match[1]), date.fromisoformat(match[2])
        matches = [node for day, node in self.dated.get(key, []) if first <= day <= last]
        nodes = []
        for node in matches[offset : offset + 100]:
            pages = self.reviews.get(node.get("id", ""), [{"nodes": []}])
            nodes.append(
                dict(
                    node,
                    reviews={
                        "pageInfo": {"hasNextPage": len(pages) > 1, "endCursor": "c1"},
                        "nodes": pages[0]["nodes"],
                    },
                )
            )
        more = offset + 100 < len(matches)
        return ok(
            {
                "data": {
                    "search": {
                        "issueCount": len(matches),
                        "pageInfo": {"hasNextPage": more, "endCursor": str(offset + 100) if more else None},
                        "nodes": nodes,
                    }
                }
            }
        )


def review(state: str, submitted: str) -> dict[str, str]:
    return {"state": state, "submittedAt": submitted}


def commit(sha: str, when: str) -> dict[str, Any]:
    return {"sha": sha, "commit": {"author": {"date": when}}}


AUTHORED = "org:acme author:octo is:pr created:"
MERGED = "org:acme author:octo is:pr is:merged merged:"
COMMITS = "org:acme author:octo author-date:"
REVIEWED = "org:acme reviewed-by:octo -author:octo is:pr updated:"


def reviews_of(page_info: dict[str, Any], nodes: list[Any], author: object = None) -> tuple[Any, list[Any]]:
    """`_review_dates` over one pull request whose every review page answers `page_info` and `nodes`."""
    connection = {"pageInfo": page_info, "nodes": nodes}
    pull = {"id": "PR_1", "author": author, "reviews": connection}
    search = {"data": {"search": {"issueCount": 1, "pageInfo": {"hasNextPage": False}, "nodes": [pull]}}}
    run, calls = bounded(ok(search), ok({"data": {"node": pull}}))
    client = GitHubSearchClient(run, Recorder())
    try:
        return report._review_dates(client, "acme", "octo", [date(2026, 1, 1)], date(2026, 1, 31), {}), calls
    except GitHubError as exc:
        return exc, calls


class CollectTests(unittest.TestCase):
    def fake(self) -> FakeGitHub:
        github = FakeGitHub()
        github.dated[AUTHORED] = [(date(2026, 3, 15), {"node_id": "PR_a", "created_at": "2026-03-15T10:00:00Z"})]
        github.dated[MERGED] = [
            (date(2026, 5, 2), {"node_id": "PR_a", "pull_request": {"merged_at": "2026-05-02T10:00:00Z"}}),
        ]
        github.dated[COMMITS] = [
            (date(2026, 3, 10), commit("a" * 40, "2026-03-10T12:00:00Z")),
            (date(2026, 3, 31), commit("b" * 40, "2026-03-31T22:30:00-05:00")),
            (date(2026, 3, 10), commit("a" * 40, "2026-03-10T12:00:00Z")),
        ]
        github.dated[REVIEWED] = [
            (date(2026, 4, 10), {"id": "PR_1", "author": {"login": "someone"}}),
            (date(2026, 4, 11), {"id": "PR_self", "author": {"login": "Octo"}}),
            (date(2026, 5, 3), {"id": "PR_2", "author": None}),
        ]
        github.reviews["PR_1"] = [
            {
                "nodes": [
                    review("COMMENTED", "2026-03-02T09:00:00Z"),
                    review("APPROVED", "2026-03-05T09:00:00Z"),
                    review("PENDING", "2026-04-01T09:00:00Z"),
                    review("APPROVED", "2026-04-02T09:00:00Z"),
                    review("APPROVED", "2025-12-31T23:59:00Z"),
                ]
            }
        ]
        github.reviews["PR_2"] = [
            {"nodes": [review("CHANGES_REQUESTED", "2026-05-01T09:00:00Z")]},
            {"nodes": [review("APPROVED", "2026-05-03T09:00:00Z")]},
        ]
        return github

    def collect(self, github: FakeGitHub) -> Activity:
        return collect_activity(GitHubSearchClient(github, Recorder()), "acme", "octo", 3, TODAY)

    def test_every_window_month_is_present_with_zero_defaults(self) -> None:
        activity = self.collect(self.fake())
        self.assertEqual(["2026-03", "2026-04", "2026-05"], activity.months)
        for counts in (
            activity.authored,
            activity.merged,
            activity.commits,
            activity.prs_reviewed,
            activity.reviews_submitted,
        ):
            self.assertEqual(activity.months, list(counts))

    def test_each_category_is_searched_once_for_the_whole_window(self) -> None:
        github = self.fake()
        self.collect(github)
        self.assertEqual(
            [f"{prefix}2026-03-01..2026-05-20" for prefix in (AUTHORED, MERGED, COMMITS, REVIEWED)], github.queries
        )

    def test_pull_requests_bucket_by_creation_and_merge_month(self) -> None:
        activity = self.collect(self.fake())
        self.assertEqual({"2026-03": 1, "2026-04": 0, "2026-05": 0}, activity.authored)
        self.assertEqual({"2026-03": 0, "2026-04": 0, "2026-05": 1}, activity.merged)

    def test_commits_are_deduplicated_and_bucketed_by_utc_author_date(self) -> None:
        activity = self.collect(self.fake())
        self.assertEqual({"2026-03": 1, "2026-04": 1, "2026-05": 0}, activity.commits)

    def test_reviews_count_submissions_and_distinct_pull_requests_per_month(self) -> None:
        activity = self.collect(self.fake())
        self.assertEqual({"2026-03": 2, "2026-04": 1, "2026-05": 2}, activity.reviews_submitted)
        self.assertEqual({"2026-03": 1, "2026-04": 1, "2026-05": 1}, activity.prs_reviewed)
        self.assertEqual(2, activity.prs_reviewed_total)
        self.assertEqual({}, activity.capped)

    def test_self_authored_pull_requests_are_excluded_from_reviews(self) -> None:
        github = self.fake()
        self.collect(github)
        self.assertNotIn("PR_self", github.reviews)
        self.assertTrue(all("-author:octo" in query for query in github.queries if "reviewed-by" in query))

    def test_capped_days_are_recorded_per_column(self) -> None:
        github = self.fake()
        github.dated[COMMITS] += [
            (date(2026, 4, 2), commit(f"{index:040x}", "2026-04-02T00:00:00Z")) for index in range(1001)
        ]
        activity = self.collect(github)
        self.assertEqual({"Commits": ["2026-04-02"]}, activity.capped)
        self.assertEqual(1001, activity.commits["2026-04"])
        self.assertEqual(1, activity.commits["2026-03"])

    def test_unreadable_pull_request_fails_closed(self) -> None:
        github = self.fake()
        original = github.search

        def hide_first(query: str, offset: int) -> CommandResult:
            payload = json.loads(original(query, offset).stdout)
            payload["data"]["search"]["nodes"][0] = {}
            return ok(payload)

        with mock.patch.object(github, "search", hide_first), self.assertRaises(GitHubError) as context:
            self.collect(github)
        self.assertEqual("forbidden", context.exception.kind)

    def test_review_cap_is_reported_for_both_review_columns_across_the_window(self) -> None:
        github = self.fake()
        github.dated[REVIEWED] = [
            (date(2026, 5, 20), {"id": f"PR_{index}", "author": {"login": "someone"}}) for index in range(1200)
        ]
        for index in range(1200):
            github.reviews[f"PR_{index}"] = [{"nodes": [review("APPROVED", "2026-03-15T09:00:00Z")]}]
        activity = self.collect(github)
        self.assertEqual({"Reviews": ["2026-05-20"]}, activity.capped)
        self.assertEqual(1000, activity.reviews_submitted["2026-03"])
        text = render_report(activity, "acme", "octo", TODAY)
        self.assertIn("pull requests last updated on 2026-05-20", text)
        self.assertIn("PRs reviewed and Reviews submitted may be undercounted in every month and in both totals", text)
        self.assertNotIn("Reviews for 2026-05-20", text)

    def test_review_search_splits_and_pages_past_the_cap(self) -> None:
        github = self.fake()
        github.dated[REVIEWED] = [
            (date(2026, 3, 1) + timedelta(days=index % 80), {"id": f"PR_{index}", "author": {"login": "someone"}})
            for index in range(1500)
        ]
        for index in range(1500):
            github.reviews[f"PR_{index}"] = [{"nodes": [review("APPROVED", "2026-04-15T09:00:00Z")]}]
        activity = self.collect(github)
        self.assertEqual(1500, activity.prs_reviewed_total)
        self.assertEqual({}, activity.capped)
        self.assertEqual(
            f"{REVIEWED}2026-03-01..2026-05-20", next(query for query in github.queries if "reviewed-by" in query)
        )

    def test_a_review_timestamp_must_state_its_offset(self) -> None:
        failure, _ = reviews_of({"hasNextPage": False}, [review("APPROVED", "2026-01-31T22:00:00")])
        self.assertIsInstance(failure, GitHubError)
        self.assertEqual("malformed", failure.kind)
        self.assertIn("reviews.nodes[0].submittedAt must be an ISO 8601 timestamp with a UTC offset", str(failure))
        accepted = [review("APPROVED", "2026-01-31T22:00:00Z"), review("COMMENTED", "2026-01-31T22:00:00-05:00")]
        dates, _ = reviews_of({"hasNextPage": False}, accepted)
        self.assertEqual({"PR_1": [date(2026, 1, 31), date(2026, 2, 1)]}, dates)

    def test_a_search_result_timestamp_must_state_its_offset(self) -> None:
        github = self.fake()
        github.dated[AUTHORED] = [(date(2026, 3, 31), {"node_id": "PR_a", "created_at": "2026-03-31T22:00:00"})]
        with self.assertRaises(GitHubError) as context:
            self.collect(github)
        self.assertEqual("malformed", context.exception.kind)
        self.assertIn("created_at must be an ISO 8601 timestamp with a UTC offset", str(context.exception))

    def test_search_results_without_identity_fail_closed(self) -> None:
        github = self.fake()
        github.dated[AUTHORED] = [(date(2026, 3, 15), {"created_at": "2026-03-15T10:00:00Z"})]
        with self.assertRaises(GitHubError) as context:
            self.collect(github)
        self.assertEqual("malformed", context.exception.kind)


def sample_activity(capped: dict[str, list[str]] | None = None) -> Activity:
    months = ["2026-04", "2026-05"]
    return Activity(
        months,
        {"2026-04": 2, "2026-05": 1},
        {"2026-04": 1, "2026-05": 1},
        {"2026-04": 10, "2026-05": 0},
        {"2026-04": 3, "2026-05": 2},
        {"2026-04": 4, "2026-05": 2},
        4,
        capped or {},
    )


class RenderTests(unittest.TestCase):
    def test_table_has_a_row_per_month_and_a_total_row(self) -> None:
        text = render_report(sample_activity(), "acme", "octo", TODAY)
        self.assertIn("| Month | PRs authored | PRs merged | Commits | PRs reviewed | Reviews submitted |", text)
        self.assertIn("| 2026-04 | 2 | 1 | 10 | 3 | 4 |", text)
        self.assertIn("| 2026-05 | 1 | 1 | 0 | 2 | 2 |", text)
        self.assertIn("| **Total** | **3** | **2** | **10** | **4** | **6** |", text)
        self.assertIn("only once in the total", text)
        self.assertIn("All dates and months are UTC", text)
        self.assertIn("Counts cover only acme repositories the current token can read", text)
        self.assertNotIn("WARNING", text)

    def test_cap_warning_appears_only_when_capped(self) -> None:
        text = render_report(sample_activity({"Commits": ["2026-04"]}), "acme", "octo", TODAY)
        self.assertIn("WARNING: Commits for 2026-04 exceeded GitHub's 1000-result Search API cap", text)


def run_report(arguments: list[str], client: GitHubSearchClient | None = None) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = main(arguments, client, TODAY)
        except SystemExit as exit_:
            if not isinstance(exit_.code, int):
                raise AssertionError(f"exit code {exit_.code!r}") from exit_
            code = exit_.code
    return code, stdout.getvalue(), stderr.getvalue()


class MainTests(unittest.TestCase):
    def test_prints_the_report(self) -> None:
        client = GitHubSearchClient(CollectTests().fake(), Recorder())
        code, stdout, _ = run_report(["--org", "acme", "--user", "octo", "--months", "3"], client)
        self.assertEqual(0, code)
        self.assertTrue(stdout.startswith("## GitHub activity for octo in acme"))

    def test_an_enterprise_managed_login_is_reported(self) -> None:
        client = GitHubSearchClient(CollectTests().fake(), Recorder())
        code, stdout, _ = run_report(["--org", "acme", "--user", "mona-lisa_acme", "--months", "3"], client)
        self.assertEqual(0, code)
        self.assertTrue(stdout.startswith("## GitHub activity for mona-lisa_acme in acme"))

    def test_api_errors_print_a_failed_line_and_exit_1(self) -> None:
        run, _ = scripted(failed("gh: HTTP 401: Bad credentials"))
        code, stdout, stderr = run_report(["--org", "acme", "--user", "octo"], GitHubSearchClient(run, Recorder()))
        self.assertEqual((1, "FAILED gh: HTTP 401: Bad credentials [authentication]\n"), (code, stdout))
        self.assertEqual(
            "Querying GitHub for 12 month(s); searches are spaced 2.1s apart.\n",
            stderr,
            "stderr carries only progress, never the failure",
        )

    def test_a_multi_line_failure_is_one_failed_line(self) -> None:
        run, _ = scripted(failed("gh: HTTP 404: Not Found\n(https://api.github.com/search/issues)\n"))
        code, stdout, _ = run_report(["--org", "acme", "--user", "octo"], GitHubSearchClient(run, Recorder()))
        self.assertEqual(
            (1, "FAILED gh: HTTP 404: Not Found (https://api.github.com/search/issues) [not_found]\n"), (code, stdout)
        )

    def test_an_unsearchable_user_fails_with_the_reason_github_gives(self) -> None:
        reason = (
            "The listed users cannot be searched either because the users do not exist or you do not have "
            "permission to view the users."
        )
        body = json.dumps({"message": "Validation Failed", "errors": [{"message": reason, "code": "invalid"}]})
        head = "HTTP/2.0 422 Unprocessable Entity\r\nContent-Type: application/json\r\n\r\n"
        run, _ = scripted(failed("gh: Validation Failed (HTTP 422)\n", head + body))
        code, stdout, _ = run_report(["--org", "acme", "--user", "octo"], GitHubSearchClient(run, Recorder()))
        self.assertEqual((1, f"FAILED gh: Validation Failed (HTTP 422): {reason} [api]\n"), (code, stdout))

    def test_output_survives_a_console_that_cannot_encode_it(self) -> None:
        # A Windows pipe defaults to a legacy code page, and a failure quotes gh's stderr as it came. The child runs
        # the script as a program with gh replaced, so nothing reaches the network.
        script = str(Path(report.__file__).resolve())
        core = str(Path(report.__file__).resolve().parents[2] / "ejryan89-skill-core" / "scripts")
        program = (
            "import runpy, sys\n"
            f"sys.path.insert(0, {core!r})\n"
            "import bounded_process\n"
            "def fake(command, timeout, **options):\n"
            "    stderr = 'gh: HTTP 500: proxy \\u2192 upstream \\u2713'.encode()\n"
            "    return bounded_process.Finished(1, b'', stderr)\n"
            "bounded_process.run_bounded = fake\n"
            f"sys.argv = [{script!r}, '--org', 'acme', '--user', 'octo', '--months', '1']\n"
            f"runpy.run_path({script!r}, run_name='__main__')\n"
        )
        result = subprocess.run(
            [sys.executable, "-B", "-c", program],
            capture_output=True,
            env={**os.environ, "PYTHONIOENCODING": "cp1252"},
            check=False,
        )
        self.assertEqual(1, result.returncode, result.stderr.decode("utf-8", "replace"))
        self.assertEqual(["FAILED gh: HTTP 500: proxy → upstream ✓ [api]"], result.stdout.decode("utf-8").splitlines())


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"total_count": 1}, id="no-items"),
        pytest.param({"items": []}, id="no-total"),
        pytest.param([], id="a-list"),
        pytest.param({"items": [], "total_count": "1"}, id="a-string-total"),
    ],
)
def test_malformed_search_responses_fail_closed(payload: object) -> None:
    client, _ = client_for(scripted(ok(payload))[0])
    with pytest.raises(GitHubError) as context:
        client.search_all("search/issues", "q", KEY)
    assert context.value.kind == "malformed"


COUNTS_REFUSED = [
    pytest.param(True, id="true"),
    pytest.param(False, id="false"),
    pytest.param("1", id="a-string"),
    pytest.param(1.0, id="a-float"),
    pytest.param(-1, id="negative"),
]


@pytest.mark.parametrize("count", COUNTS_REFUSED)
def test_a_search_count_must_be_a_non_negative_integer(count: object) -> None:
    client, _ = client_for(scripted(ok(search_page([], count)))[0])
    with pytest.raises(GitHubError) as context:
        client.search_all("search/issues", "q", KEY)
    assert context.value.kind == "malformed"
    assert "response.total_count must be an integer of at least 0" in str(context.value)


def test_a_search_count_that_is_a_non_negative_integer_is_read() -> None:
    client, _ = client_for(scripted(ok(search_page(rows(1), 1)))[0])
    assert fetch(client) == 1


def graphql_count_page(count: object) -> CommandResult:
    nodes = [{"id": "PR_1"}]
    return ok({"data": {"search": {"issueCount": count, "pageInfo": {"hasNextPage": False}, "nodes": nodes}}})


@pytest.mark.parametrize("count", COUNTS_REFUSED)
def test_a_graphql_search_count_must_be_a_non_negative_integer(count: object) -> None:
    client, _ = client_for(scripted(graphql_count_page(count))[0])
    with pytest.raises(GitHubError) as context:
        client.graphql_search_range("q {span}", "octo", date(2026, 1, 1), date(2026, 1, 31))
    assert context.value.kind == "malformed"
    assert "data.search.issueCount must be an integer of at least 0" in str(context.value)


def test_a_graphql_search_count_that_is_a_non_negative_integer_is_read() -> None:
    client, _ = client_for(scripted(graphql_count_page(1))[0])
    nodes, capped = client.graphql_search_range("q {span}", "octo", date(2026, 1, 1), date(2026, 1, 31))
    assert (len(nodes), capped) == (1, [])


@pytest.mark.parametrize(
    "search",
    [
        pytest.param(None, id="null"),
        pytest.param([], id="a-list"),
        pytest.param({"issueCount": 0, "pageInfo": {"hasNextPage": False}}, id="no-nodes"),
        pytest.param({"issueCount": 0, "nodes": []}, id="no-page-info"),
        pytest.param({"issueCount": 0, "pageInfo": [], "nodes": []}, id="a-list-page-info"),
    ],
)
def test_malformed_graphql_search_responses_fail_closed(search: object) -> None:
    client, _ = client_for(scripted(ok({"data": {"search": search}}))[0])
    with pytest.raises(GitHubError) as context:
        client.graphql_search_range("q {span}", "octo", date(2026, 1, 1), date(2026, 1, 31))
    assert context.value.kind == "malformed"


@pytest.mark.parametrize("value", ["true", 1, None])
def test_incomplete_results_must_be_a_boolean(value: object) -> None:
    run, calls = scripted(ok(dict(search_page([], 0), incomplete_results=value)))
    client, sleeper = client_for(run)
    with pytest.raises(GitHubError) as context:
        fetch(client)
    assert (context.value.kind, len(calls), sleeper.waits) == ("malformed", 1, [])
    assert "response.incomplete_results must be a boolean" in str(context.value)


@pytest.mark.parametrize(
    ("stderr", "kind"),
    [
        pytest.param("gh: HTTP 401: Bad credentials", "authentication", id="bad-credentials"),
        pytest.param("You are not logged into any GitHub hosts", "authentication", id="not-logged-in"),
        pytest.param(
            "gh: Resource protected by organization SAML enforcement (HTTP 403)", "forbidden", id="saml-enforcement"
        ),
        pytest.param("Only the first 1000 search results are available (HTTP 422)", "search_cap", id="search-cap"),
        pytest.param("gh: Validation Failed (HTTP 422)", "api", id="validation-failed"),
        pytest.param("gh: Not Found (HTTP 404)", "not_found", id="not-found"),
        pytest.param(
            "error connecting to api.github.com\ncheck your internet connection or https://githubstatus.com",
            "network",
            id="network",
        ),
    ],
)
def test_failures_are_classified(stderr: str, kind: str) -> None:
    client, sleeper = client_for(scripted(failed(stderr))[0])
    with pytest.raises(GitHubError) as context:
        fetch(client)
    assert kind == context.value.kind
    assert sleeper.waits == []


@pytest.mark.parametrize("request_kind", ["search", "graphql"])
def test_sso_partial_results_fail_closed(request_kind: str) -> None:
    header = "X-Github-Sso: partial-results; organizations=21955855\r\n"
    payload = search_page(rows(1)) if request_kind == "search" else {"data": {"node": {}}}
    client, sleeper = client_for(scripted(ok(payload, header))[0])

    def request() -> object:
        if request_kind == "search":
            return fetch(client)
        return client.graphql("query", {"id": "PR_1"})

    with pytest.raises(GitHubError) as context:
        request()
    assert context.value.kind == "sso_partial"
    assert "21955855" in str(context.value)
    assert sleeper.waits == []


@pytest.mark.parametrize(
    ("message", "page_info"),
    [
        ("reviews.pageInfo.hasNextPage must be a boolean", {"hasNextPage": "false"}),
        ("reviews.pageInfo.endCursor must be a non-empty string", {"hasNextPage": True, "endCursor": 7}),
        (
            "reviews.pageInfo.endCursor must be a cursor not already followed",
            {"hasNextPage": True, "endCursor": "r1"},
        ),
    ],
)
def test_review_page_info_must_be_typed_and_advance(message: str, page_info: dict[str, Any]) -> None:
    failure, calls = reviews_of(page_info, [])
    assert isinstance(failure, GitHubError)
    assert failure.kind == "malformed"
    assert message in str(failure)
    assert len(calls) <= 2


SUBMITTED = {"submittedAt": "2026-01-10T00:00:00Z"}


@pytest.mark.parametrize(
    ("message", "nodes"),
    [
        ("reviews.nodes[0] must be an object, found null", [None, dict(SUBMITTED, state="APPROVED")]),
        ("reviews.nodes[1] must be an object, found string", [dict(SUBMITTED, state="APPROVED"), "x"]),
        ("reviews.nodes[0].state must be a non-empty string, found null", [SUBMITTED]),
        ("reviews.nodes[0].state must be a non-empty string, found integer 5", [dict(SUBMITTED, state=5)]),
    ],
)
def test_a_review_must_be_an_object_with_a_state(message: str, nodes: list[Any]) -> None:
    failure, _ = reviews_of({"hasNextPage": False}, nodes)
    assert isinstance(failure, GitHubError)
    assert failure.kind == "malformed"
    assert message in str(failure)


@pytest.mark.parametrize(
    "author",
    [
        pytest.param({"login": 5}, id="a-number-login"),
        pytest.param({}, id="no-login"),
        pytest.param("octo", id="a-string"),
    ],
)
def test_a_pull_request_author_must_be_an_object_with_a_login(author: object) -> None:
    failure, _ = reviews_of({"hasNextPage": False}, [], author)
    assert isinstance(failure, GitHubError)
    assert failure.kind == "malformed"
    assert "author" in str(failure)


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param(["--org", "acme corp", "--user", "octo"], id="an-org-with-a-space"),
        pytest.param(["--org", "acme", "--user", "octo:repo"], id="a-user-with-a-colon"),
        pytest.param(["--org", "acme", "--user", "o" * 40], id="a-user-of-40-characters"),
        pytest.param(["--org", "acme", "--user", "octo--cat"], id="a-user-with-a-double-hyphen"),
        pytest.param(["--org", "acme", "--user", "octo_"], id="a-user-ending-in-an-underscore"),
        pytest.param(["--org", "-acme", "--user", "octo"], id="an-org-starting-with-a-hyphen"),
        pytest.param(["--org", "acme", "--user", "octo", "--months", "0"], id="zero-months"),
        pytest.param(["--org", "acme", "--user", "octo", "--months", "37"], id="37-months"),
    ],
)
def test_invalid_arguments_are_rejected_before_querying(arguments: list[str]) -> None:
    run, calls = scripted()
    code, _, _ = run_report(arguments, GitHubSearchClient(run, Recorder()))
    assert code == 2
    assert calls == []
