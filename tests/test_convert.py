"""Tests for the convert module."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import sqlalchemy as sa
from typer.testing import CliRunner

from dwca_tools.cli import app
from dwca_tools.db import create_engine_and_session
from dwca_tools.settings import get_convert_settings

runner = CliRunner()

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "test_dwca.zip"


class TestConvertCLI:
    """Tests for convert CLI command."""

    def test_convert_help(self) -> None:
        """Convert help includes new options."""
        result = runner.invoke(app, ["convert", "convert", "--help"])
        assert result.exit_code == 0
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
        assert "chunk-size" in plain
        assert "num-threads" in plain

    @pytest.mark.integration
    def test_convert_sqlite(self, tmp_path: Path) -> None:
        """Convert a test archive to SQLite and verify row counts."""
        get_convert_settings.cache_clear()
        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"

        result = runner.invoke(
            app,
            [
                "convert",
                "convert",
                str(FIXTURE_PATH),
                "--db-url",
                db_url,
                "--chunk-size",
                "5",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Conversion completed successfully" in result.output

        engine, session = create_engine_and_session(db_url)
        inspector = sa.inspect(engine)
        table_names = inspector.get_table_names()
        assert "occurrence" in table_names
        assert "multimedia" in table_names

        # Verify row counts
        occ_table = sa.Table("occurrence", sa.MetaData(), autoload_with=engine)
        occ_count = session.execute(sa.select(sa.func.count()).select_from(occ_table)).scalar_one()
        assert occ_count == 20

        mm_table = sa.Table("multimedia", sa.MetaData(), autoload_with=engine)
        mm_count = session.execute(sa.select(sa.func.count()).select_from(mm_table)).scalar_one()
        assert mm_count == 10

        session.close()


class TestConvertSettings:
    """Tests for ConvertSettings."""

    def test_defaults(self) -> None:
        """Default settings have expected values."""
        get_convert_settings.cache_clear()
        settings = get_convert_settings()
        assert settings.chunk_size == 500
        assert settings.num_threads == 4
        assert "occurrence" in settings.columns_of_interest
        assert "occurrence" in settings.indexes

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings can be overridden via env vars."""
        get_convert_settings.cache_clear()
        monkeypatch.setenv("DWCA_CHUNK_SIZE", "100")
        get_convert_settings.cache_clear()
        settings = get_convert_settings()
        assert settings.chunk_size == 100
        get_convert_settings.cache_clear()
