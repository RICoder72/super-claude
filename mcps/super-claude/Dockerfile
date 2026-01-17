FROM python:3.12-slim

WORKDIR /app

# Set Docker API version to match Synology's daemon
ENV DOCKER_API_VERSION=1.41

# Install Docker CLI, git, and other tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        git && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install uv

# Copy shared modules
COPY shared/ /app/shared/

# Copy MCP code
COPY mcps/super-claude/ /app/

# Install dependencies
RUN uv pip install --system -e .

# Configure git to trust the /data directory (for shell_exec git commands)
RUN git config --global --add safe.directory /data

EXPOSE 8000

CMD ["python", "server.py"]
