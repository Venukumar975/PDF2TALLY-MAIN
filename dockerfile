# 1. Use an official lightweight Python runtime base image
FROM python:3.11-slim

# 2. Set environment variables to optimize Python inside Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Install system dependencies required by libraries like pdfplumber/pdfminer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 5. Copy the requirements file and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the entire local project directory structure into the container
COPY . .

# 7. Expose the default networking port Streamlit communicates on
EXPOSE 8501

# 8. Configure healthchecks to monitor container stability
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 9. Launch the main script entry point using Streamlit's runtime engine
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]