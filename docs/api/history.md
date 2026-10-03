<a id="iss.history"></a>

# iss.history

<a id="iss.history.download"></a>

#### download

```python
@OffsetFunctionFactory(
    base_url=
    'https://iss.moex.com/iss/history/engines/{}/markets/{}/securities/{}.csv?',
    unrelated_args=('verbose', 'lang', 'timeout', 'out'),
    to_format=('engine', 'market', 'security'),
    increment_arg='start',
    increment=100,
    ignore_end=3)
def download(security: str,
             engine: str = 'stock',
             market: str = 'shares',
             sort_order: str = 'asc',
             st: dt.date = dt.date(2014, 1, 1),
             end: dt.date = dt.date(2037, 12, 31),
             numtrades: int = 0,
             tradingsession: str = '',
             marketprice_board: bool = True,
             verbose: bool = False,
             lang: str = 'en',
             timeout: int = 5,
             out: str = 'polars') -> dict[str, int | str | bool]
```

Download information on a security for given engine and market and for a given date range

Inputs:
    security: str - name of the security
    engine: str - target engine
    market: str - target market
    sort_order: str - order of sorting data upon receiving, can be `asc` or `desc`
    st: datetime.date - start date to get info for
    end: datetime.date - end date to get info for
    numtrades: int - minimal number of trades with a security
    tradingsession: str - session of choice (only for funds' market)
        0 - Moring session
        1 - Day session (main)
        2 - Evening session
        3 - Overall
    marketprice_board: bool - give data only for the main trading session, if True - means activate this feature
    verbose: bool - verbosity flag
    lang: str - preffered language, can be `en` or `ru`
    timeout: int - timeout in seconds, defaults to 5
    out: str - output format, can be `polars`, `pandas` or `lazy` for polars.LazyFrame, defaults to `polars`

Outputs:
    candles as a DataFrame of choice

<a id="iss.history.trading_listing"></a>

#### trading\_listing

```python
@prep_kwargs(unrelated_args=('lang', 'verbose'))
def trading_listing(engine: str | Iterable[str] = 'stock',
                    market: str | Iterable[str] = 'shares',
                    status: str | Iterable[str] = 'all',
                    lang: str | Iterable[str] = 'en',
                    idx_st: int | Iterable[int] = 0,
                    verbose: bool = True) -> dict[str, pl.DataFrame]
```

Get the list of traded/not-traded instruments. 
IMOEX ISS reference: https://iss.moex.com/iss/reference/489

Inputs:
    engine:[str, List[str], np.ndarray] - target engine(-s), default is stock

    market:[str, List[str], np.ndarray] - target market(-s), default is shares

    status:[str, List[str], np.ndarray] - status of the group of securities you want to fetch. Can take values 'traded', 'not traded', 'all', default is 'all'

    lang:[str, List[str], np.ndarray] - language of the output, can be 'en' or 'ru', default is 'en'

    idx_st:[int, List[int], np.ndarray] - index of the start of the output dataframe, default is 0

    verbose:bool - verbosity toggle, default is False

Output:
    data:[dict, pd.DataFrame] - pandas dataframe with all of the data if only one of each value was given, otherwise dictionary where keys are engine|market
                                and values are data on the respective engine+market combination

