# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import multiprocessing

import gunicorn.glogging

max_requests = 1000
max_requests_jitter = 50
log_file = "-"
bind = "0.0.0.0:8000"

timeout = 600
# https://learn.microsoft.com/en-us/troubleshoot/azure/app-service/web-apps-performance-faqs#why-does-my-request-time-out-after-230-seconds

num_cpus = multiprocessing.cpu_count()
workers = num_cpus * 2 + 1
worker_class = "uvicorn_worker.UvicornWorker"
port = 8000
log_config = gunicorn.glogging.CONFIG_DEFAULTS
