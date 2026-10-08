# Use the same Python version as the application container.
FROM python:3.12-slim

# Prevent Python from creating unnecessary .pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Send Python output directly to the terminal without buffering.
ENV PYTHONUNBUFFERED=1

# Use a dedicated directory inside the container.
WORKDIR /tests

# Copy the dependency list before the test code.
# This allows Docker to reuse the dependency layer when only tests change.
COPY requirements.txt .

# Install the pinned testing dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Create an unprivileged user instead of running tests as root.
RUN useradd \
    --create-home \
    --uid 10002 \
    --user-group \
    test-runner

# Copy the integration tests and give ownership to the test user.
COPY --chown=test-runner:test-runner test_app.py .

# Run all following commands as the unprivileged user.
USER test-runner

# Address used to reach the application through the Compose network.
ENV APP_BASE_URL=http://app:8000

# Run every test with verbose output.
# Disable pytest's cache because this container is removed after each run.
CMD ["pytest", "--verbose", "-p", "no:cacheprovider", "test_app.py"]
