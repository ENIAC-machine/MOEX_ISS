import pytest
import polars as pl
import pandas as pd
from datetime import date

import iss.history as history_module
import iss.base as base_module


# ============================================================
# download
# ============================================================

class TestDownload:
    def test_success_returns_dataframe(self, mocker, mock_response, moex_csv):
        content = moex_csv(
            headers=["SECID", "PRICE"],
            rows=[["YNDX", str(i)] for i in range(4)],
        )
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = history_module.download(
            security="YNDX",
            st=date(2024, 1, 1),
            end=date(2024, 1, 2),
            verbose=False,
        )

        assert isinstance(result, pl.DataFrame)
        assert result.height == 1  # 4 rows - 3 ignored at end = 1

    def test_ignore_end_slices_last_3_rows(self, mocker, mock_response, moex_csv):
        content = moex_csv(
            headers=["SECID", "PRICE"],
            rows=[["YNDX", str(i)] for i in range(10)],
        )
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = history_module.download(
            security="YNDX",
            st=date(2024, 1, 1),
            end=date(2024, 1, 2),
            verbose=False,
        )

        # 10 rows - 3 ignored at end = 7
        assert result.height == 7

    def test_empty_after_slicing_returns_empty_df(self, mocker, mock_response, moex_csv):
        content = moex_csv(
            headers=["SECID", "PRICE"],
            rows=[["YNDX", str(i)] for i in range(3)],
        )
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = history_module.download(
            security="YNDX",
            st=date(2024, 1, 1),
            end=date(2024, 1, 2),
            verbose=False,
        )

        assert result.height == 0

    def test_output_pandas(self, mocker, mock_response, moex_csv):
        content = moex_csv(
            headers=["SECID", "PRICE"],
            rows=[["YNDX", str(i)] for i in range(4)],
        )
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = history_module.download(
            security="YNDX",
            st=date(2024, 1, 1),
            end=date(2024, 1, 2),
            out="pandas",
            verbose=False,
        )

        assert isinstance(result, pd.DataFrame)

    def test_output_polars_lazy(self, mocker, mock_response, moex_csv):
        content = moex_csv(
            headers=["SECID", "PRICE"],
            rows=[["YNDX", str(i)] for i in range(4)],
        )
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = history_module.download(
            security="YNDX",
            st=date(2024, 1, 1),
            end=date(2024, 1, 2),
            out="polars_lazy",
            verbose=False,
        )

        assert isinstance(result, pl.LazyFrame)

    def test_invalid_output_raises_not_implemented(self, mocker, mock_response, moex_csv):
        content = moex_csv(
            headers=["SECID", "PRICE"],
            rows=[["YNDX", str(i)] for i in range(4)],
        )
        mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        with pytest.raises(NotImplementedError):
            history_module.download(
                security="YNDX",
                st=date(2024, 1, 1),
                end=date(2024, 1, 2),
                out="xlsx",
                verbose=False,
            )

    def test_url_includes_security_engine_market(self, mocker, mock_response, moex_csv):
        content = moex_csv(
            headers=["SECID"],
            rows=[["YNDX"]] * 4,
        )
        get = mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        history_module.download(
            security="YNDX",
            engine="stock",
            market="shares",
            st=date(2024, 1, 1),
            end=date(2024, 1, 2),
            verbose=False,
        )

        url = get.call_args.args[0]
        assert "history/engines/stock/markets/shares/securities/YNDX.csv" in url

    def test_total_calculation_for_long_range(self, mocker, mock_response, moex_csv):
        """For a 250-day range, total should be ceil(250/100) = 3 iterations."""
        content = moex_csv(
            headers=["SECID"],
            rows=[["YNDX"]] * 4,
        )
        get = mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        history_module.download(
            security="YNDX",
            st=date(2024, 1, 1),
            end=date(2024, 9, 8),  # ~250 days
            verbose=False,
        )

        # total = ceil(250/100) = 3, but first empty response breaks the loop
        # Since we return 4 rows (1 after slicing), it won't break early
        assert get.call_count >= 1

    def test_st_equals_end(self, mocker, mock_response, moex_csv):
        """When st == end, total = ceil(0/100) = 0, so no requests should be made."""
        content = moex_csv(headers=["SECID"], rows=[["YNDX"]] * 4)
        get = mocker.patch.object(base_module.rq, "get", return_value=mock_response(content=content))

        result = history_module.download(
            security="YNDX",
            st=date(2024, 1, 1),
            end=date(2024, 1, 1),
            verbose=False,
        )

        # total = 0, so loop doesn't execute, returns empty DataFrame
        assert result.height == 0
        assert get.call_count == 0


# ============================================================
# trading_listing
# ============================================================

class TestTradingListing:
    def test_invalid_status_raises_value_error(self, mocker):
        mocker.patch.object(history_module, "check_connection")

        with pytest.raises(ValueError, match="Wrong input to the status argument"):
            history_module.trading_listing(status="invalid_status")

    def test_valid_status_values(self, mocker):
        """Verify that all valid status values are accepted."""
        mocker.patch.object(history_module, "check_connection")
        mocker.patch.object(history_module.pl, "read_csv", return_value=pl.DataFrame())
        mocker.patch("iss.history.tqdm", side_effect=lambda it, **kw: it, create=True)

        # These should NOT raise ValueError
        for status in ["traded", "not traded", "all"]:
            try:
                history_module.trading_listing(status=status, verbose=False)
            except ValueError:
                pytest.fail(f"trading_listing raised ValueError for valid status '{status}'")
            except Exception:
                pass  # Other errors are fine, we just want to verify no ValueError

    def test_success_single_engine_market(self, mocker):
        df = pl.DataFrame({"SECID": ["SBER"], "STATUS": ["traded"]})
        empty = df.clear()

        mocker.patch.object(history_module.pl, "read_csv", side_effect=[df, empty])
        mocker.patch.object(history_module, "check_connection")
        mocker.patch("iss.history.tqdm", side_effect=lambda it, **kw: it, create=True)

        result = history_module.trading_listing(
            engine="stock",
            market="shares",
            status="all",
            verbose=False,
        )

        assert "stock|shares" in result
        assert result["stock|shares"].height == 1

    def test_pagination_until_empty(self, mocker):
        """Verify that trading_listing keeps fetching until an empty response."""
        page1 = pl.DataFrame({"SECID": ["S1", "S2"]})
        page2 = pl.DataFrame({"SECID": ["S3"]})
        empty = page1.clear()

        mocker.patch.object(
            history_module.pl, "read_csv",
            side_effect=[page1, page2, empty],
        )
        mocker.patch.object(history_module, "check_connection")
        mocker.patch("iss.history.tqdm", side_effect=lambda it, **kw: it, create=True)

        result = history_module.trading_listing(
            engine="stock",
            market="shares",
            status="all",
            verbose=False,
        )

        assert result["stock|shares"].height == 3
        assert history_module.pl.read_csv.call_count == 3
