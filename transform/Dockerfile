# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Install the PostgreSQL client
RUN apt-get update && apt-get install -y postgresql-client libpq-dev && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages
RUN pip install --no-cache-dir -r requirements.txt 

# Run app.py when the container launches
CMD ["python", "app.py"]