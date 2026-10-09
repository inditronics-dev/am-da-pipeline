# Base image
FROM python:3.14

# Set working directory
WORKDIR /app

# Copy entire project
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable (optional default)
ENV RUN_DATE=""

# Run your pipeline
CMD ["python", "main.py"]