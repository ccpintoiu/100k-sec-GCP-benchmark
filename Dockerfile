# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.9-slim


# Allow statements and log messages to stdout and stderr to be sent to the console without buffering.
ENV PYTHONUNBUFFERED True


# Set the working directory in the container.
WORKDIR /app


# Copy the requirements file into the container.
COPY requirements.txt .


# Install dependencies.
RUN pip install --no-cache-dir -r requirements.txt


# Copy the rest of the application code into the container.
COPY . .


# Command to run the application using Gunicorn.
# Cloud Run injects the PORT environment variable.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
