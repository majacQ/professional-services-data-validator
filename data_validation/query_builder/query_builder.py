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

import ibis
from third_party.ibis.ibis_addon import operations


class AggregateField(object):
    def __init__(self, ibis_expr, field_name=None, alias=None):
        """ A representation of a table or column aggregate in Ibis

        Args:
            ibis_expr (ColumnExpr): A column aggregation to use from Ibis
            field_name (String: A field to act on in the table.
                Table level expr do not have a field name
            alias (String): A field to use as the aggregate alias name
        """
        self.expr = ibis_expr
        self.field_name = field_name
        self.alias = alias

    @staticmethod
    def count(field_name=None, alias=None):
        return AggregateField(
            ibis.expr.types.ColumnExpr.count, field_name=field_name, alias=alias,
        )

    @staticmethod
    def min(field_name=None, alias=None):
        return AggregateField(
            ibis.expr.types.ColumnExpr.min, field_name=field_name, alias=alias
        )

    @staticmethod
    def avg(field_name=None, alias=None):
        return AggregateField(
            ibis.expr.types.NumericColumn.mean, field_name=field_name, alias=alias
        )

    @staticmethod
    def max(field_name=None, alias=None):
        return AggregateField(
            ibis.expr.types.ColumnExpr.max, field_name=field_name, alias=alias,
        )

    @staticmethod
    def sum(field_name=None, alias=None):
        return AggregateField(
            ibis.expr.api.NumericColumn.sum, field_name=field_name, alias=alias,
        )

    def compile(self, ibis_table):
        if self.field_name:
            agg_field = self.expr(ibis_table[self.field_name])
        else:
            agg_field = self.expr(ibis_table)

        if self.alias:
            agg_field = agg_field.name(self.alias)

        return agg_field


class FilterField(object):
    def __init__(
        self, ibis_expr, left=None, right=None, left_field=None, right_field=None
    ):
        """ A representation of a query filter to be used while building a query.
            You can alternatively use either (left or left_field) and
            (right or right_field).

        Args:
            ibis_expr (ColumnExpr): A column expression to be used for comparisons (None represents a custom filter).
            left (Object): A value to compare on the left side of the expression
            left_field (String): A column name to be used to filter against
            right (Object): A value to compare on the right side of the expression
            right_field (String): A column name to be used to filter against

        """
        self.expr = ibis_expr
        self.left = left
        self.right = right
        self.left_field = left_field
        self.right_field = right_field

    @staticmethod
    def greater_than(field_name, value):
        # Build Left and Right Objects
        return FilterField(
            ibis.expr.types.ColumnExpr.__gt__, left_field=field_name, right=value
        )

    @staticmethod
    def less_than(field_name, value):
        # Build Left and Right Objects
        return FilterField(
            ibis.expr.types.ColumnExpr.__lt__, left_field=field_name, right=value
        )

    @staticmethod
    def equal_to(field_name, value):
        # Build Left and Right Objects
        return FilterField(
            ibis.expr.types.ColumnExpr.__eq__, left_field=field_name, right=value
        )

    @staticmethod
    def custom(expr):
        """ Returns a FilterField instance built for any custom SQL using a supported operator.

        Args:
            expr (Str): A custom SQL expression used to filter a query.
        """
        return FilterField(None, left=expr)

    def compile(self, ibis_table):
        if self.expr is None:
            return operations.compile_raw_sql(ibis_table, self.left)

        if self.left_field:
            self.left = ibis_table[self.left_field]
            # Cast All Datetime to Date (TODO this may be a bug in BQ)
            if isinstance(
                ibis_table[self.left_field].type(), ibis.expr.datatypes.Timestamp
            ):
                self.left = self.left.cast("date")
        if self.right_field:
            self.right = ibis_table[self.right_field]
            # Cast All Datetime to Date (TODO this may be a bug in BQ)
            if isinstance(
                ibis_table[self.right_field].type(), ibis.expr.datatypes.Timestamp
            ):
                self.right = self.right.cast("date")

        return self.expr(self.left, self.right)


class GroupedField(object):
    def __init__(self, field_name, alias=None, cast=None):
        """ A representation of a group by field used to build a query.

        Args:
            field_name (String): A field to act on in the table
            alias (String): An alias to use for the group
            cast (String): A cast on the column if required
        """
        self.field_name = field_name
        self.alias = alias
        self.cast = cast

    def compile(self, ibis_table):
        # Fields are supplied on compile or on build
        group_field = ibis_table[self.field_name]

        # TODO: generate cast for known types not specified
        if self.cast:
            group_field = group_field.cast(self.cast)
        elif isinstance(group_field.type(), ibis.expr.datatypes.Timestamp):
            group_field = group_field.cast("date")
        else:
            # TODO: need to build Truncation Int support
            # TODO: should be using a logger
            print("WARNING: Unknown cast types can cause memory errors")

        # The Casts require we also supply a name.
        alias = self.alias or self.field_name
        group_field = group_field.name(alias)

        return group_field


class QueryBuilder(object):
    def __init__(self, aggregate_fields, filters, grouped_fields, limit=None):
        """ Build a QueryBuilder object which can be used to build queries easily

        Args:
            aggregate_fields (list[AggregateField]): AggregateField instances with Ibis expressions
            filters (list[FilterField]): A list of FilterField instances
            grouped_fields (list[GroupedField]): A list of GroupedField instances
            limit (int): A limit value for the number of records to pull (used for testing)
        """
        self.aggregate_fields = aggregate_fields
        self.filters = filters
        self.grouped_fields = grouped_fields
        self.limit = limit

    @staticmethod
    def build_count_validator(limit=None):
        """ Return a basic template builder for most validations """
        aggregate_fields = []
        filters = []
        grouped_fields = []

        return QueryBuilder(
            aggregate_fields,
            filters=filters,
            grouped_fields=grouped_fields,
            limit=limit,
        )

    def compile_aggregate_fields(self, table):
        aggs = [field.compile(table) for field in self.aggregate_fields]

        return aggs

    def compile_filter_fields(self, table):
        return [field.compile(table) for field in self.filters]

    def compile_group_fields(self, table):
        return [field.compile(table) for field in self.grouped_fields]

    def compile(self, data_client, schema_name, table_name):
        """ Return an Ibis query object

        Args:
            data_client (IbisClient): The client used to validate the query.
            schema_name (String): The name of the schema for the given table.
            table_name (String): The name of the table to query.
        """
        table = data_client.table(table_name, database=schema_name)

        # Build Query Expressions
        aggs = self.compile_aggregate_fields(table)
        filters = self.compile_filter_fields(table)
        groups = self.compile_group_fields(table)

        query = table.filter(filters)
        query = query.groupby(groups)
        query = query.aggregate(aggs)

        # if groups:
        #     query = table.groupby(groups).aggregate(aggs)
        # else:
        #     query = table.aggregate(aggs)

        if self.limit:
            query = query.limit(self.limit)

        return query

    def add_aggregate_field(self, aggregate_field):
        """ Add an AggregateField instance to the query which
            will be used when compiling your query (ie. SUM(a))

        Args:
            aggregate_field (AggregateField): An AggregateField instance
        """
        self.aggregate_fields.append(aggregate_field)

    def add_grouped_field(self, grouped_field):
        """ Add a GroupedField instance to the query which
            represents adding a column to group by in the
            query being built.

        Args:
            grouped_field (GroupedField): A GroupedField instance
        """
        self.grouped_fields.append(grouped_field)

    def add_filter_field(self, filter_obj):
        """ Add a FilterField instance to your query which
            will add the desired filter to your compiled
            query (ie. WHERE query_filter=True)

        Args:
            filter_obj (FilterField): A FilterField instance
        """
        self.filters.append(filter_obj)
