"""HeadHunter API Client.

This module provides a client for interacting with the HeadHunter job search API.
The client supports both public API endpoints (for searching vacancies and
retrieving public information) and authenticated endpoints (for managing user
resumes and applications via OAuth).

The client handles:
    - Vacancy search with various filters and pagination
    - Detailed vacancy and employer information retrieval
    - Similar vacancies discovery
    - Reference data access (areas, dictionaries)
    - OAuth authentication and token management
    - User operations (applications, resumes) with proper authentication
    - Automatic token refresh for authenticated requests

Authentication:
    The client supports two types of authentication:
    1. App token authentication for public API calls
    2. OAuth access token authentication for user-specific operations

Required environment variables:
    - HH_CLIENT_ID: OAuth client ID (for authentication)
    - HH_CLIENT_SECRET: OAuth client secret (for authentication)
    - HH_APP_TOKEN: Application token for public API calls (optional)
    - HH_REDIRECT_URI: OAuth redirect URI (for authentication)
    - HH_ACCESS_TOKEN: User access token (optional, for authenticated calls)
    - HH_REFRESH_TOKEN: Refresh token (optional, for token renewal)
"""

import httpx
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta


class HHClient:
    """HeadHunter API client for job search and application management.

    This client provides a comprehensive interface to the HeadHunter API,
    supporting both public operations (vacancy search, employer information)
    and authenticated operations (resume management, job applications).

    The client automatically handles authentication headers, token management,
    and provides convenient methods for all supported HeadHunter API endpoints.

    Attributes:
        BASE_URL (str): Base URL for HeadHunter API endpoints
        client_id (str): OAuth client ID from environment variables
        client_secret (str): OAuth client secret from environment variables
        app_token (str): Application token for public API calls
        redirect_uri (str): OAuth redirect URI from environment variables
        access_token (str): Current user access token for authenticated calls
        refresh_token (str): Refresh token for automatic token renewal
        token_expires_at (datetime): Expiration time for the current access token
    """

    BASE_URL = "https://api.hh.ru"

    def __init__(self):
        """Initialize the HeadHunter client with configuration from environment variables.

        Loads OAuth credentials, tokens, and other configuration from environment
        variables. The client can work in two modes:
        1. Public mode: Using app token for public API calls
        2. Authenticated mode: Using access token for user-specific operations

        Environment variables loaded:
            - HH_CLIENT_ID: OAuth client ID
            - HH_CLIENT_SECRET: OAuth client secret
            - HH_APP_TOKEN: Application token for public calls
            - HH_REDIRECT_URI: OAuth redirect URI
            - HH_ACCESS_TOKEN: User access token (optional)
            - HH_REFRESH_TOKEN: Refresh token for token renewal (optional)
        """
        self.client_id = os.getenv("HH_CLIENT_ID")
        self.client_secret = os.getenv("HH_CLIENT_SECRET")
        self.app_token = os.getenv("HH_APP_TOKEN")
        self.redirect_uri = os.getenv("HH_REDIRECT_URI")
        self.access_token: Optional[str] = os.getenv("HH_ACCESS_TOKEN")
        self.refresh_token: Optional[str] = os.getenv("HH_REFRESH_TOKEN")
        self.token_expires_at: Optional[datetime] = None

    def _get_headers(self, authenticated: bool = False) -> Dict[str, str]:
        """Generate HTTP headers for HeadHunter API requests.

        Creates appropriate headers including User-Agent and authorization
        based on the authentication mode. Uses either OAuth access token
        for authenticated requests or app token for public requests.

        Args:
            authenticated (bool): Whether to use authenticated headers with
                access token. If False, uses app token for public API calls.
                Defaults to False.

        Returns:
            Dict[str, str]: Dictionary containing HTTP headers including:
                - User-Agent: Required by HeadHunter API
                - HH-User-Agent: Application identifier
                - Authorization: Bearer token (access token or app token)
        """
        headers = {
            "User-Agent": "JobHunter/1.0 (jhunterpro.ru)",
            "HH-User-Agent": "JobHunter/1.0 (jhunterpro.ru)",
        }

        if authenticated and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        elif not authenticated and self.app_token:
            headers["Authorization"] = f"Bearer {self.app_token}"

        return headers

    async def search_vacancies(
        self,
        text: Optional[str] = None,
        area: Optional[int] = None,
        experience: Optional[str] = None,
        employment: Optional[str] = None,
        schedule: Optional[str] = None,
        salary: Optional[int] = None,
        only_with_salary: bool = False,
        per_page: int = 20,
        page: int = 0,
    ) -> Dict[str, Any]:
        """Search for job vacancies with various filters.

        Performs a search for job vacancies on HeadHunter with optional filtering
        by location, experience level, employment type, schedule, salary, and more.
        Supports pagination for handling large result sets.

        This is a public API method that doesn't require authentication.

        Args:
            text (Optional[str]): Search query text (job title, keywords, skills).
                Can include company names, technologies, etc.
            area (Optional[int]): Region ID for location filtering.
                Use get_areas() to find available region IDs.
                Examples: 1=Moscow, 2=St.Petersburg, 113=Russia.
            experience (Optional[str]): Required experience level.
                Valid values: "noExperience", "between1And3", "between3And6", "moreThan6".
            employment (Optional[str]): Employment type.
                Valid values: "full", "part", "project", "volunteer", "probation".
            schedule (Optional[str]): Work schedule type.
                Valid values: "fullDay", "shift", "flexible", "remote", "flyInFlyOut".
            salary (Optional[int]): Minimum salary filter in rubles.
            only_with_salary (bool): If True, show only vacancies with specified salary.
                Defaults to False.
            per_page (int): Number of results per page (max 100). Defaults to 20.
            page (int): Page number for pagination (0-indexed). Defaults to 0.

        Returns:
            Dict[str, Any]: Search results containing:
                - found (int): Total number of matching vacancies
                - items (List[Dict]): List of vacancy objects with basic info
                - pages (int): Total number of pages available
                - per_page (int): Results per page
                - page (int): Current page number

        Raises:
            httpx.HTTPError: If the API request fails or returns an error status.
        """
        params = {
            "text": text,
            "area": area,
            "experience": experience,
            "employment": employment,
            "schedule": schedule,
            "salary": salary,
            "only_with_salary": only_with_salary,
            "per_page": per_page,
            "page": page,
        }
        params = {k: v for k, v in params.items() if v is not None}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/vacancies", params=params, headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def get_vacancy(self, vacancy_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific vacancy.

        Retrieves comprehensive information about a job vacancy including
        description, requirements, salary, employer details, and other metadata.

        This is a public API method that doesn't require authentication.

        Args:
            vacancy_id (str): The unique identifier of the vacancy to retrieve.
                Can be obtained from search results.

        Returns:
            Dict[str, Any]: Detailed vacancy information including:
                - id (str): Vacancy ID
                - name (str): Vacancy title
                - description (str): Full job description (HTML)
                - employer (Dict): Employer/company information
                - salary (Dict): Salary range and currency
                - area (Dict): Location information
                - experience (Dict): Required experience level
                - employment (Dict): Employment type
                - schedule (Dict): Work schedule
                - key_skills (List[Dict]): Required skills
                - alternate_url (str): Web URL for the vacancy

        Raises:
            httpx.HTTPError: If the vacancy doesn't exist or API request fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/vacancies/{vacancy_id}", headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def get_employer(self, employer_id: str) -> Dict[str, Any]:
        """Get detailed information about an employer/company.

        Retrieves comprehensive information about a company including
        description, industry, location, website, and other details.

        This is a public API method that doesn't require authentication.

        Args:
            employer_id (str): The unique identifier of the employer.
                Can be obtained from vacancy data or search results.

        Returns:
            Dict[str, Any]: Detailed employer information including:
                - id (str): Employer ID
                - name (str): Company name
                - description (str): Company description
                - site_url (str): Company website URL
                - area (Dict): Company location
                - industries (List[Dict]): Company industries
                - type (str): Company type (agency, employer, etc.)
                - logo_urls (Dict): Company logo URLs in different sizes
                - alternate_url (str): HeadHunter page URL for the employer

        Raises:
            httpx.HTTPError: If the employer doesn't exist or API request fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/employers/{employer_id}", headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def get_similar_vacancies(self, vacancy_id: str) -> Dict[str, Any]:
        """Get similar vacancies for a specific vacancy.

        Retrieves a list of job vacancies that are similar to the specified
        vacancy based on HeadHunter's recommendation algorithm.

        This is a public API method that doesn't require authentication.

        Args:
            vacancy_id (str): The unique identifier of the reference vacancy
                for which to find similar positions.

        Returns:
            Dict[str, Any]: Similar vacancies data containing:
                - items (List[Dict]): List of similar vacancy objects with:
                    - id (str): Vacancy ID
                    - name (str): Vacancy title
                    - employer (Dict): Basic employer information
                    - area (Dict): Location information
                    - alternate_url (str): Web URL for the vacancy

        Raises:
            httpx.HTTPError: If the vacancy doesn't exist or API request fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/vacancies/{vacancy_id}/similar_vacancies",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def get_areas(self) -> List[Dict[str, Any]]:
        """Get list of all available regions/areas for filtering.

        Retrieves the hierarchical list of all geographical areas available
        on HeadHunter. This includes countries, regions, cities, and districts
        with their unique IDs that can be used for vacancy filtering.

        This is a public API method that doesn't require authentication.

        Returns:
            List[Dict[str, Any]]: List of area objects in hierarchical structure:
                - id (str): Area ID for use in search filters
                - name (str): Area name (e.g., "Moscow", "Russia")
                - areas (List[Dict]): Sub-areas (cities within regions, etc.)

            Common area IDs:
                - 1: Moscow
                - 2: St. Petersburg
                - 113: Russia (all regions)

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/areas", headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    async def get_dictionaries(self) -> Dict[str, Any]:
        """Get all filter dictionaries from HeadHunter.

        Retrieves all reference dictionaries used for filtering vacancies,
        including experience levels, employment types, work schedules,
        industries, and other categorization data.

        This is a public API method that doesn't require authentication.

        Returns:
            Dict[str, Any]: Dictionary containing all filter categories:
                - experience (List[Dict]): Experience level options
                    ("noExperience", "between1And3", etc.)
                - employment (List[Dict]): Employment type options
                    ("full", "part", "project", etc.)
                - schedule (List[Dict]): Work schedule options
                    ("fullDay", "remote", "flexible", etc.)
                - industries (List[Dict]): Industry categories
                - currency (List[Dict]): Available currencies
                - education_level (List[Dict]): Education requirements
                - language (List[Dict]): Language requirements
                - And other categorical data used in vacancy filtering

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/dictionaries", headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

    def set_tokens(self, access_token: str, refresh_token: str, expires_in: int):
        """Set OAuth tokens and calculate expiration time.

        Updates the client's authentication tokens and calculates the
        expiration time for the access token. This method is typically
        called after successful OAuth authentication or token refresh.

        Args:
            access_token (str): OAuth access token for authenticated API calls.
            refresh_token (str): Refresh token for renewing expired access tokens.
            expires_in (int): Token lifetime in seconds from now.
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

    async def refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token.

        Attempts to refresh the OAuth access token using the stored refresh token.
        If successful, updates the client's tokens and expiration time.

        This method is useful for maintaining authentication when the access
        token expires, avoiding the need for full re-authentication.

        Returns:
            bool: True if token refresh was successful and new tokens were set,
                False if refresh failed (no refresh token or API error).

        Note:
            Requires a valid refresh token to be set in the client.
            If refresh fails, the user will need to re-authenticate via OAuth.
        """
        if not self.refresh_token:
            return False

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://hh.ru/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
                headers=self._get_headers(),
            )

            if response.status_code == 200:
                data = response.json()
                self.set_tokens(
                    data["access_token"], data["refresh_token"], data["expires_in"]
                )
                return True
        return False

    async def apply_to_vacancy(
        self, vacancy_id: str, resume_id: str, letter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit a job application to a specific vacancy.

        Submits an application for a job vacancy using one of the user's
        resumes. Optionally includes a cover letter with the application.

        This method requires OAuth authentication. The user must have
        authorized the application and have a valid access token.

        Args:
            vacancy_id (str): The unique identifier of the vacancy to apply to.
                Must be a valid, active vacancy ID.
            resume_id (str): The ID of the user's resume to use for the application.
                Must be one of the user's own resumes.
            letter (Optional[str]): Cover letter text to include with the
                application. Optional but recommended for better results.

        Returns:
            Dict[str, Any]: Application response containing:
                - id (str): Application/negotiation ID
                - created_at (str): Application submission timestamp
                - updated_at (str): Last update timestamp
                - state (Dict): Application status information
                - vacancy (Dict): Applied vacancy basic information

        Raises:
            Exception: If no access token is available (authentication required).
            httpx.HTTPError: If the application fails (vacancy not found,
                resume not accessible, already applied, etc.).
        """
        if not self.access_token:
            raise Exception("Authentication required. User must authorize via OAuth.")

        data = {"vacancy_id": vacancy_id, "resume_id": resume_id}
        if letter:
            data["letter"] = letter

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/negotiations",
                json=data,
                headers=self._get_headers(authenticated=True),
            )
            response.raise_for_status()
            return response.json()

    async def get_negotiations(
        self, per_page: int = 20, page: int = 0
    ) -> Dict[str, Any]:
        """Get user's application history and status.

        Retrieves a paginated list of all job applications (negotiations)
        submitted by the authenticated user, including their current status
        and related vacancy information.

        This method requires OAuth authentication. The user must have
        authorized the application and have a valid access token.

        Args:
            per_page (int): Number of applications to return per page (max 100).
                Defaults to 20.
            page (int): Page number for pagination (0-indexed). Defaults to 0.

        Returns:
            Dict[str, Any]: Applications data containing:
                - found (int): Total number of user's applications
                - items (List[Dict]): List of application objects with:
                    - id (str): Application ID
                    - created_at (str): Application submission date
                    - state (Dict): Current application status
                    - vacancy (Dict): Applied vacancy information
                - pages (int): Total number of pages available
                - per_page (int): Results per page
                - page (int): Current page number

        Raises:
            Exception: If no access token is available (authentication required).
            httpx.HTTPError: If the API request fails.
        """
        if not self.access_token:
            raise Exception("Authentication required.")

        params = {"per_page": per_page, "page": page}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/negotiations",
                params=params,
                headers=self._get_headers(authenticated=True),
            )
            response.raise_for_status()
            return response.json()

    async def get_resumes(self) -> Dict[str, Any]:
        """Get list of user's resumes.

        Retrieves all resumes belonging to the authenticated user,
        including their status, title, publication status, and basic metadata.

        This method requires OAuth authentication. The user must have
        authorized the application and have a valid access token.

        Returns:
            Dict[str, Any]: User's resumes data containing:
                - items (List[Dict]): List of resume objects with:
                    - id (str): Resume ID
                    - title (str): Resume title
                    - status (Dict): Publication status information
                    - updated_at (str): Last update timestamp
                    - created_at (str): Creation timestamp
                    - views_count (int): Number of views by employers
                    - url (str): Direct resume URL

        Raises:
            Exception: If no access token is available (authentication required).
            httpx.HTTPError: If the API request fails.
        """
        if not self.access_token:
            raise Exception("Authentication required.")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/resumes/mine",
                headers=self._get_headers(authenticated=True),
            )
            response.raise_for_status()
            return response.json()

    async def get_resume(self, resume_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific resume.

        Retrieves comprehensive information about a user's resume including
        personal information, experience, education, skills, and other details.

        This method requires OAuth authentication. The user must have
        authorized the application and have a valid access token.

        Args:
            resume_id (str): The unique identifier of the resume to retrieve.
                Must be one of the user's own resumes.

        Returns:
            Dict[str, Any]: Detailed resume information including:
                - id (str): Resume ID
                - title (str): Resume title
                - status (Dict): Publication status information
                - experience (List[Dict]): Work experience entries
                - education (List[Dict]): Education entries
                - skills (str): Skills description
                - contact (List[Dict]): Contact information
                - personal (Dict): Personal information
                - updated_at (str): Last update timestamp
                - created_at (str): Creation timestamp
                - views_count (int): Number of views by employers

        Raises:
            Exception: If no access token is available (authentication required).
            httpx.HTTPError: If the resume doesn't exist, is not accessible,
                or API request fails.
        """
        if not self.access_token:
            raise Exception("Authentication required.")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/resumes/{resume_id}",
                headers=self._get_headers(authenticated=True),
            )
            response.raise_for_status()
            return response.json()
