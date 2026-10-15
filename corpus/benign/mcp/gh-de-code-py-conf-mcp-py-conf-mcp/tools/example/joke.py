# Mostly copied from smolagents examples

import logging

import requests


LOGGER = logging.getLogger(__name__)


def get_joke() -> str:
    '''
    Fetches a random joke from the JokeAPI.
    This function sends a GET request to the JokeAPI to retrieve a random joke.
    It handles both single jokes and two-part jokes (setup and delivery).
    If the request fails or the response does not contain a joke, an error message is returned.
    Returns:
        str: The joke as a string, or an error message if the joke could not be fetched.
    '''
    url = 'https://v2.jokeapi.dev/joke/Programming?type=single&safe-mode&blacklistFlags=nsfw'
    LOGGER.info('url: %r', url)

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        LOGGER.info('data: %r', data)

        if 'joke' in data:
            return data['joke']
        if 'setup' in data and 'delivery' in data:
            return f'{data['setup']} - {data['delivery']}'
        return 'Error: Unable to fetch joke.'

    except requests.exceptions.RequestException as e:
        return f'Error fetching joke: {str(e)}'
