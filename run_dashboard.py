"""Launches the Streamlit dashboard. Run with:

    python run_dashboard.py

Then open http://localhost:8501 in your browser.
"""
import subprocess
import sys
from pathlib import Path

from app.database import init_db
from app.services.company_service import sync_companies_from_yaml
from app.database import get_session


def main() -> None:
    init_db()
    with get_session() as session:
        sync_companies_from_yaml(session)

    dashboard_path = Path(__file__).resolve().parent / "app" / "dashboard.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(dashboard_path)])


if __name__ == "__main__":
    main()
