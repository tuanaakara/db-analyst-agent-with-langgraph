# Use Python 3.13-slim base image
FROM python:3.13-slim

# Set working directory to /app
WORKDIR /app

# Update system dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy only requirements.txt first and install dependencies.
# This layering prevents reinstalling dependencies when code changes.
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend code
# Note: This COPY command works according to the build context in docker-compose.yml.
# Since we set context: ./backend in docker-compose.yml, it copies everything in the ./backend directory.
COPY . .

# Expose port 8000 for FastAPI server
EXPOSE 8000

# Command to run when the container starts
# Runs the FastAPI object named "app" in backend.py
CMD ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"]
