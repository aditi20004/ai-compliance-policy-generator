FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data generated_policies data/chroma data/evidence

COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]
