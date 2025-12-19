"""
ETL DAG for Product Data

Purpose:
- Extract raw product data from CSV (products.csv)
- Transform/clean data: remove duplicates, handle missing values, standardize columns
- Load transformed data into a cleaned CSV (transformed_products.csv)
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
import os
import shutil
import logging

# File paths
RAW_FILE_PATH = 'data/products.csv'
TRANSFORMED_FILE_PATH = 'data/transformed_products.csv'
ARCHIVE_DIR = 'data/archive/'

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def extract_products():
    """
    Extracts raw product data from CSV.
    Returns a pandas DataFrame.
    """
    if not os.path.exists(RAW_FILE_PATH):
        logging.error(f"Raw file not found at {RAW_FILE_PATH}")
        return pd.DataFrame()
    
    df = pd.read_csv(RAW_FILE_PATH)
    logging.info(f"Extracted {len(df)} rows from raw products.csv")
    return df


def transform_products():
    """
    Cleans and transforms product data.
    Operations:
    - Drop duplicates
    - Fill missing numeric values with 0
    - Fill missing string values with 'Unknown'
    - Standardize column names
    - Log summary stats
    """
    if not os.path.exists(RAW_FILE_PATH):
        logging.error(f"Raw file not found at {RAW_FILE_PATH}. Cannot transform.")
        return

    df = pd.read_csv(RAW_FILE_PATH)
    original_count = len(df)

    # Drop duplicate rows
    df = df.drop_duplicates()

    # Fill missing numeric values with 0
    numeric_cols = df.select_dtypes(include='number').columns
    df[numeric_cols] = df[numeric_cols].fillna(0)

    # Fill missing string values with 'Unknown'
    string_cols = df.select_dtypes(include='object').columns
    df[string_cols] = df[string_cols].fillna('Unknown')

    # Standardize column names
    df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]

    cleaned_count = len(df)
    logging.info(f"Transformed data: {original_count} -> {cleaned_count} rows after cleaning")

    # Save transformed CSV
    df.to_csv(TRANSFORMED_FILE_PATH, index=False)
    logging.info(f"Transformed data saved to {TRANSFORMED_FILE_PATH}")


def load_products():
    """
    Loads transformed product data.
    Currently logs the number of rows; can be extended to load into a DB.
    """
    if not os.path.exists(TRANSFORMED_FILE_PATH):
        logging.error(f"Transformed file not found at {TRANSFORMED_FILE_PATH}. Cannot load.")
        return

    df = pd.read_csv(TRANSFORMED_FILE_PATH)
    logging.info(f"Loaded {len(df)} rows from transformed CSV (ready for DB or analytics)")


def archive_raw_file():
    """
    Archives the raw CSV before transformation for traceability.
    """
    if not os.path.exists(RAW_FILE_PATH):
        logging.warning(f"No raw file to archive at {RAW_FILE_PATH}")
        return

    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)

    archive_path = os.path.join(ARCHIVE_DIR, f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    shutil.copy(RAW_FILE_PATH, archive_path)
    logging.info(f"Raw file archived at {archive_path}")


# Default DAG arguments
default_args = {
    'start_date': datetime(2025, 12, 19),
    'retries': 1,
    'catchup': False
}

# Define the DAG
with DAG(
    'etl_products_dag',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
    description='ETL DAG for extracting, transforming, and loading product data'
) as dag:

    # DAG tasks
    task_archive_raw = PythonOperator(
        task_id='archive_raw_file',
        python_callable=archive_raw_file
    )

    task_extract = PythonOperator(
        task_id='extract_products',
        python_callable=extract_products
    )

    task_transform = PythonOperator(
        task_id='transform_products',
        python_callable=transform_products
    )

    task_load = PythonOperator(
        task_id='load_products',
        python_callable=load_products
    )

    # Task sequence
    task_archive_raw >> task_extract >> task_transform >> task_load
