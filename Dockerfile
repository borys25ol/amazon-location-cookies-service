FROM python:3.14-slim

RUN mkdir /code
WORKDIR /code

COPY requirements.txt ./

RUN pip install -U pip
RUN pip install --no-cache-dir -r requirements.txt

# Chromium solves the AWS WAF challenge that fronts every Amazon storefront.
# `--only-shell` installs just the headless shell: the full Chromium build drags
# in the X11 and GTK stack for a window that is never opened.
RUN playwright install --with-deps --only-shell chromium \
    && rm -rf /var/lib/apt/lists/*

COPY .env scrapy.cfg ./

COPY main main/
