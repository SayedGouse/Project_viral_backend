# Use an official Python image
FROM python:3.11-slim

# Install necessary dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the project files into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port (if your Flask app is running on port 5000)
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
