<a id="iss.base"></a>

# iss.base

<a id="iss.base.AbstractFunctionFactory"></a>

## AbstractFunctionFactory Objects

```python
class AbstractFunctionFactory(ABC)
```

<a id="iss.base.AbstractFunctionFactory.__init__"></a>

#### \_\_init\_\_

```python
def __init__(base_url: str, unrelated_args: Iterable[str],
             to_format: Iterable[str]) -> None
```

Inputs:
    base_url: str - the url with `{}` for values to be input via `.format` method
        that will be used as base, later it is expected that arguments will be urlencoded
        onto it to send via the GET request
    unrelated_args: Iterable[str] - the arguments that will neither be formatted nor 
        will be encoded into the url as params
    to_format: Iterable[str] - the arguments to be used with `.format` to format a base_url

<a id="iss.base.AbstractFunctionFactory.__call__"></a>

#### \_\_call\_\_

```python
@abstractmethod
def __call__(func: Callable) -> Callable[..., Any]
```

The core decorator logic is expected to be here

<a id="iss.base.TickerFunctionFactory"></a>

## TickerFunctionFactory Objects

```python
class TickerFunctionFactory(AbstractFunctionFactory)
```

Decorator class to be used to create ticker functions

<a id="iss.base.TickerFunctionFactory.__init__"></a>

#### \_\_init\_\_

```python
def __init__(base_url: str,
             unrelated_args: Iterable[str] | None = None,
             to_format: Iterable[str] = ['tickers']) -> None
```

Inputs:
    base_url: str - a formated string as a base for our GET request 
    unrelated_args: Iterable[str] | None - the arguments that will neither be formatted nor 
        will be encoded into the url as params
    to_format: Iterable[str] - argumets that `base_url` lacks

<a id="iss.base.TickerFunctionFactory.__call__"></a>

#### \_\_call\_\_

```python
def __call__(
    func: Callable
) -> Callable[..., dict[str, pd.DataFrame | pl.DataFrame | pl.LazyFrame]]
```

Return decorator when called
Inputs:
    func: Callable

<a id="iss.base.QueryFunctionFactory"></a>

## QueryFunctionFactory Objects

```python
class QueryFunctionFactory(AbstractFunctionFactory)
```

Factory for queries with several outputs

<a id="iss.base.QueryFunctionFactory.__init__"></a>

#### \_\_init\_\_

```python
def __init__(base_url: str, unrelated_args: Iterable[str],
             to_format: Iterable[str]) -> None
```

Inputs:
    base_url: str - the base url for the GET request
    unrelated_args: Iterable[str] - arguments that are neither arguments for the function
        according to its MOEX ISS API reference nor the ones in `to_format` argument
    to_format: arguments that are missing in the base_url

<a id="iss.base.QueryFunctionFactory.__call__"></a>

#### \_\_call\_\_

```python
def __call__(
    func: Callable[..., dict[str, pl.DataFrame]]
) -> Callable[..., dict[str, pl.DataFrame]]
```

Return decorator when called
Inputs:
    func: Callable

<a id="iss.base.OffsetFunctionFactory"></a>

## OffsetFunctionFactory Objects

```python
class OffsetFunctionFactory(AbstractFunctionFactory)
```

<a id="iss.base.OffsetFunctionFactory.__call__"></a>

#### \_\_call\_\_

```python
def __call__(
    func: Callable[..., dict[str, pl.DataFrame]]
) -> Callable[..., pl.DataFrame | pl.LazyFrame | pd.DataFrame]
```

Return decorator when called
Inputs:
    func: Callable

<a id="iss.base.list_securities"></a>

#### list\_securities

```python
@OffsetFunctionFactory(base_url='https://iss.moex.com/iss/securities.csv?',
                       unrelated_args={'out', 'verbose', 'timeout', 'total'},
                       to_format=(),
                       trouble_cols=('emitent_id', 'emitent_inn',
                                     'emitent_okpo', 'regnumber'))
def list_securities(
        q: str,
        engine: str = 'stock',
        trading: bool = True,
        market: str = 'shares',
        group_by: str = '',
        start: int = 0,
        end: int | None = None,
        group_by_filter: str = '',
        verbose: bool = True,
        lang: str = 'en',
        out: str = 'polars',
        timeout: int = 5) -> pd.DataFrame | pl.DataFrame | pl.LazyFrame
```

List available securities

Inputs:
    q: str - query, can be ticker, name, ISIN, emitent's id, gov. registry number
        queries of length less than 3 are ignored

    engine: str - engine to fetch info from

    trading: bool - whether you want to search among the currently traded assets

    market: str - engine's market to getch info from

    group_by: str - field to group the values by

    start: int - start index to search from

    end: int | None - end index, default is to search until all info is exhausted

    group_by_filter: str - fields to filter in `groupby` operation, depends on group_by arg

    verbose: bool - verbosity flag

    lang: str - language of output, can be `en` or `ru`

    out: str - output format, defaults to `polars`

    timeout: int - timeout time between failed GET requests, in seconds

Outputs:
    A DataFrame of preffered type with the data on securities that satisfy the query

<a id="iss.base.security_specs"></a>

#### security\_specs

```python
@TickerFunctionFactory(base_url='https://iss.moex.com/iss/securities/{}.csv?')
def security_specs(
        tickers: str | Iterable[str],
        primary_board: bool | Iterable[bool] = True,
        start: int | Iterable[int] = 0,
        lang: str | Iterable[str] = 'en',
        verbose: bool = True,
        out: str | Iterable[str] = 'polars',
        timeout: int = 5
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

<a id="iss.base.indxs4secs"></a>

#### indxs4secs

```python
@TickerFunctionFactory(
    base_url="https://iss.moex.com/iss/securities/{}/indices.csv?")
def indxs4secs(
        tickers: str | Iterable[str],
        only_actual: bool | Iterable[bool] = True,
        lang: str | Iterable[str] = 'en',
        verbose: bool = True,
        out: str | Iterable[str] = 'polars',
        timeout: int = 5
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

<a id="iss.base.agg_info"></a>

#### agg\_info

```python
@TickerFunctionFactory(
    base_url='https://iss.moex.com/iss/securities/{}/aggregates.csv?')
def agg_info(tickers: str | Iterable[str],
             dates: str | Iterable[str] = ('2020-06-05', ),
             lang: str | Iterable[str] = ('en', ),
             verbose: bool = True,
             out: str | Iterable[str] = 'polars',
             timeout: int = 5) -> dict[str, str | bool | Iterable[str]]
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

<a id="iss.base.market_info"></a>

#### market\_info

```python
def market_info(is_traded: bool = True,
                hide_inactive: bool = True,
                lang: str = 'en') -> dict[str, pl.DataFrame]
```

Get general market info
Correponds to https://iss.moex.com/iss/reference/543

Inputs:
    is_traded:bool - flag to show only currently traded boardgroups, default is True

    hide_inactive:bool - hide inactive security groups, default is True

    verbose:bool - verbosity flag, default is False

    lang:str - language of output, can be 'en' or 'ru', default is en

Outputs:
    dfs:dict - info about the market

<a id="iss.base.turnovers"></a>

#### turnovers

```python
def turnovers(is_tonight_session: bool = True,
              start: dt.date | None = None,
              end: dt.date = dt.datetime.now(),
              verbose: bool = False,
              lang: str = 'en',
              out: str = 'polars',
              timeout: int = 5) -> pl.DataFrame | pl.LazyFrame | pd.DataFrame
```

Get turnovers for markets for a specific date or a range of dates

Inputs:
is_tonight_session:bool - show turnovers for the evening session

dt_st:[str, datetime.datetime] - start date in the format 'Y-M-D' to get the data from,
default is None

dt_end:[str, datetime.datetime] - end date, same format, default is 'today'

verbose:bool-verbosity flag, default is False

lang:str - language of output, can be 'en' or 'ru', default is en

Note: here the data is extracted from day [dt_st] to day [dt_end], not vice versa!

Outputs:
dfs:dict - dictionary with all the values for dates, dates are keys and pd.DataFrames are values

<a id="iss.base.turnover_cols"></a>

#### turnover\_cols

```python
def turnover_cols(lang: str = 'en', timeout: int = 5) -> pl.DataFrame
```

Get turnover columns description

Inputs:
    lang:str - language of output, can be 'en' or 'ru', default is en


Outputs:
    df:pd.DataFrame - description of turnover columns in the selected language

