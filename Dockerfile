# 1) Base Python image
FROM python:3.12-slim

# 2) Install prerequisites, build tools, and the Microsoft ODBC driver
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl \
      gnupg2 \
      apt-transport-https \
      unixodbc-dev \
      ca-certificates \
      build-essential \
      python3-dev \
      libffi-dev && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list \
      > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
      msodbcsql18 && \
    rm -rf /var/lib/apt/lists/*


# 3) Install Python dependencies
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# 4) Copy your app code
COPY . /app

# tell Docker/Cloud Run which port we’ll listen on
ENV PORT 8080
EXPOSE 8080

# use shell form so $PORT is expanded at runtime
ENTRYPOINT streamlit run src/app.py \
  --server.port $PORT \
  --server.address 0.0.0.0


