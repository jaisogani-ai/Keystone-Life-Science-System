# Keystone — Scientific Operating System for translational biomedical research
# One-command run: `docker build -t keystone . && docker run -p 8000:8000 keystone`
# Offline by default (uses committed real fixtures). Set KEYSTONE_LIVE=1 and pass
# an ANTHROPIC_API_KEY to enable the live semantic layer.
FROM python:3.11-slim

WORKDIR /app

# Install runtime deps first for layer caching. requirements.txt covers the
# workbench + MCP server; the editable install below wires the keystone package.
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

# Offline by default — deterministic, reproducible, no external calls at runtime.
# Set KEYSTONE_OFFLINE=0 at `docker run` time to re-enable live connectors.
ENV KEYSTONE_OFFLINE=1 KEYSTONE_PORT=8000
EXPOSE 8000

# Serve the workbench. Tests run in CI, not on every image pull.
CMD ["python", "-m", "keystone.ui.server"]
