<a id="iss.engines"></a>

# iss.engines

<a id="iss.engines.available_engines"></a>

#### available\_engines

```python
def available_engines(lang: str = 'en') -> pl.DataFrame
```

Corresponds to iss.moex.com/iss/reference/391
Lists available engines

Inputs:
    lang: str - preffered language, can be `en` or `ru`

<a id="iss.engines.engine_info"></a>

#### engine\_info

```python
def engine_info(engine: str, lang: str = 'en') -> dict[str, pl.DataFrame]
```

https://iss.moex.com/iss/reference/397

Gives info about engine

Inputs:
    engine: str - engine to give info about
    lang: str - preffered language, can be `en` or `ru`

Outputs:
    engine info in dict format

<a id="iss.engines.engine_zcyc"></a>

#### engine\_zcyc

```python
@QueryFunctionFactory(
    base_url='https://iss.moex.com/iss/engines/{}/zcyc.json?',
    unrelated_args=['engine'],
    to_format=['engine'])
def engine_zcyc(engine: str,
                date: str,
                lang: str = 'en') -> dict[str, pl.DataFrame]
```

Zero-coupon yield curve
Corresponds to https://iss.moex.com/iss/reference/417

Inputs:
    engine: str - engine of choice 
    date: str - date to look zcyc upon
    lang: str - preffered language, can be `en` or `ru`

Outputs:    
    zcyc info

<a id="iss.engines.candles"></a>

#### candles

```python
def candles(
        tickers: str | Iterable[str],
        st: date | Iterable[date],
        end: date | Iterable[date],
        engine: str = 'stock',
        market: str = 'shares',
        interval: int | Iterable[int] = 10,
        verbose: bool = True,
        out: str = 'polars',
        timeout: int = 5
) -> dict[str, pl.DataFrame | pd.DataFrame | pl.LazyFrame]
```

Gives candles per [interval] minutes for selected interval

Inputs:
    tickers: str | Iterable[str] - target tickers
    st: date | Iterable[date] - start date(-s)
    end: date | Iterable[date] - end date(-s)
    engine: str - target engine 
    market: str - target market 
    interval: int | Iterable[int] - desired interval, defaults to 10 minutes 
    verbose: bool - verbosity flag 
    out: str - output format, can be `polars`, `pandas` or `lazy` for pl.LazyFrame, defaults to `polars`
    timeout: int - timeout time in seconds, defaults to 5 secs 

Outputs:    
    dict with candle info with tickers as keys and candle info as values

<a id="iss.engines.available_markets"></a>

#### available\_markets

```python
def available_markets(engine: str, lang: str = 'en') -> pl.DataFrame
```

Corresponds to https://iss.moex.com/iss/reference/343
Gives info on available markets for a target engine 

Inputs:
    engine: str - target engine 
    lang: str - preffered language, can be `en` or `ru`

Outputs:
    market info as a polars DataFrame

<a id="iss.engines.market_info"></a>

#### market\_info

```python
@QueryFunctionFactory(
    base_url='https://iss.moex.com/iss/engines/{}/markets/{}.json?',
    unrelated_args=('engine', 'market'),
    to_format=('engine', 'market'))
def market_info(engine: str, market: str, lang: str = 'en') -> dict[str, str]
```

Correponds to https://iss.moex.com/iss/reference/351
Gives info about a singular market for some target engine 

Inputs:
    engine: str - target engine
    market: str - target market
    lang: str - preffered language, can be `en` or `ru`

Outputs:
    market_info as a dict with field names as keys and info as values

<a id="iss.engines.secstats"></a>

#### secstats

```python
def secstats(
    engine: str,
    market: str,
    lang: str = 'en',
    trading_session: int = 1,
    securities: Iterable[str] = ('GAZP', ),
    board_id: Sequence[str] = ('TQBR', )
) -> pl.DataFrame
```

Get the intermediate results for the trading day
Corresponds to the method in docs https://iss.moex.com/iss/reference/403

Inputs:
    engine: str - target engine
    market: str - target market
    lang: str - preffered language, can be `en` or `ru`
    trading_session: int - show data for some session,
        1 - Day session (main)
        2 - Evening session
        3 - Overall
    securities: Iterable[str] - array of target securities, no more than 10 are allowed
    board_id: Iterable[str] - board filters, no more than 10 are allowed

<a id="iss.engines.market_zcyc"></a>

#### market\_zcyc

```python
@QueryFunctionFactory(
    base_url='https://iss.moex.com/iss/engines/{}/markets/zcyc.json?',
    unrelated_args=('engine', ),
    to_format=('engine', ))
def market_zcyc(engine: str,
                lang: str = 'en',
                frm: str = '2000-01-01',
                tll: str = '2100-01-01',
                start: int = 0) -> dict[str, pl.DataFrame]
```

Data deprecated since 2018-01-03
Correponds to https://iss.moex.com/iss/reference/405

<a id="iss.engines.market_orderbook_info"></a>

#### market\_orderbook\_info

```python
def market_orderbook_info(engine: str,
                          market: str,
                          lang: str = 'en') -> dict[str, pl.DataFrame]
```

Gives info on the orderbook for the particular market
Corresponds to https://iss.moex.com/iss/reference/411

Inputs:    
    engine: str - target engine
    market: str - target market
    lang: str - preffered language, can be `en` or `ru`

Outputs:
    orderbook info with field as key and info as value in a python dictionary

<a id="iss.engines.res_intra"></a>

#### res\_intra

```python
def res_intra(engine: str | Iterable[str],
              market: str | Iterable[str],
              secstats: int | Iterable[int] = 0,
              trsession: int | Iterable[int] = 0,
              securities: str | Sequence[str] = '',
              boardid: str | Iterable[str] = '',
              verbose: bool = True,
              lang: str = 'en') -> dict[str, pl.DataFrame]
```

Get the information on the intraday results, only for the fund market

Inputs:

    market:[str, list - trading market, default is None

    secstats:[int, list - intraday results, can be int or iterable, can take 3 possible values:
        1 for the main session, 2 for the evening session, 3 for the general summary, default is None

    trsession:[int, list - session data filter, works identically to secstats in terms of values, 
        default is None

    sec:[str, list - securities to get the stats about

    boardid:[str, list - board id, can be string or iterable, default is None

    verbose:bool - verbosity parameter, default is True so that when you start the function you seem cool or smth, idk

Outputs:
    dfs:[dict, pd.DataFrame] - data on the intraday results, if several engines/ markets are requested returns an array
        with key as the unique engine-market combination and the value as the pd.DataFrame with the info

