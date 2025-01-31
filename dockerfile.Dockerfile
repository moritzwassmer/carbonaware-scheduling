# Use an official Python runtime as a base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the necessary files into the container
COPY scheduler.py .
COPY workload.yaml .

# Install required Python libraries
RUN pip install kubernetes kopf requests pyyaml

# Set the default command to run the scheduler
CMD kopf run /app/scheduler.py --verbose