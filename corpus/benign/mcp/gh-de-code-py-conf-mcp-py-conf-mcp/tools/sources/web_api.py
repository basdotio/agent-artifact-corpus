import json
import logging
import os
from pathlib import Path
from typing import Any, Mapping, Optional, TypedDict

import jinja2
import requests
import requests.auth

from py_conf_mcp.tools.typing import ToolClass


LOGGER = logging.getLogger(__name__)


def get_requests_session() -> requests.Session:
    return requests.Session()


def read_secret_from_env(var_name: str) -> str:
    path = os.environ[var_name]
    return Path(path).read_text(encoding='utf-8')


def get_evaluated_template(template: str, variables: Mapping[str, Any]) -> Any:
    compiled_template = jinja2.Template(template)
    compiled_template.globals['read_secret_from_env'] = read_secret_from_env
    return compiled_template.render(variables)


def get_evaluated_query_parameters(
    query_parameters: Mapping[str, Any],
    variables: Mapping[str, Any]
) -> Mapping[str, Any]:
    return {
        key: get_evaluated_template(value, variables)
        for key, value in query_parameters.items()
    }


def get_optional_evaluated_json_body(
    json_template: Optional[str],
    variables: Mapping[str, Any]
) -> Optional[Any]:
    if json_template is None:
        return None
    return json.loads(get_evaluated_template(json_template, variables))


class BasicAuthConfig(TypedDict):
    username: str
    password: str


def get_requests_auth(
    basic_auth: Optional[BasicAuthConfig]
) -> Optional[requests.auth.HTTPBasicAuth]:
    if not basic_auth:
        return None
    variables = {
        'env': os.environ
    }
    return requests.auth.HTTPBasicAuth(
        username=get_evaluated_template(
            basic_auth['username'],
            variables=variables
        ),
        password=get_evaluated_template(
            basic_auth['password'],
            variables=variables
        )
    )


class WebApiTool(ToolClass):  # pylint: disable=too-many-instance-attributes
    def __init__(  # pylint: disable=too-many-arguments
        self,
        url: str,
        *,
        query_parameters: Optional[Mapping[str, str]] = None,
        json_template: Optional[str] = None,
        response_template: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
        method: str = 'GET',
        verify_ssl: bool = True,
        basic_auth: Optional[BasicAuthConfig] = None
    ):
        super().__init__()
        self.url = url
        self.query_parameters = query_parameters or {}
        self.json_template = json_template
        self.response_template = response_template
        self.method = method
        self.verify_ssl = verify_ssl
        self.headers = headers
        self.auth = get_requests_auth(basic_auth)

    def __call__(self, **kwargs):
        session = get_requests_session()
        url = get_evaluated_template(self.url, kwargs)
        params = get_evaluated_query_parameters(
            self.query_parameters,
            kwargs
        )
        json_body = get_optional_evaluated_json_body(
            self.json_template,
            kwargs
        )
        LOGGER.info(
            'url: %r (method: %r, params: %r, kwargs: %r, has_json_body: %r)',
            url, self.method, params, kwargs, bool(json_body)
        )
        LOGGER.info('json_body: %r', json_body)
        response = session.request(
            method=self.method,
            url=url,
            params=params,
            headers=self.headers,
            auth=self.auth,
            verify=self.verify_ssl,
            json=json_body
        )
        response.raise_for_status()
        response_json = response.json()
        if not self.response_template:
            LOGGER.info('response_json: %r', response_json)
            return response_json
        response_content = get_evaluated_template(
            self.response_template,
            variables={
                'response_json': response_json,
                'params': params
            }
        )
        LOGGER.info('response_content after template: %r', response_content)
        return response_content
