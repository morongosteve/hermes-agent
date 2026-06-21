# Hugging Face Docker Space for Hermes Agent.
#
# This image is compatible with Spaces Dev Mode:
#   - bash is installed (required to establish SSH connections)
#   - curl, wget and procps are installed (required by the VS Code server)
#   - git and git-lfs are installed (to commit/push changes from Dev Mode)
#   - the application lives in /app, owned by uid 1000
#   - a CMD instruction is provided for startup
#   - the base image is debian-based (python:slim)
#
# See: https://huggingface.co/docs/hub/spaces-dev-mode
FROM python:3.11-slim

# System packages required by Spaces Dev Mode, plus a few developer
# conveniences (vim, nano, htop) and build tooling for Python wheels.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      bash \
      curl wget procps \
      git git-lfs \
      ca-certificates \
      build-essential \
      vim nano htop && \
    git lfs install && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the application code into /app (where Dev Mode detects changes).
COPY --link . /app

# Install the core Python dependencies so the agent is ready to use from a
# Dev Mode terminal. Optional extras (messaging, modal, ...) can be installed
# on demand with: pip install -e ".[all]"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Hugging Face Spaces serves the app on port 7860 by default.
ENV PORT=7860
EXPOSE 7860

# Dev Mode requires /app to be owned by uid 1000 so code can be edited live.
RUN chown -R 1000 /app
USER 1000

# A CMD is required for Dev Mode; the daemon starts it as a restartable
# sub-process.
CMD ["python", "space_app.py"]
