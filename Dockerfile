# Use official Streamlit image as base
FROM python:3.10

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 8501

# Run Streamlit app
CMD ["streamlit", "run", "app1.py", "--server.port=8501", "--server.enableCORS=false"]
