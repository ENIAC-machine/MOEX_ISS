<a id="iss.aio.base"></a>

# iss.aio.base

<a id="iss.aio.base.AsyncTickerFunctionFactory"></a>

## AsyncTickerFunctionFactory Objects

```python
class AsyncTickerFunctionFactory(AbstractFunctionFactory)
```

Decorator class to be used to create async ticker functions

<a id="iss.aio.base.AsyncTickerFunctionFactory.__init__"></a>

#### \_\_init\_\_

```python
def __init__(base_url: str,
             unrelated_args: Iterable[str] | None = None,
             to_format: Iterable[str] = ['tickers']) -> None
```

base_url: str - a formated string (like 'Hello, {}!')

<a id="iss.aio.base.security_specs"></a>

#### security\_specs

```python
@AsyncTickerFunctionFactory(
    base_url='https://iss.moex.com/iss/securities/{}.csv?')
async def security_specs(
    tickers: str | Iterable[str],
    primary_board: bool | Iterable[bool] = True,
    start: int | Iterable[int] = 0,
    lang: str | Iterable[str] = 'en',
    verbose: bool = True,
    out: str | Iterable[str] = 'polars'
) -> dict[str, pl.DataFrame | pl.LazyFrame | pd.DataFrame]
```

Get the description of a single of multiple security(-ies). 
Corresponds to the api call from docs: https://iss.moex.com/iss/reference/193

Inputs:

    tickers:str | Iterable[str] - ticker(-s) of the security

    primary_board:bool | Iterable[bool] - show only the primary board info, default is True

    start:int | Iterable[int] - index of line to start from, default is 0 

    verbose:bool - verbosity, default is True

    lang: str | Iterable[str] - language of output, can be 'en' or 'ru', default is en

    out: str | Iterable[str] - output format for each ticker, can be 'polars', 'pandas' or
        'polars_lazy'

Outputs:

    ticker_descs: dict[str, pl.DataFrame | pl.LazyFrame | pd.DataFrame] - python dictionary with
        keys as tickers and values as the dataframes with their descriptions

<a id="iss.aio.base.indxs4secs"></a>

#### indxs4secs

```python
@AsyncTickerFunctionFactory(
    base_url="https://iss.moex.com/iss/securities/{}/indices.csv?")
async def indxs4secs(
    tickers: str | Iterable[str],
    only_actual: bool | Iterable[bool] = True,
    lang: str | Iterable[str] = 'en',
    verbose: bool = True,
    out: str | Iterable[str] = 'polars'
) -> dict[str, pd.DataFrame | pl.LazyFrame | pl.DataFrame]
```

Get the indices in which the given security(-ies) is(are) mentioned.
    Corresponds to the api call from docs: https://iss.moex.com/iss/reference/199

Inputs:

    tickers:[str, list, np.ndarray] - ticker(-s) to consider

    only_actual:bool - flag to return only indices still in use, default is True

    verbose:bool - verbosity flag, default is False

Outputs:

    ticker_data: dict[str, pd.DataFrame, pl.LazyFrame, pl.DataFrame] - python dictionary of
        structure ticker : ticker_data

<a id="iss.aio.base.agg_info"></a>

#### agg\_info

```python
@AsyncTickerFunctionFactory(
    base_url='https://iss.moex.com/iss/securities/{}/aggregates.csv?')
async def agg_info(
    tickers: str | Iterable[str],
    dates: str | Iterable[str] = ('2020-06-05', ),
    lang: str | Iterable[str] = ('en', ),
    verbose: bool = True,
    out: str | Iterable[str] = 'polars'
) -> dict[str, pd.DataFrame | pl.LazyFrame | pl.DataFrame]
```

Get aggregate info on one or multiple indices/securities.
Corresponds to the api call from docs: https://iss.moex.com/iss/reference/201 

Inputs:

    tickers: str | Iterable[str] - a single ticker or a list of tickers

    dates: str | Iterable[str] - a single or an Iterable of dates
        It's assumed that each date corresponds to the security/ stock of the same index.

    verbose: bool - verbosity toggle, default is False

    lang: str | Iterable[str] - language of output, can be 'en' or 'ru', default is en


Outputs:

    ticker_data: dict[str, pd.DataFrame, pl.LazyFrame, pl.DataFrame] - dict with strings as 
        tickers and values as respective dataframes for each ticker

