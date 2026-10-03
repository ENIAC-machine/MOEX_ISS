import pytest
import polars as pl


@pytest.fixture
def mock_response(mocker):
    """
    Fixture factory for mocked requests.Response objects.
    """

    def _make(content: bytes = b"", json_data=None, status_code: int = 200):
        response = mocker.Mock()
        response.status_code = status_code
        response.raise_for_status.return_value = None
        response.content = content
        response.json.return_value = json_data if json_data is not None else {}
        return response

    return _make


@pytest.fixture
def mock_error_response(mocker):
    """
    Fixture factory for mocked requests.Response objects that raise HTTP errors.
    """

    def _make(status_code: int = 404):
        import requests
        response = mocker.Mock()
        response.status_code = status_code
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"{status_code} Error"
        )
        return response

    return _make


@pytest.fixture
def moex_csv():
    """
    Fixture factory for MOEX-like CSV bytes.
    MOEX ISS CSV responses have two ignored rows before the header.
    """

    def _make(headers: list[str], rows: list[list[str]]) -> bytes:
        lines = [
            "ignored",
            "ignored",
            ";".join(headers),
        ]
        lines.extend(
            ";".join(str(value) for value in row)
            for row in rows
        )
        return ("\n".join(lines) + "\n").encode("cp1251")

    return _make


@pytest.fixture
def moex_json():
    """
    Fixture factory for MOEX-like JSON responses.
    """

    def _make(tables: dict[str, dict]) -> dict:
        return tables

    return _make
