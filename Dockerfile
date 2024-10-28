FROM python:3.9-slim

WORKDIR /app

COPY . . /app

RUN pip install --no-cache-dir -r requirements.txt

# Expose standard HTTP port 80
EXPOSE 80

# Set Streamlit to run on port 80 without a base URL path
ENV STREAMLIT_SERVER_PORT=80

CMD ["streamlit", "run", "app.py", "--server.port=80"]
