FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /load-generator

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --uid 10001 loadgen

COPY --chown=loadgen:loadgen load.py .

USER loadgen

CMD ["python", "load.py"]