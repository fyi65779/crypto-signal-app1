# Use official Python base image
FROM python:3.10

# Set working directory
WORKDIR /app

# Copy all files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Streamlit port
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "app1.py", "--server.port=8501", "--server.enableCORS=false"]
