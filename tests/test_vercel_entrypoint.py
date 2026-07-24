import runpy
from pathlib import Path


def test_vercel_entrypoint_exports_fastapi_app() -> None:
    namespace = runpy.run_path(Path(__file__).parents[1] / "app.py")

    assert namespace["app"].title == "France Company Clean API"
