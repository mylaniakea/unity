# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install step CLI
RUN apt-get update && apt-get install -y wget
RUN wget https://dl.step.sm/gh-release/cli/docs-cli-install/v0.29.0/step-cli_0.29.0-1_amd64.deb
RUN dpkg -i step-cli_0.29.0-1_amd64.deb

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install dev dependencies if APP_ENV is set to development
ARG APP_ENV
COPY requirements-dev.txt .
RUN if [ "$APP_ENV" = "development" ] ; then pip install --no-cache-dir -r requirements-dev.txt ; fi


# Copy the rest of the application's code into the container at /app
COPY ./src /app/src

# Expose port 8000 to the outside world
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
