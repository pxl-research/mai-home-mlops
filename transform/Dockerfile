# docker-compose -f docker-compose.prod.yml pull
# docker-compose -f docker-compose.prod.yml down
# docker-compose -f docker-compose.prod.yml up --build


# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir influxdb-client

# Run app.py when the container launches
CMD ["python", "app.py"]