FROM python:3.11

# Set the working directory in the container
WORKDIR /code

# Poppler is required for pdf2image
# Install system dependencies, including Poppler
RUN apt-get update && \
    apt-get install -y poppler-utils && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

    # Copy the requirements file into the container
COPY requirements.dockerize.txt requirements.txt ./

# Install the dependencies
RUN pip install --no-cache-dir --upgrade -r requirements.dockerize.txt


# Copy the rest of the application code into the container
COPY comprendo ./comprendo
COPY comprendo server.py ./

# Expose the port that the app will run on
EXPOSE 3100

# Command to run the application using Uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3100", "--workers", "2"]