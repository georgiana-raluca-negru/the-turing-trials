# 1. Base Image: Use an official, lightweight Python image
FROM python:3.12-slim

# 2. Set the Working Directory inside the container
WORKDIR /app

# 3. Copy only the requirements file first (Pro-tip for speed!)
COPY requirements.txt .

# 4. Install the Python packages
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your backend code into the container
COPY . .

# 6. Make llm_functionality packages importable (ai_engine, backend_integration)
ENV PYTHONPATH="/app/llm_functionality:${PYTHONPATH}"

# 7. Expose the port FastAPI uses
EXPOSE 8000

# 8. The command to start the server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]