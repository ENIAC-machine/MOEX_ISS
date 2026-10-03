import pytest
import polars as pl
import pandas as pd
import requests
from datetime import date

import iss.engines as engines
import iss.base as base_module


# ============================================================
# available_engines
# ============================================================

class TestAvailableEngines:
    def test_success_default_lang(self, mocker):
        expected = pl.DataFrame({"engine": ["stock"]})
        read_csv = mocker.patch.object(engines.pl, "read_csv", return_value=expected)

        result = engines.available_engines()

        assert result is expected
        url = read_csv.call_args.args[0]
        assert url == "https://iss.moex.com/iss/engines.csv?lang=en"

    def test_success_custom_lang(self, mocker):
        expected = pl.DataFrame({"engine": ["stock"]})
        read_csv = mocker.patch.object(engines.pl, "read_csv", return_value=expected)

        engines.available_engines(lang="ru")

        url = read_csv.call_args.args[0]
        assert url == "https://iss.moex.com/iss/engines.csv?lang=ru"

    def test_csv_parsing_kwargs(self, mocker):
        mocker.patch.object(engines.pl, "read_csv", return_value=pl.DataFrame())

        engines.available_engines()

        kwargs = engines.pl.read_csv.call_args.kwargs
        assert kwargs["skip_rows"] == 2
        assert kwargs["has_header"] is True
        assert kwargs["encoding"] == "cp1251"
        assert kwargs["separator"] == ";"

    def test_empty_response(self, mocker):
        expected = pl.DataFrame()
        mocker.patch.object(engines.pl, "read_csv", return_value=expected)

        result = engines.available_engines()

        assert result.height == 0


# ============================================================
# engine_info
# ============================================================

class TestEngineInfo:
    def test_success_parses_all_tables(self, mocker, mock_response):
        json_data = {
            "engine": {
                "columns": ["engine", "title"],
                "data": [["stock", "Stock Market"]],
            },
            "markets": {
                "columns": ["market", "title"],
                "data": [["shares", "Shares"], ["bonds", "Bonds"]],
            },
        }

        mocker.patch.object(engines.rq, "get", return_value=mock_response(json_data=json_data))
        mocker.patch.object(engines, "check_connection")

        result = engines.engine_info("stock")

        assert isinstance(result, dict)
        assert len(result) == 2
        assert result["engine"].height == 1
        assert result["markets"].height == 2

    def test_time_columns_converted(self, mocker, mock_response):
        json_data = {
            "session": {
                "columns": ["start_time", "stop_time"],
                "data": [["09:00:00", "18:00:00"]],
            },
        }

        mocker.patch.object(engines.rq, "get", return_value=mock_response(json_data=json_data))
        mocker.patch.object(engines, "check_connection")

        result = engines.engine_info("stock")

        assert result["session"].schema["start_time"] == pl.Time
        assert result["session"].schema["stop_time"] == pl.Time

    def test_non_time_columns_not_converted(self, mocker, mock_response):
        json_data = {
            "info": {
                "columns": ["name", "value"],
                "data": [["test", "123"]],
            },
        }

        mocker.patch.object(engines.rq, "get", return_value=mock_response(json_data=json_data))
        mocker.patch.object(engines, "check_connection")

        result = engines.engine_info("stock")

        assert result["info"].schema["name"] == pl.String
        assert result["info"].schema["value"] == pl.String

    def test_partial_time_columns_not_converted(self, mocker, mock_response):
        """If only start_time exists without stop_time, no conversion should happen."""
        json_data = {
            "session": {
                "columns": ["start_time", "other_col"],
                "data": [["09:00:00", "value"]],
            },
        }

        mocker.patch.object(engines.rq, "get", return_value=mock_response(json_data=json_data))
        mocker.patch.object(engines, "check_connection")

        result = engines.engine_info("stock")

        # Should remain String since not both time_cols are present
        assert result["session"].schema["start_time"] == pl.String

    def test_url_includes_engine_and_lang(self, mocker, mock_response):
        mocker.patch.object(engines.rq, "get", return_value=mock_response(json_data={}))
        mocker.patch.object(engines, "check_connection")

        engines.engine_info("futures", lang="ru")

        url = engines.rq.get.call_args.args[0]
        assert url == "https://iss.moex.com/iss/engines/futures.json?lang=ru"

    def test_check_connection_called(self, mocker, mock_response):
        mocker.patch.object(engines.rq, "get", return_value=mock_response(json_data={}))
        check = mocker.patch.object(engines, "check_connection")

        engines.engine_info("stock")

        check.assert_called_once()

    def test_empty_json_response(self, mocker, mock_response):
        mocker.patch.object(engines.rq, "get", return_value=mock_response(json_data={}))
        mocker.patch.object(engines, "check_connection")

        result = engines.engine_info("stock")

        assert result == {}


# ============================================================
# engine_zcyc
# ============================================================

class TestEngineZcyc:
    def test_success(self, mocker, mock_response):
        json_data = {
            "zcyc": {
                "columns": ["date", "yield"],
                "data": [["2024-01-01", 7.5]],
            }
        }

        mocker.patch.object(base_module, "check_connection")
        mocker.patch.object(
            base_module.rq, "get",
            return_value=mock_response(json_data=json_data),
        )

        result = engines.engine_zcyc(engine="stock", date="2024-01-01")

        assert isinstance(result, dict)
        assert "zcyc" in result

    def test_url_formatting(self, mocker, mock_response):
        mocker.patch.object(base_module, "check_connection")
        mocker.patch.object(
            base_module.rq, "get",
            return_value=mock_response(json_data={}),
        )

        engines.engine_zcyc(engine="stock", date="2024-01-01", lang="ru")

        url = base_module.rq.get.call_args.args[0]
        assert "engines/stock/zcyc.json" in url
        assert "lang=ru" in url


# ============================================================
# _candle_single_day
# ============================================================

class TestCandleSingleDay:
    def test_success_single_ticker(self, mocker, mock_response, moex_csv):
        content = moex_csv(
            headers=["open", "close", "high", "low", "value", "volume", "begin", "end"],
            rows=[[100.0, 101.0, 102.0, 99.0, 1000.0, 10, "2024-01-01 10:00:00", "2024-01-01 10:10:00"]],
        )

        mocker.patch.object(base_module, "check_connection")
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = engines._candle_single_day(
            engine="stock",
            market="shares",
            tickers="SBER",
            st=date(2024, 1, 1),
            end=date(2024, 1, 2),
            verbose=False,
        )

        assert "SBER" in result
        assert result["SBER"].height == 1

    def test_multiple_tickers(self, mocker, mock_response, moex_csv):
        content = moex_csv(
            headers=["open", "close", "high", "low", "value", "volume", "begin", "end"],
            rows=[[100.0, 101.0, 102.0, 99.0, 1000.0, 10, "2024-01-01 10:00:00", "2024-01-01 10:10:00"]],
        )

        mocker.patch.object(base_module, "check_connection")
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = engines._candle_single_day(
            engine="stock",
            market="shares",
            tickers=["SBER", "GAZP"],
            st=date(2024, 1, 1),
            end=date(2024, 1, 2),
            verbose=False,
        )

        assert "SBER" in result
        assert "GAZP" in result


# ============================================================
# candles
# ============================================================

class TestCandles:
    def _make_candle_df(self):
        return pl.DataFrame({
            "open": [100.0],
            "close": [101.0],
            "high": [102.0],
            "low": [99.0],
            "value": [1000.0],
            "volume": [10],
            "begin": ["2024-01-01 10:00:00"],
            "end": ["2024-01-01 10:10:00"],
        }).with_columns(pl.col("volume").cast(pl.Int64))

    def test_single_ticker_single_day_polars(self, mocker):
        df = self._make_candle_df()
        mocker.patch.object(engines, "_candle_single_day", return_value={"SBER": df})

        result = engines.candles(
            tickers="SBER",
            st=date(2024, 1, 1),
            end=date(2024, 1, 2),
            verbose=False,
        )

        assert "SBER" in result
        assert isinstance(result["SBER"], pl.DataFrame)
        assert result["SBER"].height == 1

    def test_single_ticker_multiple_days(self, mocker):
        df = self._make_candle_df()
        mock_single = mocker.patch.object(
            engines, "_candle_single_day",
            side_effect=[{"SBER": df.clone()}, {"SBER": df.clone()}, {"SBER": df.clone()}],
        )

        result = engines.candles(
            tickers="SBER",
            st=date(2024, 1, 1),
            end=date(2024, 1, 4),
            verbose=False,
        )

        assert result["SBER"].height == 3
        assert mock_single.call_count == 3

    def test_multiple_tickers(self, mocker):
        df = self._make_candle_df()
        mocker.patch.object(
            engines, "_candle_single_day",
            side_effect=[
                {"SBER": df.clone()},
                {"GAZP": df.clone()},
            ],
        )

        result = engines.candles(
            tickers=["SBER", "GAZP"],
            st=[date(2024, 1, 1), date(2024, 1, 1)],
            end=[date(2024, 1, 2), date(2024, 1, 2)],
            verbose=False,
        )

        assert "SBER" in result
        assert "GAZP" in result

    def test_output_polars_lazy(self, mocker):
        df = self._make_candle_df()
        mocker.patch.object(engines, "_candle_single_day", return_value={"SBER": df})

        result = engines.candles(
            tickers="SBER",
            st=date(2024, 1, 1),
            end=date(2024, 1, 2),
            out="polars_lazy",
            verbose=False,
        )

        assert isinstance(result["SBER"], pl.LazyFrame)

    def test_output_pandas(self, mocker):
        df = self._make_candle_df()
        mocker.patch.object(engines, "_candle_single_day", return_value={"SBER": df})

        result = engines.candles(
            tickers="SBER",
            st=date(2024, 1, 1),
            end=date(2024, 1, 2),
            out="pandas",
            verbose=False,
        )

        assert isinstance(result["SBER"], pd.DataFrame)

    def test_st_equals_end_returns_empty(self, mocker):
        mocker.patch.object(engines, "_candle_single_day")

        result = engines.candles(
            tickers="SBER",
            st=date(2024, 1, 1),
            end=date(2024, 1, 1),
            verbose=False,
        )

        assert result == {'SBER' : None}

    def test_schema_casting(self, mocker):
        """Verify that output columns are cast to the expected schema."""
        df = self._make_candle_df()
        mocker.patch.object(engines, "_candle_single_day", return_value={"SBER": df})

        result = engines.candles(
            tickers="SBER",
            st=date(2024, 1, 1),
            end=date(2024, 1, 2),
            verbose=False,
        )

        schema = result["SBER"].schema
        assert schema["open"] == pl.Float64
        assert schema["close"] == pl.Float64
        assert schema["high"] == pl.Float64
        assert schema["low"] == pl.Float64
        assert schema["value"] == pl.Float64
        assert schema["volume"] == pl.Int64
        assert schema["begin"] == pl.String
        assert schema["end"] == pl.String


# ============================================================
# available_markets
# ============================================================

class TestAvailableMarkets:
    def test_success(self, mocker):
        expected = pl.DataFrame({"market": ["shares"]})
        read_csv = mocker.patch.object(engines.pl, "read_csv", return_value=expected)
        check = mocker.patch.object(engines, "check_connection")

        result = engines.available_markets("stock")

        assert result is expected
        check.assert_called_once()
        assert "engines/stock/markets.csv" in read_csv.call_args.args[0]

    def test_custom_lang(self, mocker):
        mocker.patch.object(engines.pl, "read_csv", return_value=pl.DataFrame())
        mocker.patch.object(engines, "check_connection")

        engines.available_markets("stock", lang="ru")

        url = engines.pl.read_csv.call_args.args[0]
        assert "lang=ru" in url

    def test_different_engine(self, mocker):
        mocker.patch.object(engines.pl, "read_csv", return_value=pl.DataFrame())
        mocker.patch.object(engines, "check_connection")

        engines.available_markets("futures")

        url = engines.pl.read_csv.call_args.args[0]
        assert "engines/futures/markets.csv" in url


# ============================================================
# market_info (engines)
# ============================================================

class TestMarketInfoEngines:
    
    def test_success(self, mocker, mock_response):
        json_data = {
            "market": {
                "columns": ["market", "title"],
                "data": [["shares", "Shares"]],
            }
        }

        mocker.patch.object(base_module, "check_connection")
        mocker.patch.object(
            base_module.rq, "get",
            return_value=mock_response(json_data=json_data),
        )

        result = engines.market_info("stock", "shares")

        assert "market" in result
        assert result["market"].height == 1


# ============================================================
# secstats
# ============================================================

class TestSecstats:
    def test_success_single_security(self, mocker):
        expected = pl.DataFrame({"SECID": ["GAZP"], "VALUE": [100.0]})
        read_csv = mocker.patch.object(engines.pl, "read_csv", return_value=expected)
        mocker.patch.object(engines, "check_connection")

        result = engines.secstats("stock", "shares", securities=["GAZP"])

        assert result is expected
        url = read_csv.call_args.args[0]
        assert "securities=GAZP" in url

    def test_success_multiple_securities(self, mocker):
        expected = pl.DataFrame({"SECID": ["GAZP", "SBER"]})
        read_csv = mocker.patch.object(engines.pl, "read_csv", return_value=expected)
        mocker.patch.object(engines, "check_connection")

        engines.secstats("stock", "shares", securities=["GAZP", "SBER"])

        url = read_csv.call_args.args[0]
        assert "GAZP" in url
        assert "SBER" in url

    def test_rejects_more_than_10_board_ids(self, mocker):
        mocker.patch.object(engines, "check_connection")

        with pytest.raises(ValueError, match="10 or less"):
            engines.secstats("stock", "shares", board_id=[f"B{i}" for i in range(11)])

    def test_accepts_exactly_10_board_ids(self, mocker):
        mocker.patch.object(engines.pl, "read_csv", return_value=pl.DataFrame())
        mocker.patch.object(engines, "check_connection")

        # Should NOT raise
        engines.secstats("stock", "shares", board_id=[f"B{i}" for i in range(10)])

    def test_url_includes_tradingsession(self, mocker):
        read_csv = mocker.patch.object(engines.pl, "read_csv", return_value=pl.DataFrame())
        mocker.patch.object(engines, "check_connection")

        engines.secstats("stock", "shares", trading_session=2)

        url = read_csv.call_args.args[0]
        assert "tradingsession=2" in url

    def test_check_connection_called(self, mocker):
        mocker.patch.object(engines.pl, "read_csv", return_value=pl.DataFrame())
        check = mocker.patch.object(engines, "check_connection")

        engines.secstats("stock", "shares")

        check.assert_called_once()


# ============================================================
# market_zcyc
# ============================================================

class TestMarketZcyc:
    def test_emits_deprecation_warning(self):
        original = getattr(engines.market_zcyc, "__wrapped__", None)
        if original is None:
            pytest.skip("market_zcyc does not expose __wrapped__")

        with pytest.warns(DeprecationWarning, match="deprecated"):
            original(engine="stock")

    def test_wrapper_success(self, mocker, mock_response):
        json_data = {"zcyc": {"columns": ["date"], "data": [["2024-01-01"]]}}

        mocker.patch.object(base_module, "check_connection")
        mocker.patch.object(
            base_module.rq, "get",
            return_value=mock_response(json_data=json_data),
        )

        with pytest.warns(DeprecationWarning):
            result = engines.market_zcyc(engine="stock")

        assert "zcyc" in result


# ============================================================
# market_orderbook_info
# ============================================================

class TestMarketOrderbookInfo:
    def test_success(self, mocker, mock_response):
        json_data = {
            "orderbook": {
                "columns": ["bid", "offer"],
                "data": [[100.0, 101.0]],
            }
        }

        get = mocker.patch.object(engines.rq, "get", return_value=mock_response(json_data=json_data))
        check = mocker.patch.object(engines, "check_connection")

        result = engines.market_orderbook_info("stock", "shares")

        assert "orderbook" in result
        assert result["orderbook"].height == 1
        check.assert_called_once()

    def test_url_structure(self, mocker, mock_response):
        get = mocker.patch.object(engines.rq, "get", return_value=mock_response(json_data={}))
        mocker.patch.object(engines, "check_connection")

        engines.market_orderbook_info("stock", "shares", lang="ru")

        url = get.call_args.args[0]
        assert "engines/stock/markets/shares.json" in url
        assert "lang=ru" in url
        assert url.endswith("/orderbook")

    def test_empty_response(self, mocker, mock_response):
        mocker.patch.object(engines.rq, "get", return_value=mock_response(json_data={}))
        mocker.patch.object(engines, "check_connection")

        result = engines.market_orderbook_info("stock", "shares")

        assert result == {}

    def test_multiple_tables(self, mocker, mock_response):
        json_data = {
            "orderbook": {
                "columns": ["bid"],
                "data": [[100]],
            },
            "metadata": {
                "columns": ["key"],
                "data": [["value"]],
            },
        }

        mocker.patch.object(engines.rq, "get", return_value=mock_response(json_data=json_data))
        mocker.patch.object(engines, "check_connection")

        result = engines.market_orderbook_info("stock", "shares")

        assert len(result) == 2
        assert "orderbook" in result
        assert "metadata" in result


# ============================================================
# res_intra
# ============================================================

class TestResIntra:
    def test_single_batch(self, mocker):
        df = pl.DataFrame({"SECID": ["S0", "S1", "S2"]})
        read_csv = mocker.patch.object(engines.pl, "read_csv", return_value=df)
        mocker.patch.object(engines, "check_connection")
        mocker.patch("iss.engines.tqdm", side_effect=lambda it, **kw: it, create=True)

        result = engines.res_intra(
            engine="stock",
            market="shares",
            securities=["S0", "S1", "S2"],
            verbose=False,
        )

        assert len(result) == 3
        assert read_csv.call_count == 1

    def test_multiple_batches(self, mocker):
        first = pl.DataFrame({"SECID": [f"S{i}" for i in range(10)]})
        second = pl.DataFrame({"SECID": ["S10", "S11"]})

        mocker.patch.object(engines.pl, "read_csv", side_effect=[first, second])
        mocker.patch.object(engines, "check_connection")
        mocker.patch("iss.engines.tqdm", side_effect=lambda it, **kw: it, create=True)

        securities = [f"S{i}" for i in range(12)]
        result = engines.res_intra(
            engine="stock",
            market="shares",
            securities=securities,
            verbose=False,
        )

        assert len(result) == 12
        assert engines.pl.read_csv.call_count == 2

    def test_exactly_10_securities_single_batch(self, mocker):
        df = pl.DataFrame({"SECID": [f"S{i}" for i in range(10)]})
        mocker.patch.object(engines.pl, "read_csv", return_value=df)
        mocker.patch.object(engines, "check_connection")
        mocker.patch("iss.engines.tqdm", side_effect=lambda it, **kw: it, create=True)

        securities = [f"S{i}" for i in range(10)]
        result = engines.res_intra(
            engine="stock",
            market="shares",
            securities=securities,
            verbose=False,
        )

        assert len(result) == 10
        assert engines.pl.read_csv.call_count == 1

    def test_empty_securities_returns_empty_dict(self, mocker):
        mocker.patch.object(engines, "check_connection")
        mocker.patch("iss.engines.tqdm", side_effect=lambda it, **kw: it, create=True)

        result = engines.res_intra(
            engine="stock",
            market="shares",
            securities=[],
            verbose=False,
        )

        assert result == {}

    def test_filters_by_secid(self, mocker):
        df = pl.DataFrame({"SECID": ["S0", "S1", "S2"], "VALUE": [1, 2, 3]})
        mocker.patch.object(engines.pl, "read_csv", return_value=df)
        mocker.patch.object(engines, "check_connection")
        mocker.patch("iss.engines.tqdm", side_effect=lambda it, **kw: it, create=True)

        result = engines.res_intra(
            engine="stock",
            market="shares",
            securities=["S0", "S1", "S2"],
            verbose=False,
        )

        assert result["S0"].height == 1
        assert result["S0"]["VALUE"][0] == 1
        assert result["S1"]["VALUE"][0] == 2

    def test_missing_security_returns_empty_df(self, mocker):
        df = pl.DataFrame({"SECID": ["S0"], "VALUE": [1]})
        mocker.patch.object(engines.pl, "read_csv", return_value=df)
        mocker.patch.object(engines, "check_connection")
        mocker.patch("iss.engines.tqdm", side_effect=lambda it, **kw: it, create=True)

        result = engines.res_intra(
            engine="stock",
            market="shares",
            securities=["S0", "MISSING"],
            verbose=False,
        )

        assert result["MISSING"].height == 0
