import logging
from typing import Any, Iterable, Mapping, Sequence

from google.cloud import bigquery
from google.cloud.bigquery.table import RowIterator
import jinja2

from py_conf_mcp.tools.typing import ToolClass
from py_conf_mcp.utils.json import get_json_as_csv_lines


LOGGER = logging.getLogger(__name__)


def toquoted(value: str) -> str:
    if value is None:
        raise ValueError('value must not be none')
    return "'" + value.replace("'", "\\'") + "'"


def get_evaluated_template(template: str, variables: Mapping[str, Any]) -> Any:
    env = jinja2.Environment()
    env.filters['toquoted'] = toquoted
    compiled_template = env.from_string(template)
    return compiled_template.render(variables)


def get_bq_client(project_name: str) -> bigquery.Client:
    return bigquery.Client(project=project_name)


def get_bq_result_from_bq_query(
    project_name: str,
    query: str,
    query_parameters: Sequence[Any] | None = tuple()
) -> RowIterator:
    client = get_bq_client(project_name=project_name)
    job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
    query_job = client.query(query, job_config=job_config)  # Make an API request.
    bq_result = query_job.result()  # Waits for query to finish
    LOGGER.debug('bq_result: %r', bq_result)
    return bq_result


def iter_dict_from_bq_query(
    project_name: str,
    query: str,
    query_parameters: Sequence[Any] | None = tuple()
) -> Iterable[dict]:
    bq_result = get_bq_result_from_bq_query(
        project_name=project_name,
        query=query,
        query_parameters=query_parameters
    )
    for row in bq_result:
        LOGGER.debug('row: %r', row)
        yield dict(row.items())


class BigQueryTool(ToolClass):  # pylint: disable=too-many-instance-attributes
    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        project_name: str,
        sql_query: str,
        is_sql_query_template: bool = True,
        output_format: str = 'json'
    ):
        super().__init__()
        self.project_name = project_name
        self.sql_query = sql_query
        self.is_sql_query_template = is_sql_query_template
        self.output_format = output_format

    def __call__(self, **kwargs):
        sql_query = self.sql_query
        if self.is_sql_query_template:
            sql_query = get_evaluated_template(
                sql_query,
                variables=kwargs
            )
        try:
            LOGGER.info('Running BigQuery SQL:\n```sql\n%s\n```', sql_query)
            result: Any = list(iter_dict_from_bq_query(
                project_name=self.project_name,
                query=sql_query
            ))
            if self.output_format == 'csv':
                result = '\n'.join(get_json_as_csv_lines(result))
            LOGGER.info('query results: %r', result)
        except Exception as exc:
            LOGGER.warning('Failed to run BigQuery SQL due to %r', exc, exc_info=True)
            raise
        return result
