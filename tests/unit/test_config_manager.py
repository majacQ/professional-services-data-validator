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

import copy
import pytest

from data_validation import consts


SAMPLE_CONFIG = {
    # BigQuery Specific Connection Config
    consts.CONFIG_SOURCE_CONN: {"type": "DNE connection"},
    consts.CONFIG_TARGET_CONN: {"type": "DNE connection"},
    # Validation Type
    consts.CONFIG_TYPE: "Column",
    # Configuration Required Depending on Validator Type
    consts.CONFIG_SCHEMA_NAME: "bigquery-public-data.new_york_citibike",
    consts.CONFIG_TABLE_NAME: "citibike_trips",
    consts.CONFIG_GROUPED_COLUMNS: [],
    consts.CONFIG_RESULT_HANDLER: {
        consts.CONFIG_TYPE: "BigQuery",
        consts.PROJECT_ID: "my-project",
        consts.TABLE_ID: "dataset.table_name",
    },
}

AGGREGATE_CONFIG_A = {
    consts.CONFIG_SOURCE_COLUMN: "a",
    consts.CONFIG_TARGET_COLUMN: "a",
    consts.CONFIG_FIELD_ALIAS: "sum__a",
    consts.CONFIG_TYPE: "sum",
}

GROUPED_COLUMN_CONFIG_A = {
    consts.CONFIG_SOURCE_COLUMN: "a",
    consts.CONFIG_TARGET_COLUMN: "a",
    consts.CONFIG_FIELD_ALIAS: "a",
    consts.CONFIG_CAST: None,
}


class MockIbisClient(object):
    def table(self, table, database=None):
        return MockIbisTable()


class MockIbisTable(object):
    columns = ["a", "b", "c"]

    def __getitem__(self, key):
        return self

    def type(self):
        return "int64"


@pytest.fixture
def module_under_test():
    from data_validation import config_manager

    return config_manager


def test_import(module_under_test):
    """Test import cleanly """
    assert module_under_test is not None


def test_config_property(module_under_test):
    """Test getting config copy."""
    config_manager = module_under_test.ConfigManager(
        SAMPLE_CONFIG, MockIbisClient(), MockIbisClient(), verbose=False
    )

    config = config_manager.config
    assert config == config_manager._config


def test_filters_property(module_under_test):
    config_manager = module_under_test.ConfigManager(
        SAMPLE_CONFIG, MockIbisClient(), MockIbisClient(), verbose=False
    )
    assert config_manager.filters == []


def test_source_connection_property(module_under_test):
    """Test getting config copy."""
    config_manager = module_under_test.ConfigManager(
        SAMPLE_CONFIG, MockIbisClient(), MockIbisClient(), verbose=False
    )
    source_connection = config_manager.source_connection
    assert source_connection == SAMPLE_CONFIG[consts.CONFIG_SOURCE_CONN]


def test_target_connection_property(module_under_test):
    """Test getting config copy."""
    config_manager = module_under_test.ConfigManager(
        SAMPLE_CONFIG, MockIbisClient(), MockIbisClient(), verbose=False
    )
    target_connection = config_manager.target_connection
    assert target_connection == SAMPLE_CONFIG[consts.CONFIG_TARGET_CONN]


def test_process_in_memory(module_under_test):
    """Test getting config copy."""
    config_manager = module_under_test.ConfigManager(
        SAMPLE_CONFIG, MockIbisClient(), MockIbisClient(), verbose=False
    )

    assert config_manager.process_in_memory() is True

    config_manager._config = copy.deepcopy(config_manager._config)
    config_manager._config[consts.CONFIG_TYPE] = "Row"
    assert config_manager.process_in_memory() is False


def test_get_table_info(module_under_test):
    """Test basic handler executes """
    config_manager = module_under_test.ConfigManager(
        SAMPLE_CONFIG, MockIbisClient(), MockIbisClient(), verbose=False
    )

    source_table_spec = "{}.{}".format(
        config_manager.source_schema, config_manager.source_table
    )
    target_table_spec = "{}.{}".format(
        config_manager.target_schema, config_manager.target_table
    )
    expected_table_spec = "{}.{}".format(
        SAMPLE_CONFIG[consts.CONFIG_SCHEMA_NAME],
        SAMPLE_CONFIG[consts.CONFIG_TABLE_NAME],
    )

    assert source_table_spec == expected_table_spec
    assert target_table_spec == expected_table_spec


def test_build_config_grouped_columns(module_under_test):
    config_manager = module_under_test.ConfigManager(
        SAMPLE_CONFIG, MockIbisClient(), MockIbisClient(), verbose=False
    )

    column_configs = config_manager.build_config_grouped_columns(["a"])
    assert column_configs[0] == GROUPED_COLUMN_CONFIG_A


def test_build_config_aggregates(module_under_test):
    config_manager = module_under_test.ConfigManager(
        SAMPLE_CONFIG, MockIbisClient(), MockIbisClient(), verbose=False
    )

    aggregate_configs = config_manager.build_config_column_aggregates("sum", ["a"], [])
    assert aggregate_configs[0] == AGGREGATE_CONFIG_A


def test_build_config_aggregates_no_match(module_under_test):
    config_manager = module_under_test.ConfigManager(
        SAMPLE_CONFIG, MockIbisClient(), MockIbisClient(), verbose=False
    )

    aggregate_configs = config_manager.build_config_column_aggregates(
        "sum", ["a"], ["float64"]
    )
    assert not aggregate_configs


def test_build_config_count_aggregate(module_under_test):
    config_manager = module_under_test.ConfigManager(
        SAMPLE_CONFIG, MockIbisClient(), MockIbisClient(), verbose=False
    )

    agg = config_manager.build_config_count_aggregate()
    assert agg[consts.CONFIG_SOURCE_COLUMN] is None
    assert agg[consts.CONFIG_TARGET_COLUMN] is None
    assert agg[consts.CONFIG_FIELD_ALIAS] == "count"
    assert agg[consts.CONFIG_TYPE] == "count"


def test_get_yaml_validation_block(module_under_test):
    config_manager = module_under_test.ConfigManager(
        SAMPLE_CONFIG, MockIbisClient(), MockIbisClient(), verbose=False
    )
    yaml_config = config_manager.get_yaml_validation_block()
    expected_validation_keys = [
        consts.CONFIG_TYPE,
        consts.CONFIG_SCHEMA_NAME,
        consts.CONFIG_TABLE_NAME,
        consts.CONFIG_GROUPED_COLUMNS,
    ]
    assert yaml_config[consts.CONFIG_TYPE] == SAMPLE_CONFIG[consts.CONFIG_TYPE]
    assert list(yaml_config.keys()) == expected_validation_keys


def test_get_result_handler(module_under_test):
    config_manager = module_under_test.ConfigManager(
        SAMPLE_CONFIG, MockIbisClient(), MockIbisClient(), verbose=False
    )
    handler = config_manager.get_result_handler()

    assert handler._table_id == "dataset.table_name"
