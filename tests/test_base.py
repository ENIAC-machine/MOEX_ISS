import pytest
import polars as pl
import pandas as pd
from datetime import date, datetime

import iss.base as base_module


# ============================================================
# list_securities
# ============================================================

class TestListSecurities:
    def test_success(self, mocker, mock_response, moex_csv):
        content = moex_csv(
            headers=["ticker", "emitent_id", "emitent_inn", "emitent_okpo", "regnumber"],
            rows=[["SBER", "1", "7707083893", "00000000", "1-02-77777"]],
        )
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = base_module.list_securities(q="SBER", start=0, end=1, verbose=False)

        assert isinstance(result, pl.DataFrame)
        assert result.height == 1
        assert result["ticker"][0] == "SBER"

    def test_trouble_cols_cast_to_string(self, mocker, mock_response, moex_csv):
        """Verify that trouble_cols are cast to String."""
        content = moex_csv(
            headers=["ticker", "emitent_id", "emitent_inn", "emitent_okpo", "regnumber"],
            rows=[["SBER", "12345", "7707083893", "00000000", "1-02-77777"]],
        )
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = base_module.list_securities(q="SBER", start=0, end=1, verbose=False)

        assert result.schema["emitent_id"] == pl.String
        assert result.schema["emitent_inn"] == pl.String

    def test_output_pandas(self, mocker, mock_response, moex_csv):
        content = moex_csv(
            headers=["ticker", "emitent_id", "emitent_inn", "emitent_okpo", "regnumber"],
            rows=[["SBER", "1", "7707083893", "00000000", "1-02"]],
        )
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = base_module.list_securities(q="SBER", start=0, end=1, verbose=False, out="pandas")

        assert isinstance(result, pd.DataFrame)

    
# ============================================================
# security_specs / indxs4secs / agg_info (TickerFunctionFactory)
# ============================================================

class TestTickerFunctions:
    @pytest.mark.parametrize("func,kwargs", [
        (base_module.security_specs, {"tickers": "SBER"}),
        (base_module.indxs4secs, {"tickers": "SBER"}),
        (base_module.agg_info, {"tickers": "SBER"}),
    ])
    def test_success_single_ticker(self, mocker, mock_response, moex_csv, func, kwargs):
        content = moex_csv(headers=["col"], rows=[["value"]])
        mocker.patch.object(base_module, "check_connection")
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = func(**kwargs, verbose=False)

        assert isinstance(result, dict)
        assert "SBER" in result

    @pytest.mark.parametrize("func,kwargs", [
        (base_module.security_specs, {"tickers": ["SBER", "GAZP"]}),
        (base_module.indxs4secs, {"tickers": ["SBER", "GAZP"]}),
        (base_module.agg_info, {"tickers": ["SBER", "GAZP"]}),
    ])
    def test_multiple_tickers(self, mocker, mock_response, moex_csv, func, kwargs):
        content = moex_csv(headers=["col"], rows=[["value"]])
        mocker.patch.object(base_module, "check_connection")
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = func(**kwargs, verbose=False)

        assert "SBER" in result
        assert "GAZP" in result

    def test_invalid_output_raises(self, mocker, mock_response, moex_csv):
        content = moex_csv(headers=["col"], rows=[["value"]])
        mocker.patch.object(base_module, "check_connection")
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        with pytest.raises(NotImplementedError):
            base_module.security_specs(tickers="SBER", out="xlsx", verbose=False)


# ============================================================
# market_info (base)
# ============================================================

class TestMarketInfoBase:
    def test_success(self, mocker, mock_response):
        json_data = {
            "boards": {
                "columns": ["boardid", "title"],
                "data": [["TQDE", "Main Board"]],
            }
        }
        get = mocker.patch.object(base_module.rq, "get", return_value=mock_response(json_data=json_data))
        check = mocker.patch.object(base_module, "check_connection")

        result = base_module.market_info()

        assert "boards" in result
        assert result["boards"].height == 1
        check.assert_called_once()

    def test_url_params(self, mocker, mock_response):
        get = mocker.patch.object(base_module.rq, "get", return_value=mock_response(json_data={}))
        mocker.patch.object(base_module, "check_connection")

        base_module.market_info(is_traded=False, hide_inactive=False, lang="ru")

        url = get.call_args.args[0]
        assert "lang=ru" in url
        assert "is_traded=False" in url
        assert "hide_inactive=False" in url

    def test_empty_response(self, mocker, mock_response):
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(json_data={}))
        mocker.patch.object(base_module, "check_connection")

        result = base_module.market_info()

        assert result == {}

    def test_multiple_tables(self, mocker, mock_response):
        json_data = {
            "boards": {"columns": ["id"], "data": [["1"]]},
            "securities": {"columns": ["id"], "data": [["2"]]},
        }
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(json_data=json_data))
        mocker.patch.object(base_module, "check_connection")

        result = base_module.market_info()

        assert len(result) == 2


# ============================================================
# _pre_turnovers
# ============================================================

class TestPreTurnovers:
    def test_success_with_explicit_start(self, mocker, mock_response, moex_csv):
        content = moex_csv(
            headers=["NAME", "UPDATETIME"],
            rows=[["market", "2024-01-01 10:00:00"]],
        )
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = base_module._pre_turnovers(
            start=date(2024, 1, 1),
            end=date(2024, 1, 2),
            verbose=False,
        )

        assert isinstance(result, pl.DataFrame)

    def test_start_none_defaults_to_yesterday(self, mocker, mock_response, moex_csv):
        content = moex_csv(
            headers=["NAME", "UPDATETIME"],
            rows=[["market", "2024-01-01 10:00:00"]],
        )
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = base_module._pre_turnovers(
            start=None,
            end=datetime(2024, 1, 2),
            verbose=False,
        )

        assert isinstance(result, pl.DataFrame)


# ============================================================
# turnovers
# ============================================================

class TestTurnovers:
    def test_filters_service_rows(self, mocker):
        pre_df = pl.DataFrame({
            "NAME": ["turnovers", "market", "TOTALS", "turnoversprevdate"],
            "UPDATETIME": [
                "2024-01-02 10:00:00",
                "2024-01-02 11:00:00",
                "2024-01-02 12:00:00",
                "2024-01-02 13:00:00",
            ],
        })

        mocker.patch.object(base_module, "_pre_turnovers", return_value=pre_df)
        mocker.patch.object(base_module, "check_connection")

        result = base_module.turnovers(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 2),
        )

        assert result["NAME"].to_list() == ["market"]

    def test_filters_old_dates(self, mocker):
        pre_df = pl.DataFrame({
            "NAME": ["old", "new"],
            "UPDATETIME": ["2023-12-31 09:00:00", "2024-01-02 10:00:00"],
        })

        mocker.patch.object(base_module, "_pre_turnovers", return_value=pre_df)
        mocker.patch.object(base_module, "check_connection")

        result = base_module.turnovers(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 2),
        )

        assert result.height == 1
        assert result["NAME"][0] == "new"

    def test_start_none_defaults_to_yesterday(self, mocker):
        pre_df = pl.DataFrame({
            "NAME": ["market"],
            "UPDATETIME": ["2024-01-02 10:00:00"],
        })

        pre_mock = mocker.patch.object(base_module, "_pre_turnovers", return_value=pre_df)
        mocker.patch.object(base_module, "check_connection")

        base_module.turnovers(end=date(2024, 1, 3))

        called_kwargs = pre_mock.call_args.kwargs
        expected_start = date(2024, 1, 2) - __import__("datetime").timedelta(days=1)
        # start should be end.date() - 1 day = 2024-01-02
        assert called_kwargs["start"] == date(2024, 1, 2)

    def test_check_connection_called(self, mocker):
        check = mocker.patch.object(base_module, "check_connection")

        base_module.turnovers(start=datetime(2024, 1, 1), end=datetime(2024, 1, 4))

        check.assert_called_once()

    def test_empty_pre_turnovers_returns_empty(self, mocker):
        pre_df = pl.DataFrame({nm : [] for nm in\
                ['NAME', 'ID', 'VALTODAY', 'VALTODAY_USD', 'NUMTRADES', 'UPDATETIME', 'TITLE']
                               },
                              schema={'NAME': pl.String,
                              'ID': pl.String,
                              'VALTODAY': pl.String,
                              'VALTODAY_USD': pl.String,
                              'NUMTRADES': pl.String,
                              'UPDATETIME': pl.Datetime(time_unit='us', time_zone=None),
                              'TITLE': pl.String})
        mocker.patch.object(base_module, "turnovers", return_value=pre_df)
        mocker.patch.object(base_module, "check_connection")

        result = base_module.turnovers(start=date(2024, 1, 1), end=date(2024, 1, 2))

        assert result.height == 0

    def test_duplicates_removed(self, mocker):
        pre_df = pl.DataFrame({
            "NAME": ["market", "market"],
            "UPDATETIME": ["2024-01-02 10:00:00", "2024-01-02 10:00:00"],
        })

        mocker.patch.object(base_module, "_pre_turnovers", return_value=pre_df)
        mocker.patch.object(base_module, "check_connection")

        result = base_module.turnovers(start=datetime(2024, 1, 1), end=datetime(2024, 1, 2))

        assert result.height == 1


# ============================================================
# turnover_cols
# ============================================================

class TestTurnoverCols:
    def test_success(self, mocker, mock_response):
        expected = pl.DataFrame({"name": ["turnover"], "title": ["Turnover"]})
        read_csv = mocker.patch.object(base_module.pl, "read_csv", return_value=expected)
        get = mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=b""))
        check = mocker.patch.object(base_module, "check_connection")

        result = base_module.turnover_cols()

        assert result is expected
        check.assert_called_once()
        get.assert_called_once()

    def test_url_includes_lang(self, mocker, mock_response):
        get = mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=b""))
        mocker.patch.object(base_module.pl, "read_csv", return_value=pl.DataFrame())
        mocker.patch.object(base_module, "check_connection")

        base_module.turnover_cols(lang="ru")

        url = get.call_args.args[0]
        assert "lang=ru" in url

    def test_timeout_passed(self, mocker, mock_response):
        get = mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=b""))
        mocker.patch.object(base_module.pl, "read_csv", return_value=pl.DataFrame())
        mocker.patch.object(base_module, "check_connection")

        base_module.turnover_cols(timeout=10)

        assert get.call_args.kwargs["timeout"] == 10

    def test_default_timeout(self, mocker, mock_response):
        get = mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=b""))
        mocker.patch.object(base_module.pl, "read_csv", return_value=pl.DataFrame())
        mocker.patch.object(base_module, "check_connection")

        base_module.turnover_cols()

        assert get.call_args.kwargs["timeout"] == 5

    def test_check_connection_called(self, mocker, mock_response):
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=b""))
        mocker.patch.object(base_module.pl, "read_csv", return_value=pl.DataFrame())
        check = mocker.patch.object(base_module, "check_connection")

        base_module.turnover_cols()

        check.assert_called_once()
