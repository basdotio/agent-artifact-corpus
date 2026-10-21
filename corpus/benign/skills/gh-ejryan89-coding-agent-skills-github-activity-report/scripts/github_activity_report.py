"""Month-by-month GitHub contribution report for one user in one organization.

Prints the Markdown report on stdout and progress on stderr. A failure prints no table, only the line
`FAILED <reason> [<kind>]` on stdout, and exits 1; an invalid argument exits 2.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ejryan89-skill-core" / "scripts"))

from console import run_main
from flat_text import flat_text
from github_client import (
    Clock,
    CommandResult,
    GitHubClient,
    GitHubError,
    Runner,
    Sleeper,
    graphql_failure,
    json_body,
    subprocess_runner,
)
from github_logins import is_login
from typed_fields import FieldError, FieldReader, describe

T = TypeVar("T")
SEARCH_PAGE_SIZE = 100
SEARCH_RESULT_CAP = 1000
SEARCH_INTERVAL = 2.1
MAX_INTERVAL = 8.0
INTERVAL_GROWTH = 1.5
RECOVERY_STREAK = 10
PAGINATION_PASSES = 3
MAX_MONTHS = 36
READ = FieldReader()

REVIEW_SEARCH_QUERY = """
query($q: String!, $user: String!, $after: String) {
  search(type: ISSUE, query: $q, first: 100, after: $after) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        id
        author { login }
        reviews(author: $user, first: 100) {
          pageInfo { hasNextPage endCursor }
          nodes { state submittedAt }
        }
      }
    }
  }
}
"""

REVIEW_PAGE_QUERY = """
query($id: ID!, $user: String!, $after: String!) {
  node(id: $id) {
    ... on PullRequest {
      id
      reviews(author: $user, first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes { state submittedAt }
      }
    }
  }
}
"""


class SearchPacer:
    """Spaces search requests to stay under GitHub's search rate limits.

    It leaves at least `interval` between the end of one search request and the start of the next, widens the
    interval after each rate-limited attempt, and narrows it again after a run of clean searches.
    """

    def __init__(self, sleeper: Sleeper, clock: Clock) -> None:
        self.sleeper = sleeper
        self.clock = clock
        self.interval = SEARCH_INTERVAL
        self._last_search: float | None = None
        self._clean_searches = 0

    def before(self) -> None:
        if self._last_search is not None:
            remaining = self.interval - (self.clock() - self._last_search)
            if remaining > 0:
                self.sleeper(remaining)

    def after(self, error: GitHubError | None) -> None:
        self._last_search = self.clock()
        if error is None:
            self._clean_searches += 1
            if self._clean_searches >= RECOVERY_STREAK and self.interval > SEARCH_INTERVAL:
                self.interval = max(SEARCH_INTERVAL, self.interval / INTERVAL_GROWTH)
                self._clean_searches = 0
        elif error.kind == "rate_limit":
            self.interval = min(self.interval * INTERVAL_GROWTH, MAX_INTERVAL)
            self._clean_searches = 0


@contextmanager
def _shape_of(response: str) -> Iterator[None]:
    """Fail a field read inside the block as a malformed response, naming the field and what it held."""
    try:
        yield
    except FieldError as exc:
        raise GitHubError(f"{response} has an unexpected shape: {exc}", kind="malformed") from exc


def _search_payload(result: CommandResult) -> dict[str, Any]:
    """A REST search response, retrying one GitHub cut short."""
    with _shape_of("Search response"):
        response = READ.json_object(json_body(result), "response")
        incomplete = READ.boolean(response.get("incomplete_results"), "response.incomplete_results")
    if incomplete:
        raise GitHubError("GitHub search timed out and returned incomplete results", kind="incomplete", retryable=True)
    return response


def _graphql_payload(result: CommandResult) -> Any:
    """A GraphQL response, failing on the errors its body reports."""
    payload = json_body(result)
    problem = graphql_failure(payload)
    if problem is not None:
        raise problem
    return payload


def _next_cursor(page_info: Any, path: str, followed: set[str]) -> str | None:
    """The cursor of the next page a GraphQL connection's `pageInfo` promises, or None on its last page.

    `hasNextPage` must be a boolean and, when it promises a page, `endCursor` a string not already in `followed`, so a
    page that repeats fails instead of paging without end. The cursor is added to `followed`.
    """
    info = READ.json_object(page_info, path)
    if not READ.boolean(info.get("hasNextPage"), f"{path}.hasNextPage"):
        return None
    cursor = READ.string(info.get("endCursor"), f"{path}.endCursor")
    if cursor in followed:
        raise READ.fail(f"{path}.endCursor", "a cursor not already followed", describe(cursor))
    followed.add(cursor)
    return cursor


class GitHubSearchClient:
    """The REST and GraphQL searches the report makes, over ejryan89-skill-core's GitHub CLI client.

    Every request reads the response headers, so GitHub's Retry-After and quota reset set the wait, and a response
    missing results from organizations the token is not SSO-authorized for fails. Searches are also paced.
    """

    def __init__(
        self, runner: Runner = subprocess_runner, sleeper: Sleeper = time.sleep, clock: Clock = time.time
    ) -> None:
        self.github = GitHubClient(runner, sleeper=sleeper, clock=clock)
        self.pacer = SearchPacer(sleeper, clock)

    @property
    def interval(self) -> float:
        return self.pacer.interval

    def _request(self, arguments: list[str], parse: Callable[[CommandResult], T], *, search: bool) -> T:
        return self.github.request(["api", *arguments], parse, headers=True, pacer=self.pacer if search else None)

    def _search_page(self, endpoint: str, query: str, page: int, per_page: int) -> dict[str, Any]:
        response = self._request(
            [f"{endpoint}?q={quote(query, safe='')}&per_page={per_page}&page={page}"], _search_payload, search=True
        )
        with _shape_of(f"Search response for {query!r}"):
            READ.array(response.get("items"), "response.items", READ.json_object)
            READ.integer(response.get("total_count"), "response.total_count", minimum=0)
        return response

    def search_all(
        self, endpoint: str, query: str, key: tuple[str, ...], first: dict[str, Any] | None = None
    ) -> tuple[list[dict[str, Any]], bool]:
        """Fetch every distinct result up to the Search API's 1000-result cap; report whether the cap truncated them.

        A pass that ends with fewer results than GitHub reported means results shifted between pages, so the
        search is repeated from the first page and fails closed if it never comes out complete. Commit search can
        legitimately list one commit in several repositories, so only pull request searches must be distinct.
        """
        repeats_allowed = endpoint == "search/commits"
        for attempt in range(PAGINATION_PASSES):
            payload = (
                first if first is not None and attempt == 0 else self._search_page(endpoint, query, 1, SEARCH_PAGE_SIZE)
            )
            items: list[dict[str, Any]] = []
            page = 1
            while True:
                batch = payload["items"]
                items.extend(batch)
                expected = min(payload["total_count"], SEARCH_RESULT_CAP)
                if len(batch) < SEARCH_PAGE_SIZE or len(items) >= expected:
                    break
                page += 1
                payload = self._search_page(endpoint, query, page, SEARCH_PAGE_SIZE)
            unique = _unique(items, key, "Search")
            found = min(len(items), SEARCH_RESULT_CAP) if repeats_allowed else len(unique)
            if found >= expected:
                return unique[:SEARCH_RESULT_CAP], payload["total_count"] > SEARCH_RESULT_CAP
        raise GitHubError(_shortfall(query, found, expected), kind="incomplete")

    def search_range(
        self, endpoint: str, template: str, start: date, end: date, key: tuple[str, ...]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Search `template` with `{span}` set to start..end, halving the range until each part fits under the cap.

        Returns the items and the spans that still exceeded the cap because they were a single day.
        """
        query = template.replace("{span}", f"{start}..{end}")
        first = self._search_page(endpoint, query, 1, SEARCH_PAGE_SIZE)
        if first["total_count"] > SEARCH_RESULT_CAP and start < end:
            middle = start + (end - start) // 2
            left, left_capped = self.search_range(endpoint, template, start, middle, key)
            right, right_capped = self.search_range(endpoint, template, middle + timedelta(days=1), end, key)
            return left + right, left_capped + right_capped
        items, capped = self.search_all(endpoint, query, key, first)
        return items, [str(start)] if capped else []

    def graphql(self, query: str, variables: dict[str, str], *, search: bool = False) -> dict[str, Any]:
        arguments = ["graphql", "-f", f"query={query}"]
        for name, value in variables.items():
            arguments.extend(["-f", f"{name}={value}"])
        payload = self._request(arguments, _graphql_payload, search=search)
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise GitHubError("GraphQL response has no data", kind="malformed")
        return data

    def _graphql_search_page(self, query: str, user: str, after: str | None) -> dict[str, Any]:
        variables = {"q": query, "user": user}
        if after is not None:
            variables["after"] = after
        data = self.graphql(REVIEW_SEARCH_QUERY, variables, search=True)
        with _shape_of(f"GraphQL search for {query!r}"):
            search = READ.json_object(data.get("search"), "data.search")
            READ.integer(search.get("issueCount"), "data.search.issueCount", minimum=0)
            READ.array(search.get("nodes"), "data.search.nodes")
            READ.json_object(search.get("pageInfo"), "data.search.pageInfo")
        return search

    def graphql_search_range(self, template: str, user: str, start: date, end: date) -> tuple[list[Any], list[str]]:
        """GraphQL counterpart of `search_range`, returning pull request nodes with the user's reviews inline."""
        query = template.replace("{span}", f"{start}..{end}")
        page = self._graphql_search_page(query, user, None)
        if page["issueCount"] > SEARCH_RESULT_CAP and start < end:
            middle = start + (end - start) // 2
            left, left_capped = self.graphql_search_range(template, user, start, middle)
            right, right_capped = self.graphql_search_range(template, user, middle + timedelta(days=1), end)
            return left + right, left_capped + right_capped
        for attempt in range(PAGINATION_PASSES):
            if attempt:
                page = self._graphql_search_page(query, user, None)
            nodes = list(page["nodes"])
            followed: set[str] = set()
            while True:
                with _shape_of(f"GraphQL search for {query!r}"):
                    cursor = _next_cursor(page["pageInfo"], "data.search.pageInfo", followed)
                if cursor is None or len(nodes) >= SEARCH_RESULT_CAP:
                    break
                page = self._graphql_search_page(query, user, cursor)
                nodes.extend(page["nodes"])
            expected = min(page["issueCount"], SEARCH_RESULT_CAP)
            unique = _distinct_pull_requests(nodes)
            if len(unique) >= expected:
                return unique[:SEARCH_RESULT_CAP], [str(start)] if page["issueCount"] > SEARCH_RESULT_CAP else []
        raise GitHubError(_shortfall(query, len(unique), expected), kind="incomplete")


def _shortfall(query: str, found: int, expected: int) -> str:
    return (
        f"Search for {query!r} returned {found} distinct results but GitHub reported {expected} after "
        f"{PAGINATION_PASSES} attempts; results changed during pagination, so rerun the report"
    )


def _distinct_pull_requests(nodes: list[Any]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for node in nodes:
        node_id = node.get("id") if isinstance(node, dict) else None
        if not isinstance(node_id, str):
            raise GitHubError("Review search returned a result that is not a readable pull request", kind="forbidden")
        if node_id not in seen:
            seen.add(node_id)
            unique.append(node)
    return unique


def months_window(today: date, months: int) -> list[date]:
    """First day of each of the last `months` calendar months, ending with today's month."""
    year, month = today.year, today.month
    firsts: list[date] = []
    for _ in range(months):
        firsts.append(date(year, month, 1))
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return list(reversed(firsts))


def month_label(value: date) -> str:
    return f"{value:%Y-%m}"


def _utc_date(value: Any, path: str) -> date:
    """The UTC date of an ISO 8601 timestamp that states its offset or `Z`.

    A timestamp without one is refused: read in the machine's zone, the same text would fall in a different month
    depending on where the report runs.
    """
    expected = "an ISO 8601 timestamp with a UTC offset"
    if not isinstance(value, str):
        raise READ.fail(path, expected, describe(value))
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        raise READ.fail(path, expected, describe(value)) from None
    if moment.utcoffset() is None:
        raise READ.fail(path, expected, describe(value))
    return moment.astimezone(UTC).date()


@dataclass
class Activity:
    months: list[str]
    authored: dict[str, int]
    merged: dict[str, int]
    commits: dict[str, int]
    prs_reviewed: dict[str, int]
    reviews_submitted: dict[str, int]
    prs_reviewed_total: int
    capped: dict[str, list[str]] = field(default_factory=dict)


def _field(item: Any, path: tuple[str, ...]) -> Any:
    value = item
    for key in path:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def _unique(items: list[dict[str, Any]], key: tuple[str, ...], context: str) -> list[dict[str, Any]]:
    """Drop repeats that appear when results shift between pages or a commit exists in several repositories."""
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        identity = _field(item, key)
        if not isinstance(identity, str):
            raise GitHubError(f"{context} search result has no {'.'.join(key)}", kind="malformed")
        if identity not in seen:
            seen.add(identity)
            unique.append(item)
    return unique


def _monthly(
    client: GitHubSearchClient,
    endpoint: str,
    template: str,
    window: list[date],
    today: date,
    date_path: tuple[str, ...],
    key: tuple[str, ...],
    column: str,
    capped: dict[str, list[str]],
) -> dict[str, int]:
    """Count search results per UTC month of the timestamp at `date_path`, searching the whole window at once."""
    counts = {month_label(first): 0 for first in window}
    items, truncated = client.search_range(endpoint, template, window[0], today, key)
    if truncated:
        capped.setdefault(column, []).extend(truncated)
    for item in items:
        with _shape_of(f"{column} result {_field(item, key)}"):
            label = month_label(_utc_date(_field(item, date_path), ".".join(date_path)))
        if label in counts:
            counts[label] += 1
    return counts


def _review_connection(node: Any, node_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """One page of a pull request's reviews and its `pageInfo`. A missing connection means the token cannot read the
    pull request; a review that is not an object is malformed."""
    reviews = node.get("reviews") if isinstance(node, dict) else None
    if (
        not isinstance(reviews, dict)
        or not isinstance(reviews.get("nodes"), list)
        or not isinstance(reviews.get("pageInfo"), dict)
    ):
        raise GitHubError(f"Pull request {node_id} is not readable with this token", kind="forbidden")
    with _shape_of(f"Reviews of pull request {node_id}"):
        return READ.array(reviews["nodes"], "reviews.nodes", READ.json_object), reviews["pageInfo"]


def _submitted_dates(reviews: list[dict[str, Any]], node_id: str) -> list[date]:
    """The submission dates of the reviews that are not pending; a pending review has none yet."""
    dates: list[date] = []
    with _shape_of(f"Reviews of pull request {node_id}"):
        for index, review in enumerate(reviews):
            path = f"reviews.nodes[{index}]"
            if READ.string(review.get("state"), f"{path}.state") != "PENDING":
                dates.append(_utc_date(review.get("submittedAt"), f"{path}.submittedAt"))
    return dates


def _author_login(node: dict[str, Any], node_id: str) -> str | None:
    """The pull request author's login, or None for an author GitHub no longer has, such as a deleted account."""
    with _shape_of(f"Pull request {node_id}"):
        author = READ.optional(READ.json_object, node.get("author"), "author")
        return None if author is None else READ.string(author.get("login"), "author.login")


def _review_dates(
    client: GitHubSearchClient, org: str, user: str, window: list[date], today: date, capped: dict[str, list[str]]
) -> dict[str, list[date]]:
    """Submission dates of the user's non-pending reviews, per pull request someone else authored."""
    template = f"org:{org} reviewed-by:{user} -author:{user} is:pr updated:{{span}}"
    nodes, truncated = client.graphql_search_range(template, user, window[0], today)
    if truncated:
        capped.setdefault("Reviews", []).extend(truncated)
    dates: dict[str, list[date]] = {}
    for node in nodes:
        node_id = node.get("id") if isinstance(node, dict) else None
        if not isinstance(node_id, str):
            raise GitHubError("Review search returned a result that is not a readable pull request", kind="forbidden")
        login = _author_login(node, node_id)
        if node_id in dates or (login is not None and login.casefold() == user.casefold()):
            continue
        reviews, page_info = _review_connection(node, node_id)
        followed: set[str] = set()
        while True:
            with _shape_of(f"Reviews of pull request {node_id}"):
                cursor = _next_cursor(page_info, "reviews.pageInfo", followed)
            if cursor is None:
                break
            data = client.graphql(REVIEW_PAGE_QUERY, {"id": node_id, "user": user, "after": cursor})
            more, page_info = _review_connection(data.get("node"), node_id)
            reviews = reviews + more
        dates[node_id] = _submitted_dates(reviews, node_id)
    return dates


def collect_activity(client: GitHubSearchClient, org: str, user: str, months: int, today: date) -> Activity:
    window = months_window(today, months)
    labels = [month_label(first) for first in window]
    capped: dict[str, list[str]] = {}
    authored = _monthly(
        client,
        "search/issues",
        f"org:{org} author:{user} is:pr created:{{span}}",
        window,
        today,
        ("created_at",),
        ("node_id",),
        "PRs authored",
        capped,
    )
    merged = _monthly(
        client,
        "search/issues",
        f"org:{org} author:{user} is:pr is:merged merged:{{span}}",
        window,
        today,
        ("pull_request", "merged_at"),
        ("node_id",),
        "PRs merged",
        capped,
    )
    commits = _monthly(
        client,
        "search/commits",
        f"org:{org} author:{user} author-date:{{span}}",
        window,
        today,
        ("commit", "author", "date"),
        ("sha",),
        "Commits",
        capped,
    )
    prs_reviewed = dict.fromkeys(labels, 0)
    reviews_submitted = dict.fromkeys(labels, 0)
    reviewed_in_window: set[str] = set()
    for node_id, dates in _review_dates(client, org, user, window, today, capped).items():
        months_touched: set[str] = set()
        for value in dates:
            label = month_label(value)
            if label in reviews_submitted:
                reviews_submitted[label] += 1
                months_touched.add(label)
        for label in months_touched:
            prs_reviewed[label] += 1
        if months_touched:
            reviewed_in_window.add(node_id)
    return Activity(labels, authored, merged, commits, prs_reviewed, reviews_submitted, len(reviewed_in_window), capped)


def render_report(activity: Activity, org: str, user: str, today: date) -> str:
    columns = ("authored", "merged", "commits", "prs_reviewed", "reviews_submitted")
    lines = [
        f"## GitHub activity for {user} in {org}",
        "",
        f"{activity.months[0]} through {today.isoformat()}. "
        "All dates and months are UTC; the current month is partial.",
        "",
        "| Month | PRs authored | PRs merged | Commits | PRs reviewed | Reviews submitted |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for label in activity.months:
        values = " | ".join(str(getattr(activity, column)[label]) for column in columns)
        lines.append(f"| {label} | {values} |")
    totals = [sum(getattr(activity, column).values()) for column in columns]
    totals[3] = activity.prs_reviewed_total
    lines.append(f"| **Total** | {' | '.join(f'**{value}**' for value in totals)} |")
    lines += [
        "",
        "Notes:",
        f"- PRs reviewed counts distinct pull requests {user} reviewed in each month; a pull request reviewed in two "
        "months appears in both, but only once in the total. Reviews submitted counts every submitted review, "
        f"including re-reviews and comment-only reviews. Reviews on {user}'s own pull requests are excluded.",
        f"- Commits counts distinct default-branch commits whose author email is linked to {user}'s account.",
    ]
    lines.append(
        f"- Counts cover only {org} repositories the current token can read; GitHub search omits other "
        "repositories without reporting an error."
    )
    for column, days in sorted(activity.capped.items()):
        if column == "Reviews":
            lines.append(
                "- WARNING: the review search exceeded GitHub's 1000-result Search API cap for pull requests "
                f"last updated on {', '.join(days)}. Their reviews can fall in any month, so PRs reviewed and "
                "Reviews submitted may be undercounted in every month and in both totals."
            )
        else:
            lines.append(
                f"- WARNING: {column} for {', '.join(days)} exceeded GitHub's 1000-result Search API cap; "
                "those counts are lower than the true totals."
            )
    return "\n".join(lines) + "\n"


def _login(value: str) -> str:
    if not is_login(value):
        raise argparse.ArgumentTypeError(f"not a valid GitHub login: {value!r}")
    return value


def _months(value: str) -> int:
    if not value.isdigit() or not 1 <= int(value) <= MAX_MONTHS:
        raise argparse.ArgumentTypeError(f"must be an integer from 1 to {MAX_MONTHS}")
    return int(value)


def main(
    arguments: list[str] | None = None, client: GitHubSearchClient | None = None, today: date | None = None
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", type=_login, required=True)
    parser.add_argument("--user", type=_login, required=True)
    parser.add_argument("--months", type=_months, default=12)
    options = parser.parse_args(arguments)
    current = today or datetime.now(UTC).date()
    print(
        f"Querying GitHub for {options.months} month(s); searches are spaced {SEARCH_INTERVAL}s apart.", file=sys.stderr
    )
    try:
        activity = collect_activity(client or GitHubSearchClient(), options.org, options.user, options.months, current)
    except GitHubError as exc:
        # The reason can carry gh's multi-line stderr; the FAILED line stays one line.
        print(f"FAILED {flat_text(str(exc))} [{exc.kind}]")
        return 1
    sys.stdout.write(render_report(activity, options.org, options.user, current))
    return 0


if __name__ == "__main__":
    run_main(main)
