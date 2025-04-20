# 1) Base Python image
FROM python:3.12-slim

# 2) Install ODBC prerequisites, build tools & Microsoft drivers
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl \
      gnupg2 \
      apt-transport-https \
      unixodbc-dev \
      ca-certificates \
      build-essential \         # ← for gcc, make, etc.
      python3-dev   \           # ← Python C headers
      libffi-dev    \           # ← needed by cffi (used by bcrypt)
 && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
 && curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list \
      > /etc/apt/sources.list.d/mssql-release.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
      msodbcsql18 \
 && rm -rf /var/lib/apt/lists/*


# 3) Install Python dependencies
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# 4) Copy your app code
COPY . /app

# 5) Expose Streamlit and start your app
EXPOSE 8501
ENTRYPOINT ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

