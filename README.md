generate keys and serve them over a fastapi endpoint
the code uses a .env to manage base_url.
features:
  Concurrency: The concurrent key generation ensures that keys are generated quickly without blocking.
  Error Handling: Proper error handling to ensure that one base URL failure does not affect the others.
  Lifecycle Management: Background tasks are managed correctly with FastAPI’s startup events.
  Asyncio Periodic Task: The refresh_keys function is now an asyncio task that periodically refreshes keys every 30 minutes without blocking the main event loop.
  Startup Event: The refresh_keys task is started as part of the FastAPI startup event.
