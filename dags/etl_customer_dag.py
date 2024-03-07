from datetime import datetime, timedelta
from airflow.utils.dates import days_ago
from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.amazon.aws.transfers.s3_to_redshift import S3ToRedshiftOperator
import csv
import pandas as pd
from io import StringIO

default_args = {
   'owner': 'Venkata'
}

def read_s3_file(bucket_name, file_key):
    s3_hook = S3Hook(aws_conn_id='aws_conn_s3')
    file_content = s3_hook.read_key(bucket_name=bucket_name, key=file_key)
    if isinstance(file_content, bytes):
        file_content = file_content.decode('utf-8')
    df = pd.read_csv(StringIO(file_content))
    return df.to_json()

def remove_null_values(json_data):
    df = pd.read_json(json_data)
    df = df.dropna()
    df.to_csv('/Users/venkatasaisabbineni/Desktop/Airflow_local/output/transformed_customer_data.csv',index = False)
    return df.to_json()

def saving_to_csv(ti):
    extract_data = ti.xcom_pull(task_ids='extract_customers')
    with open('/Users/venkatasaisabbineni/Desktop/Airflow_local/output/customer_data.csv', 
              'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['ID', 'Name', 'Email', 'Credit_Card_Number', 'Credit_Card_Type'])
        for row in extract_data:
            writer.writerow(row)

def upload_to_s3(filename, key, bucket_name):
    hook = S3Hook(aws_conn_id = 'aws_conn_s3')
    hook.load_file(filename = filename, key = key, bucket_name = bucket_name, replace = True)

with DAG(
    dag_id = 'etl_customer_dag',
    description = 'Extract Credit Card Details From Customers Database.',
    default_args = default_args,
    start_date = datetime(2024,2,26),
    schedule_interval = '@once',
) as dag:

    extract_customers = PostgresOperator(
        task_id = 'extract_customers',
        postgres_conn_id = 'postgres_connection',
        sql='''
            SELECT * 
            FROM customer_credit_card_details;
        '''
    )

    saving_to_csv = PythonOperator(
        task_id='saving_to_csv',
        python_callable=saving_to_csv
    )

    task_upload_to_s3 = PythonOperator(
        task_id='upload_to_s3',
        python_callable = upload_to_s3,
        op_kwargs = {
            'filename' : '/Users/venkatasaisabbineni/Desktop/Airflow_local/output/customer_data.csv',
            'key' : 'customer_data.csv',
            'bucket_name' : 'etlcustomerbobby'
        }
    )

    read_s3_file_task = PythonOperator(
        task_id='read_s3_file_task',
        python_callable=read_s3_file,
        op_kwargs={
            'bucket_name': 'etlcustomerbobby',
            'file_key': 'customer_data.csv'
        }
    )

    remove_null_values_task = PythonOperator(
        task_id='remove_null_values_task',
        python_callable=remove_null_values,
        op_kwargs={
            'json_data': '{{ ti.xcom_pull(task_ids="read_s3_file_task") }}'
        }
    )

    task_upload_transformed_to_s3 = PythonOperator(
        task_id='upload_transformed_to_s3',
        python_callable = upload_to_s3,
        op_kwargs = {
            'filename' : '/Users/venkatasaisabbineni/Desktop/Airflow_local/output/transformed_customer_data.csv',
            'key' : 'transformed_customer_data.csv',
            'bucket_name' : 'etlcustomerbobby'
        }
    )

    is_file_in_s3_available = S3KeySensor(
        task_id='is_file_in_s3_available',
        bucket_key = 'transformed_customer_data.csv',
        bucket_name = 'etlcustomerbobby',
        aws_conn_id = 'aws_conn_s3',
        wildcard_match = False,
        timeout = 60,
        poke_interval = 5,    
    )

    transfer_s3_to_redshift = S3ToRedshiftOperator(
        task_id = "transfer_s3_to_redshift",
        aws_conn_id = 'aws_conn_s3',
        redshift_conn_id = 'aws_conn_redshift',
        s3_bucket = 'etlcustomerbobby',
        s3_key = 'transformed_customer_data.csv',
        schema = "PUBLIC",
        table = "customer_credit_card_details",
        copy_options = ["csv IGNOREHEADER 1"],
    )

    extract_customers >> saving_to_csv >> task_upload_to_s3 >> read_s3_file_task >> remove_null_values_task >> task_upload_transformed_to_s3 \
    >> is_file_in_s3_available >> transfer_s3_to_redshift

