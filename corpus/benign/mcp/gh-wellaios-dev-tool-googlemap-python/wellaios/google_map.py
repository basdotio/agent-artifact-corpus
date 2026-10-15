import os
import requests
import json

from bs4 import BeautifulSoup

# Retrieve the Google API Key from environment variables.
API_KEY = os.environ.get("Goog_Api_Key")

# Define headers for the Google Places API request.
HEADERS = {
    "X-Goog-Api-Key": API_KEY,  # Your Google API key for authentication.
    "Content-Type": "application/json",
    "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.googleMapsLinks",
}

# Define the base URL for the Google Places API text search endpoint.
API = "https://places.googleapis.com/v1/places:searchText"


def find_on_google_map(query: str) -> str:
    """
    Searches for places on Google Maps based on a text query and returns formatted results.

    This function uses the Google Places API (searchText) to find locations.
    For each found place, it also attempts to scrape the Open Graph image URL
    from the Google Maps place URI to get a thumbnail.

    Args:
        query: The text string to search for (e.g., "Eiffel Tower").

    Returns:
        A JSON string representing a list of found places, each containing:
        - "address": The formatted address of the place.
        - "name": The display name of the place.
        - "link": A direct link to directions for the place on Google Maps.
        - "image": A URL to an image of the place, if available (scraped from Google Maps).
        Returns an error message string if the API call fails.
    """
    if API_KEY is None:
        raise Exception("API_KEY is not set")

    # Prepare the data payload for the POST request to the Places API.
    data = {"textQuery": query, "pageSize": 2}

    # Make a POST request to the Google Places API.
    response = requests.post(API, headers=HEADERS, json=data)

    # Check if the API call was successful (status code 200).
    if response.status_code != 200:
        # If not successful, return an error message with the API's response text.
        return f"Error in calling the tool: {response.text}"

    # Parse the JSON response from the Google Places API.
    data = response.json()

    # Initialize an empty list to store the formatted results.
    result = []
    # Iterate through each place found in the API response.
    # The API returns results under the "places" key.
    if "places" not in data:
        # If no places are found, return an empty JSON array.
        return json.dumps([])

    for item in data["places"]:
        # Extract the Google Maps place URI, which is used to get more details (like images)
        # by making another request.
        url = item["googleMapsLinks"]["placeUri"]

        # Define headers for the subsequent GET request to the Google Maps URL.
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        # Make a GET request to the Google Maps place URI.
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        # Parse the HTML content of the Google Maps page using BeautifulSoup.
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract relevant information and format it into a dictionary.
        ret = {
            "address": item["formattedAddress"],  # Formatted address from Places API.
            "name": item["displayName"]["text"],  # Display name from Places API.
            "link": item["googleMapsLinks"][
                "directionsUri"
            ],  # Directions link from Places API.
            # Attempt to find the Open Graph image meta tag and extract its content.
            # This is often used for social media previews and usually contains a relevant image.
            # If not found, set to None.
            "image": soup.find("meta", property="og:image")["content"] if soup.find("meta", property="og:image") else None,  # type: ignore
        }
        # Add the formatted place dictionary to the results list.
        result.append(ret)

    # Convert the list of results into a JSON string and return it.
    return json.dumps(result)
