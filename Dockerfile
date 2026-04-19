# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install FFmpeg and clean up apt cache to keep image small
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend files into the container
COPY . .

# Create directories for downloads and temp files
RUN mkdir -p downloads temp

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run the FastAPI server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
