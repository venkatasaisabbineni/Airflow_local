from datetime import datetime, timedelta
from airflow.utils.dates import days_ago

from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python import PythonOperator

import csv

default_args = {
   'owner': 'loonycorn'
}


def saving_to_csv(ti):
    filter_data = ti.xcom_pull(task_ids='filtering_customers')

    with open('/Users/venkatasaisabbineni/Desktop/Airflow_local/output/filtered_customer_data.csv', 
              'w', newline='') as file:

        writer = csv.writer(file)

        writer.writerow(['Name', 'Product', 'Price'])

        for row in filter_data:
            writer.writerow(row)

with DAG(
    dag_id = 'postgres_pipeline',
    description = 'Running a pipeline using the Postgres operator',
    default_args = default_args,
    start_date = days_ago(1),
    schedule_interval = '@once',
    tags = ['operator', 'postgres'],
    template_searchpath = '/Users/venkatasaisabbineni/Desktop/Airflow_local/sql_statements'
) as dag:

    create_table_customers = PostgresOperator(
        task_id = 'create_table_customers',
        postgres_conn_id = 'postgres_connection',
        sql = 'create_table_customers.sql'
    )

    create_table_customer_purchases = PostgresOperator(
        task_id = 'create_table_customer_purchases',
        postgres_conn_id = 'postgres_connection',
        sql = 'create_table_customer_purchases.sql'
    )

    insert_customers = PostgresOperator(
        task_id = 'insert_customers',
        postgres_conn_id = 'postgres_connection',
        sql = 'insert_customers.sql'
    )

    insert_customer_purchases = PostgresOperator(
        task_id = 'insert_customer_purchases',
        postgres_conn_id = 'postgres_connection',
        sql = 'insert_customer_purchases.sql'
    )


    joining_table = PostgresOperator(
        task_id = 'joining_table',
        postgres_conn_id = 'postgres_connection',
        sql = 'joining_table.sql'
    )

    filtering_customers = PostgresOperator(
        task_id = 'filtering_customers',
        postgres_conn_id = 'postgres_connection',
        sql='''
            SELECT name, product, price
            FROM complete_customer_details
            WHERE name = ANY(%(names)s)
        ''',
        parameters={'names': ['Kiele West', 'Koma Day-Lewis']}
    )

    saving_to_csv = PythonOperator(
        task_id='saving_to_csv',
        python_callable=saving_to_csv
    )


    create_table_customers >> create_table_customer_purchases >> \
        insert_customers >> insert_customer_purchases >> \
        joining_table >> filtering_customers >> saving_to_csv








