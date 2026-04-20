FROM apache/airflow:2.8.1-python3.11

# Add the local bin to PATH so Airflow can find dbt later
ENV PATH="/home/airflow/.local/bin:$PATH"

RUN pip install --no-cache-dir \
    pandas \
    numpy \
    pyarrow \
    requests \
    python-dotenv \
    snowflake-connector-python \
    streamlit \
    dbt-snowflake \
    dbt-core

WORKDIR /opt/airflow

# Copy your project files with the correct ownership
COPY --chown=airflow:root . .