FROM python:3.12-slim

WORKDIR /app

# Install shared library
COPY shared/ shared/

# Install job-specific deps
COPY jobs/embed_images_to_vector_search/requirements.txt job/requirements.txt
RUN pip install --no-cache-dir -r job/requirements.txt

# Copy job code
COPY jobs/embed_images_to_vector_search/ job/

CMD ["python", "job/main.py"]
