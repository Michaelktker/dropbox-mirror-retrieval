FROM python:3.12-slim

WORKDIR /app

# Install shared library
COPY shared/ shared/

# Install job-specific deps
COPY jobs/sync_dropbox_to_gcs/requirements.txt job/requirements.txt
RUN pip install --no-cache-dir -r job/requirements.txt

# Copy job code
COPY jobs/sync_dropbox_to_gcs/ job/

CMD ["python", "job/main.py"]
