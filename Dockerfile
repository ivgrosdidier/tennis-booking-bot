# 1. Use an official Python runtime as a parent image
FROM python:3.13-slim 

# 2. Set environment variables to prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED True

# 3. Copy local code to container image
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# 4. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Run web service on container startup. Use gunicorn webserver with 1 worker process and 8 threads
# for env with multiple CPU cores, increase the number of workers to be equal to the cores available.
# timeout set to 0 to disable timeouts of the workers to allow cloud run to handle instance scaling
# Use 8080 as a default if $PORT is not set
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app