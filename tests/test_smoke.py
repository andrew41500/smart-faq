from backend.app import create_app


def test_app_factory():
  """
  Basic smoke test to ensure the Flask app can be constructed.

  Uses environment variables to avoid hitting real LLMs in CI.
  """
  import os

  # Use Hugging Face provider with a dummy token; network is not called in this test
  os.environ.setdefault("LLM_PROVIDER", "huggingface")
  os.environ.setdefault("HUGGINGFACE_API_TOKEN", "dummy-token")

  app = create_app()
  assert app is not None


