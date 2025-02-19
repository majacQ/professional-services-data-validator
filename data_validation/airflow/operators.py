# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os

from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from data_validation import data_validation
from data_validation.query_builder import query_builder


class DataValidationCountOperator(BaseOperator):
    """
    Execute a Data Validation run using total count aggregation styles.

    :param source_config: The source configuration object to be used by the Data Validation
    :type source_config: dict
    :param target_config: The target configuration object to be used by the Data Validation
    :type target_config: dict
    :param xcom_push: If xcom_push is True, the last line written to stdout
        will also be pushed to an XCom when the bash command completes.
    :type xcom_push: bool
    :param env: If env is not None, it must be a mapping that defines the
        environment variables for the new process; these are used instead
        of inheriting the current process environment, which is the default
        behavior. (templated)
    :type env: dict
    """

    @apply_defaults
    def __init__(
        self,
        source_config,
        target_config,
        # aggregates,
        # filters,
        env=None,
        xcom_push=False,
        *args,
        **kwargs
    ):
        # TODO add dict with {"agg_function": ("source_field_name", "target_field_name")}

        super(DataValidationCountOperator, self).__init__(*args, **kwargs)
        self.source_config = source_config
        self.target_config = target_config
        self.env = env
        self.xcom_push_flag = xcom_push

    def execute(self, context):
        """
        Execute the bash command in a temporary directory
        which will be cleaned afterwards
        """
        # Prepare env for child process.
        # TODO: why are we passing env, maybe we should assume the os env is correct
        # TODO: do I even need the env?  I don't think so
        env = self.env or {}
        env.update(os.environ)

        # TODO do I need context?
        # airflow_context_vars = context_to_airflow_vars(context, in_env_var_format=True)
        # self.log.debug('Exporting the following env vars:\n%s',
        #                '\n'.join(["{}={}".format(k, v)
        #                           for k, v in airflow_context_vars.items()]))
        # env.update(airflow_context_vars)

        builder = query_builder.QueryBuilder.build_count_validator()
        data_validator = data_validation.DataValidation(
            builder,
            self.source_config,
            self.target_config,
            result_handler=None,
            verbose=False,
        )
        data_validator.execute()

        if False:
            raise AirflowException("An Error Occured")

        if self.xcom_push_flag:
            return {}

    def on_kill(self):
        self.log.info("Sending SIGTERM signal to data validation process")
