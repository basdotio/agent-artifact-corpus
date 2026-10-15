WEBSITE_URLS = [
    "https://ssl.robocup.org/",
    "https://ssl.robocup.org/tournament-organization/",
    "https://ssl.robocup.org/divisions/",
    "https://ssl.robocup.org/open-source-contributions/",
    "https://ssl.robocup.org/history-of-open-source-submissions/",
    "https://ssl.robocup.org/scientific-publications/",
    "https://ssl.robocup.org/team-description-papers/",
    "https://ssl.robocup.org/history-of-technical-challenges/",
    "https://ssl.robocup.org/match-statistics/",
    "https://ssl.robocup.org/contact/",
    "https://robocup-ssl.github.io/ssl-goals/sslgoals.html",
]
# Keywords to filter out from URLs
WEBSITE_URL_BLACKLIST = [
    "comittee",
    "comittees",
    "qualification",
    "teams",
    "results",
    "rules",
]

WEBSITE_URL_BLACKLIST_REGEX = [
    r"https?:\/\/[^ ]*robocup-\d{4}[^ ]*",
]

INITIAL_RULES_URLS = [
    "https://ssl.robocup.org/rules/",
    "https://robocup-ssl.github.io/ssl-rules/sslrules.html",
    "https://ssl.robocup.org/tournament-rules/",
    "https://ssl.robocup.org/technical-overview-of-the-small-size-league/",
]


# Sitemap URL
DEFAULT_SITEMAP_URL = "https://ssl.robocup.org/page-sitemap.html"

# Data path
DATA_PATH = "data/"

# Output file for processed URLs
URLS_FILE_PATH = DATA_PATH + "processed_urls.txt"

# Full website file path
FULL_WEBSITE_FILE_PATH = DATA_PATH + "full_website.txt"

# Full rules file path
FULL_RULES_FILE_PATH = DATA_PATH + "full_rules.txt"

# Full repository file path
FULL_REPOSITORY_FILE_PATH = DATA_PATH + "full_repository.txt"

# Vector store collection name
VECTOR_STORE_COLLECTION_NAME = "small-size-league-mcp"
