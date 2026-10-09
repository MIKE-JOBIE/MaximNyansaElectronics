FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=wsgi.py \
    FLASK_ENV=production

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user, not root
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('PORT','5000'), timeout=4)" || exit 1

CMD ["gunicorn", "wsgi:app", "-c", "gunicorn.conf.py"]
