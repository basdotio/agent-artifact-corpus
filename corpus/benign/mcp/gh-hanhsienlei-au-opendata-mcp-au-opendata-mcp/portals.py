from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Portal:
    id: str
    label: str
    api_base: str
    site_url: str


PORTALS: dict[str, Portal] = {
    "data.gov.au": Portal(
        id="data.gov.au",
        label="data.gov.au (Australian Government)",
        api_base="https://data.gov.au/data/api/3/action",
        site_url="https://data.gov.au",
    ),
    "data.sa.gov.au": Portal(
        id="data.sa.gov.au",
        label="data.sa.gov.au (South Australian Government)",
        api_base="https://data.sa.gov.au/data/api/3/action",
        site_url="https://data.sa.gov.au",
    ),
}


def get_portal(portal_id: str) -> Portal:
    try:
        return PORTALS[portal_id]
    except KeyError:
        raise ValueError(
            f"unknown portal {portal_id!r}; valid portals are: {', '.join(sorted(PORTALS))}"
        ) from None


def all_portals() -> list[Portal]:
    return list(PORTALS.values())
