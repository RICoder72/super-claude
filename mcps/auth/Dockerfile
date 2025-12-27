FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy shared module
COPY shared/ /app/shared/

# Copy MCP files
COPY mcps/auth/pyproject.toml /app/
COPY mcps/auth/server.py /app/

# Install dependencies
RUN uv pip install --system -e .

EXPOSE 8000

CMD ["python", "server.py"]
