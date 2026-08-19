# syntax=docker/dockerfile:1

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Create an unprivileged runtime user before copying application files.
RUN addgroup --system app && adduser --system --ingroup app app

# Install dependencies in their own layer so source-only changes reuse the
# dependency cache during image builds.
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

# Keep the application image minimal and avoid copying local secrets, tests,
# virtual environments, and development metadata.
COPY --chown=app:app app ./app
COPY --chown=app:app minify ./minify
COPY --chown=app:app image_utils.py main.py ./

# Gunicorn does not need root privileges to listen on port 8080.
USER app

EXPOSE 8080

CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "--error-logfile", "-", "main:myapp"]

