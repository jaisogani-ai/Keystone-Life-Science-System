# Keystone — AI Scientific Research Workbench
# Runs the interactive UI offline against the pinned real fixtures. No API key
# needed; set KEYSTONE_LIVE=1 + ANTHROPIC_API_KEY to enable the Claude agents.
FROM python:3.11-slim

WORKDIR /app

# Install deps first for layer caching.
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir requests fastapi uvicorn

COPY . .
RUN pip install --no-cache-dir -e .

# Offline by default: use the committed real fixtures, never the network at run.
ENV KEYSTONE_OFFLINE=1 KEYSTONE_PORT=8000
EXPOSE 8000

# Prove the build is sound, then serve the workbench.
RUN python -m pytest -q

CMD ["python", "-m", "keystone.ui.server"]
