# 1. Use an official Python runtime as a parent image
FROM python:3.13-slim 

# 2. Set environment variables to prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=True

# 3. Set the working directory in the container
ENV APP_HOME /app
WORKDIR $APP_HOME

# 4. Copy requirements first to leverage Docker cache
COPY requirements.txt .

# 5. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of the application code
COPY . .

# 7. Expose the port (Cloud Run uses 8080 by default)
# We use the $PORT variable provided by Cloud Run environment
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app