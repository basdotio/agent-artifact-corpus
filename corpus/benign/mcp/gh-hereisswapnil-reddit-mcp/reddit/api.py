import time
import random
import requests
from collections import defaultdict


class RedditAPI:
    AUTH_URL = "https://www.reddit.com/api/v1/access_token"
    OAUTH_BASE_URL = "https://oauth.reddit.com"
    PUBLIC_BASE_URL = "https://www.reddit.com"

    def __init__(self, client_id=None, client_secret=None, user_agent=None):
        self.client_id = client_id
        self.client_secret = client_secret
        # Reddit requires a descriptive User-Agent to avoid 403 blocks
        # Format: <platform>:<app ID>:<version>
        self.user_agent = user_agent or "python:reddit-mcp-server:v1.0.0"

        self._token = None
        self._token_expiry = 0

        self.use_oauth = bool(client_id and client_secret)

    # -------------------------
    # Auth
    # -------------------------
    def _get_token(self):
        if not self.use_oauth:
            return None

        if self._token and time.time() < self._token_expiry:
            return self._token

        auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)

        headers = {"User-Agent": self.user_agent}
        data = {"grant_type": "client_credentials"}

        res = requests.post(self.AUTH_URL, auth=auth, data=data, headers=headers)
        res.raise_for_status()

        payload = res.json()
        self._token = payload["access_token"]
        self._token_expiry = time.time() + payload["expires_in"] - 60

        return self._token

    def _headers(self):
        headers = {"User-Agent": self.user_agent}
        if self.use_oauth:
            headers["Authorization"] = f"Bearer {self._get_token()}"
        return headers

    def _base_url(self):
        return self.OAUTH_BASE_URL if self.use_oauth else self.PUBLIC_BASE_URL

    def _get(self, path, params=None, max_retries=3):
        if params is None:
            params = {}

        params["raw_json"] = 1

        url = f"{self._base_url()}{path}"

        for attempt in range(max_retries):
            try:
                res = requests.get(
                    url, headers=self._headers(), params=params, timeout=10
                )
                res.raise_for_status()
                return res.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    # Reddit is blocking us, wait and retry with backoff
                    if attempt < max_retries - 1:
                        wait_time = (2**attempt) + random.uniform(0, 1)
                        time.sleep(wait_time)
                        continue
                    else:
                        raise requests.exceptions.HTTPError(
                            "403 Forbidden: Reddit is blocking requests. "
                            "Try using OAuth credentials for better access.",
                            response=e.response,
                        )
                raise
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    continue
                raise

        raise requests.exceptions.RequestException("Max retries exceeded")

    # -------------------------
    # Helpers
    # -------------------------
    def _normalize_posts(self, children):
        posts = []
        for c in children:
            if c.get("kind") != "t3":
                continue
            d = c["data"]
            posts.append(
                {
                    "id": d.get("id"),
                    "title": d.get("title"),
                    "author": d.get("author"),
                    "score": d.get("score", 0),
                    "num_comments": d.get("num_comments", 0),
                    "created_utc": d.get("created_utc"),
                    "permalink": d.get("permalink"),
                    "url": d.get("url"),
                }
            )
        return posts

    # -------------------------
    # MCP Tools
    # -------------------------

    def browse_subreddit(
        self, subreddit, sort="hot", limit=25, after=None, time_filter=None
    ):
        params = {"limit": limit}
        if after:
            params["after"] = after
        if sort == "top" and time_filter:
            params["t"] = time_filter

        data = self._get(f"/r/{subreddit}/{sort}.json", params)
        listing = data["data"]

        return {
            "posts": self._normalize_posts(listing["children"]),
            "next_cursor": listing.get("after"),
        }

    def search_reddit(self, query, subreddit=None, sort="relevance", limit=25):
        params = {
            "q": query,
            "sort": sort,
            "limit": limit,
            "include_over_18": "on",
        }

        if subreddit:
            params["restrict_sr"] = "on"
            path = f"/r/{subreddit}/search.json"
        else:
            path = "/search.json"

        try:
            data = self._get(path, params)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"error": f"Subreddit '{subreddit}' not found.", "posts": []}
            raise

        listing = data["data"]

        return {
            "matched_query": query,
            "posts": self._normalize_posts(listing["children"]),
            "next_cursor": listing.get("after"),
        }

    def get_post_details(self, post_id, max_comments=100):
        try:
            data = self._get(f"/comments/{post_id}.json")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"error": f"Post '{post_id}' not found on Reddit."}
            raise

        post_raw = data[0]["data"]["children"][0]["data"]
        comments_raw = data[1]["data"]["children"]

        comments = []
        count = 0

        def walk(nodes, depth=0):
            nonlocal count
            for n in nodes:
                if count >= max_comments:
                    return
                if n.get("kind") != "t1":
                    continue

                d = n["data"]
                body = d.get("body")
                author = d.get("author")

                if body and author and author != "[deleted]":
                    comments.append(
                        {
                            "id": d["id"],
                            "author": author,
                            "body": body,
                            "score": d.get("score", 0),
                            "depth": depth,
                        }
                    )
                    count += 1

                replies = d.get("replies")
                if isinstance(replies, dict):
                    walk(replies["data"]["children"], depth + 1)

        walk(comments_raw)

        return {
            "post": {
                "title": post_raw.get("title"),
                "author": post_raw.get("author"),
                "score": post_raw.get("score", 0),
                "selftext": post_raw.get("selftext", ""),
                "created_utc": post_raw.get("created_utc"),
            },
            "comments": comments,
        }

    def user_analysis(self, username, limit=50):
        try:
            about = self._get(f"/user/{username}/about.json")["data"]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"error": f"User '{username}' not found on Reddit."}
            raise

        try:
            submitted = self._get(f"/user/{username}/submitted.json", {"limit": limit})[
                "data"
            ]["children"]
        except requests.exceptions.HTTPError:
            submitted = []

        try:
            comments = self._get(f"/user/{username}/comments.json", {"limit": limit})[
                "data"
            ]["children"]
        except requests.exceptions.HTTPError:
            comments = []

        subreddit_counts = defaultdict(int)
        scores = []

        for item in submitted + comments:
            d = item["data"]
            subreddit_counts[d.get("subreddit")] += 1
            scores.append(d.get("score", 0))

        top_subs = sorted(subreddit_counts.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]
        avg_score = sum(scores) / len(scores) if scores else 0

        return {
            "username": username,
            "account_age_days": int((time.time() - about["created_utc"]) / 86400),
            "total_karma": about.get("total_karma", 0),
            "top_subreddits": [
                {"name": name, "count": count} for name, count in top_subs
            ],
            "latest_5_comments": comments[:5],
            "latest_5_posts": submitted[:5],
            "total_posts": len(submitted),
            "total_comments": len(comments),
            "avg_score": round(avg_score, 2),
            "activity_level": "high" if limit >= 50 else "moderate",
        }
