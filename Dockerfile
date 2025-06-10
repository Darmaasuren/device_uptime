FROM python

WORKDIR /app

COPY requirement.txt requirement.txt

RUN pip install --no-cache-dir -r requirement.txt

COPY log_uptime.py .

CMD ["python3", "log_uptime.py"]
