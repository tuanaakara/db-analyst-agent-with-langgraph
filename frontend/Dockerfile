# Use Python 3.11-slim base image
FROM python:3.11-slim

# Set working directory to /app
WORKDIR /app

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy only requirements.txt first and install dependencies
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all frontend code
COPY . .

# Expose port 7860 for Gradio
EXPOSE 7860

# Command to run when the container starts
# Runs the frontend.py file
CMD ["python", "frontend.py"]
