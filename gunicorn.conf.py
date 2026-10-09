import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
# Free tiers have ~512MB RAM: 2 workers x 4 threads. Raise WEB_CONCURRENCY on bigger plans.
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
worker_class = "gthread"
timeout = 30
graceful_timeout = 30
keepalive = 5
max_requests = 1000            # recycle workers to contain slow memory leaks
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
forwarded_allow_ips = "*"      # Render/Heroku put the app behind a trusted proxy
