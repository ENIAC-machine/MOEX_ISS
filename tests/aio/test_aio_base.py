import pytest
import asyncio
import pandas as pd
import polars as pl
from unittest.mock import patch, MagicMock, AsyncMock
import sys

# ==========================================
# 1. MOCKING EXTERNAL DEPENDENCIES
# ==========================================
# We mock `ISS` (uppercase) because your base.py currently imports from `ISS._utils`.
# This prevents ImportErrors and isolates the async logic for testing.

mock_utils = MagicMock()
mock_utils.check_connection = MagicMock()
mock_utils.ens_tuple = lambda x: (x,) if not isinstance(x, (list, tuple, set)) else tuple(x)

def mock_ens_same_length(d):
    lengths = {k: len(v) for k, v in d.items() if isinstance(v, (list, tuple))}
    if not lengths: return d
    max_len = max(lengths.values())
    for k, v in d.items():
        if isinstance(v, (list, tuple)) and len(v) == 1:
            d[k] = tuple(list(v) * max_len)
    return d

mock_utils.ens_same_length = mock_ens_same_length

sys.modules['ISS'] = MagicMock()
sys.modules['ISS._utils'] = mock_utils
sys.modules['ISS.base'] = MagicMock()
sys.modules['ISS.base'].AbstractFunctionFactory = object

# Import the module under test AFTER mocking
from iss.aio.base import AsyncTickerFunctionFactory, security_specs

# ==========================================
# 2. TESTS
# ==========================================

@pytest.mark.asyncio
async def test_url_construction_and_params():
    """Verify that the URL is formatted correctly and parameters are encoded."""
    mock_df = pl.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    
    with patch('iss.aio.base.AsyncTickerFunctionFactory._fetch_ticker_info', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_df
        
        # Trigger execution with 'pandas' output to bypass the 'polars' bug in the original code
        await security_specs(tickers='SBER', primary_board=False, start=10, lang='ru', verbose=False, out='pandas')
        
        expected_base = 'https://iss.moex.com/iss/securities/SBER.csv?'
        mock_fetch.assert_called_once()
        actual_url = mock_fetch.call_args[0][0]
        
        assert actual_url.startswith(expected_base)
        assert 'primary_board=False' in actual_url
        assert 'start=10' in actual_url
        assert 'lang=ru' in actual_url

@pytest.mark.asyncio
async def test_output_formats():
    """Test that different output formats return the correct object types."""
    mock_df = pl.DataFrame({"ticker": ["SBER"]})
    
    with patch('iss.aio.base.AsyncTickerFunctionFactory._fetch_ticker_info', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_df
        
        # Test Pandas
        res_pd = await security_specs(tickers='SBER', verbose=False, out='pandas')
        assert isinstance(res_pd['SBER'], pd.DataFrame)
        
        # Test Polars Lazy
        res_lazy = await security_specs(tickers='SBER', verbose=False, out='polars_lazy')
        assert isinstance(res_lazy['SBER'], pl.LazyFrame)

@pytest.mark.asyncio
async def test_multiple_tickers_intended_behavior():
    """
    Test that multiple tickers return distinct DataFrames.
    NOTE: This test expects the FIXED behavior. It will fail on the original 
    base.py code due to the bug in the result mapping loop.
    """
    mock_df1 = pl.DataFrame({"ticker": ["SBER"]})
    mock_df2 = pl.DataFrame({"ticker": ["GAZP"]})
    
    with patch('iss.aio.base.AsyncTickerFunctionFactory._fetch_ticker_info', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = [mock_df1, mock_df2]
        
        result = await security_specs(tickers=['SBER', 'GAZP'], verbose=False, out='pandas')
       
        print(f'res: {result['SBER']['ticker'][0]}')

        #rint(result['SBER'])

        # Intended behavior: distinct results for each ticker
        assert result['SBER']['ticker'][0] == "SBER"
        assert result['GAZP']['ticker'][0] == "GAZP"

@pytest.mark.asyncio
async def test_default_polars_output():
    """
    Test that out='polars' returns a standard polars DataFrame.
    (The previous tests checked 'pandas' and 'polars_lazy', but skipped the default 'polars').
    """
    mock_df = pl.DataFrame({"ticker": ["SBER"]})
    
    with patch('iss.aio.base.AsyncTickerFunctionFactory._fetch_ticker_info', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_df
        
        res = await security_specs(tickers='SBER', verbose=False, out='polars')
        
        # Must be a DataFrame, but NOT a LazyFrame
        assert isinstance(res['SBER'], pl.DataFrame)
        assert not isinstance(res['SBER'], pl.LazyFrame)

@pytest.mark.asyncio
async def test_invalid_output_format():
    """Test that an unsupported output format correctly raises NotImplementedError."""
    mock_df = pl.DataFrame({"ticker": ["SBER"]})
    
    with patch('iss.aio.base.AsyncTickerFunctionFactory._fetch_ticker_info', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_df
        
        with pytest.raises(NotImplementedError):
            await security_specs(tickers='SBER', verbose=False, out='xml')

@pytest.mark.asyncio
async def test_parameter_alignment_multiple_tickers():
    """
    Test that when passing lists of parameters, they correctly align 
    with their respective tickers in the generated URLs.
    This validates that `ens_same_length` and your index mapping work correctly.
    """
    mock_df = pl.DataFrame({"col": [1]})
    
    with patch('iss.aio.base.AsyncTickerFunctionFactory._fetch_ticker_info', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_df
        
        # Pass lists of parameters that should map 1-to-1 with the tickers
        await security_specs(
            tickers=['SBER', 'GAZP'], 
            lang=['en', 'ru'], 
            start=[0, 10],
            verbose=False, 
            out='pandas'
        )
        
        assert mock_fetch.call_count == 2
        
        url1 = mock_fetch.call_args_list[0][0][0]
        url2 = mock_fetch.call_args_list[1][0][0]
        
        # Verify SBER got the first set of parameters
        assert 'SBER' in url1
        assert 'lang=en' in url1
        assert 'start=0' in url1
        
        # Verify GAZP got the second set of parameters
        assert 'GAZP' in url2
        assert 'lang=ru' in url2
        assert 'start=10' in url2

@pytest.mark.asyncio
async def test_fetch_ticker_info_csv_args():
    """
    Test that the internal _fetch_ticker_info method calls polars.read_csv 
    with the exact MOEX-specific arguments (skip_rows, encoding, etc.).
    """
    with patch('iss.aio.base.pl.read_csv') as mock_read_csv:
        mock_read_csv.return_value = pl.DataFrame({"a": [1]})
        
        # Mock the event loop's executor to run the lambda synchronously for the test
        mock_loop = MagicMock()
        async def mock_run_in_executor(executor, func):
            return func()
        mock_loop.run_in_executor = mock_run_in_executor
        
        with patch('iss.aio.base.asyncio.get_running_loop', return_value=mock_loop):
            await AsyncTickerFunctionFactory._fetch_ticker_info("http://fake-url.com")
            
            # Verify MOEX API specific formatting is strictly enforced
            mock_read_csv.assert_called_once_with(
                "http://fake-url.com",
                encoding='cp1251',
                skip_rows=2,
                has_header=True,
                quote_char=None,
                separator=';'
            )
