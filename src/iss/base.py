import pandas as pd
import polars as pl
import numpy as np
import datetime as dt

import inspect

from tqdm import tqdm
from abc import ABC, abstractmethod
from io import BytesIO
from functools import wraps
from dataclasses import dataclass, make_dataclass, fields
from urllib.parse import urlencode
from typing import Callable, Iterable, Any

from iss._utils import *

'''

This is the basic commands that can't be attributed to any distinct branch of commands in the MOEX ISS API

'''

__all__ = ['list_securities', 'security_specs', 'indxs4secs',
           'agg_info', 'market_info', 'turnovers',
           'turnover_cols']


#TODO: add string literals

class AbstractFunctionFactory(ABC):

    def __init__(self,
                 base_url: str,
                 unrelated_args: Iterable[str],
                 to_format: Iterable[str]
                 ) -> None:
        
        '''
        Inputs:
            base_url: str - the url with `{}` for values to be input via `.format` method
                that will be used as base, later it is expected that arguments will be urlencoded
                onto it to send via the GET request
            unrelated_args: Iterable[str] - the arguments that will neither be formatted nor 
                will be encoded into the url as params
            to_format: Iterable[str] - the arguments to be used with `.format` to format a base_url

        '''

        self.base_url = base_url
        self.unrelated_args = unrelated_args
        self.to_format = to_format

    @abstractmethod
    def __call__(self,
                 func: Callable
                 ) -> Callable[..., Any]:
        
        '''
        The core decorator logic is expected to be here
        '''
        ...


class TickerFunctionFactory(AbstractFunctionFactory):
    '''
    Decorator class to be used to create ticker functions 
    '''

    #define slots cause we are based
    __slots__ = ['base_url', 'unrelated_args', 'to_format']
    
    def __init__(self,
                 base_url: str,
                 unrelated_args: Iterable[str] | None = None,
                 to_format: Iterable[str] = ['tickers']
                 ) -> None:

        '''
        Inputs:
            base_url: str - a formated string as a base for our GET request 
            unrelated_args: Iterable[str] | None - the arguments that will neither be formatted nor 
                will be encoded into the url as params
            to_format: Iterable[str] - argumets that `base_url` lacks
        '''

        if unrelated_args is None:
            unrelated_args = {'verbose', 'out', 'timeout'} 

        super().__init__(base_url, unrelated_args, to_format)


    def __call__(self,
                 func: Callable
                ) -> Callable[..., dict[str, pd.DataFrame | pl.DataFrame | pl.LazyFrame]]:

        '''
        Return decorator when called
        Inputs:
            func: Callable
        '''

        @wraps(func) 
        def wrapper(*args: Any,
                    **kwargs: Any
                    ) -> dict[str, pd.DataFrame | pl.DataFrame | pl.LazyFrame]:

            '''
            Core decorator logic
            For TickerFunctionFactory decorator it is iterating over every ticker and
                storing the full information about the ticker in a dictionary

            '''

            kwargs = func(*args, **kwargs)

            new_kwargs = {k: ens_tuple(v) for k, v in kwargs.items() 
                          if k in self.to_format
                          }

            new_kwargs = ens_same_length(new_kwargs)

            for arg in self.unrelated_args:
                if arg in kwargs:
                    new_kwargs[arg] = kwargs[arg]
            
            kwargs = new_kwargs
            del new_kwargs

            #raise error if shit hits the fan
            check_connection()

            ticker_descs = {}
         
            for idx, ticker in tqdm(enumerate(kwargs['tickers']),
                                    desc='Processing tickers',
                                    disable=not kwargs['verbose'],
                                    leave=False
                                    ):
                
                base_url_i = self.base_url.format(*[kwargs[fm][idx] for fm in self.to_format])
                kwargs_i = {k : v[idx] for k, v in kwargs.items() 
                            if k not in self.unrelated_args and\
                                    k not in self.to_format and\
                                    k != 'tickers'
                            }
                query = rf"{base_url_i}{urlencode(kwargs_i)}"
                res = rq.get(query, timeout=kwargs['timeout'])
                res.raise_for_status()
                ticker_descs[ticker] = pl.read_csv(source=BytesIO(res.content),
                                                   encoding='cp1251',
                                                   skip_rows=2,
                                                   has_header=True,
                                                   quote_char=None,
                                                   separator=';'
                                                   )

                if kwargs['out'] == 'polars_lazy':
                    ticker_descs[ticker] = ticker_descs[ticker].lazy()

                elif kwargs['out'] == 'pandas':
                    ticker_descs[ticker] = ticker_descs[ticker].to_pandas()

                elif kwargs['out'] != 'polars':
                    raise NotImplementedError

            return ticker_descs

        return wrapper 


class QueryFunctionFactory(AbstractFunctionFactory):

    '''
    Factory for queries with several outputs
    '''

    __slots__ = ['base_url', 'unrelated_args', 'to_format']

    def __init__(self,
                 base_url: str,
                 unrelated_args: Iterable[str],
                 to_format: Iterable[str]
                 ) -> None:
        '''
        Inputs:
            base_url: str - the base url for the GET request
            unrelated_args: Iterable[str] - arguments that are neither arguments for the function
                according to its MOEX ISS API reference nor the ones in `to_format` argument
            to_format: arguments that are missing in the base_url
        '''


        super().__init__(base_url, unrelated_args, to_format)

    def __call__(self,
                 func: Callable[..., dict[str, pl.DataFrame]]
                 ) -> Callable[..., dict[str, pl.DataFrame]]:

        '''
        Return decorator when called
        Inputs:
            func: Callable
        '''

        @wraps(func)
        def wrapper(*args: Any,
                    **kwargs: Any
                    ) -> dict[str, pl.DataFrame]:

            '''
            Core decorator logic
            For QueryFunctionFactory it is getting a response
                and mutating it into dictionary with names
                of the sections as keys and corresponding
                DataFrames as values
            '''


            kwargs = func(*args, **kwargs)

            check_connection()
            
            url = self.base_url.format(*[kwargs[arg] for arg in self.to_format]) +\
                    urlencode({k : v for k, v in kwargs.items() if
                               k not in self.unrelated_args and\
                                       k not in self.to_format
                               })

            res = rq.get(url)
            res.raise_for_status()
           
            res = res.json()

            info: dict[str, pl.DataFrame] = {}

            for k in res.keys():
                info[k] = pl.from_records(res[k]['data'], schema=res[k]['columns'], orient='row')

            return info

        return wrapper


class OffsetFunctionFactory(AbstractFunctionFactory):

    __slots__ = ['base_url', 'unrelated_args',
                 'to_format', 'trouble_cols',
                 'increment_arg', 'increment']

    def __init__(self,
                 base_url: str,
                 unrelated_args: Iterable[str],
                 to_format: Iterable[str] = tuple(),
                 trouble_cols: Iterable[str] = tuple(),
                 increment_arg : str = 'start',
                 increment: int | dt.timedelta = 100,
                 ignore_start: int = 0,
                 ignore_end: int | None = None 
                 ) -> None:

        super().__init__(base_url, unrelated_args, to_format)
        self.trouble_cols = trouble_cols
        self.increment = increment
        self.increment_arg = increment_arg
        self.ignore_start = ignore_start
        self.ignore_end = -ignore_end if ignore_end is not None else None

    def __call__(self,
                 func: Callable[..., dict[str, pl.DataFrame]]
                 ) -> Callable[..., pl.DataFrame | pl.LazyFrame | pd.DataFrame]:

        '''
        Return decorator when called
        Inputs:
            func: Callable
        '''

        @wraps(func)
        def wrapper(*args,
                    **kwargs
                    ) -> pl.DataFrame | pl.LazyFrame | pd.DataFrame:

            '''
            Core decorator logic.
            For OffsetFunctionFactory it is iteratively sending a GET request with slightly
                changing parameters the change (offset) is determined by the function
            
            Any function wrapped must also pass the `total` argument, which is `end` - `start`. 
            It was done because these can of different dtype like datetime, so the handling of that
            is outsources to preprocessing inside the function
            '''

            #always expect function to returns locals() 
            kwargs = func(*args, **kwargs)
            
            base_query = self.base_url.format(*[kwargs[nm] for nm in self.to_format])

            dfs = []
           
            for i in tqdm(range(kwargs['total']),
                          desc='Fetching data',
                          disable= not kwargs['verbose']):


                query = base_query + urlencode({k : v for k, v in kwargs.items()
                                                if k not in self.unrelated_args and\
                                                k not in self.to_format
                                                })


                res = rq.get(query, timeout=kwargs['timeout'])
                res.raise_for_status()

                df_tmp = pl.read_csv(source=BytesIO(res.content),
                                     encoding="cp1251",
                                     separator=";",
                                     has_header=True,
                                     quote_char=None,
                                     skip_rows=2,
                                     n_threads=1,
                                     ignore_errors=True)
               
                if bool(self.trouble_cols):
                    #force string on trouble cols
                    df_tmp = df_tmp.with_columns(pl.col(*self.trouble_cols).cast(pl.String, strict=True))
                #cleanup from nulls 
                df_tmp = df_tmp.filter(~pl.all_horizontal(pl.all().is_null()))
                
                #to drop the cursor info etc.
                df_tmp = df_tmp[self.ignore_start:self.ignore_end, :]


                if len(df_tmp) == 0:
                    if kwargs['verbose']:
                        print('No more entries found, finishing early...')
                    break

                dfs.append(df_tmp)

                kwargs.update({self.increment_arg : kwargs[self.increment_arg] + self.increment})

            if len(dfs) == 0:
                return pl.DataFrame()

            #sometimes full columns will be nulls so we use 'vertical_relaxed'
            if kwargs['out'] == 'pandas':
                df = pl.concat(dfs, how='vertical_relaxed').to_pandas()
                
            elif kwargs['out'] == 'polars':
                df = pl.concat(dfs, how='vertical_relaxed')

            elif kwargs['out'] == 'polars_lazy':
                df = pl.concat(map(lambda x: x.lazy(), dfs), how='vertical_relaxed')
            
            else:
                raise NotImplementedError

            return df
               

        return wrapper

#iss/securities
@OffsetFunctionFactory(base_url='https://iss.moex.com/iss/securities.csv?',
                       unrelated_args={'out', 'verbose', 'timeout', 'total'},
                       to_format=(),
                       trouble_cols=('emitent_id', 'emitent_inn', 'emitent_okpo', 'regnumber'))
def list_securities(q: str,
                    engine: str = 'stock',
                    trading: bool = True,
                    market: str = 'shares',
                    group_by: str = '',
                    start: int = 0,
                    end: int | None = None,
                    group_by_filter: str='',
                    verbose: bool=True,
                    lang: str='en',
                    out: str = 'polars',
                    timeout: int = 5
                    ) -> pd.DataFrame | pl.DataFrame | pl.LazyFrame:

    '''
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

    '''

    total = 1_000_000 if end is None else end - start

    return locals()


#/iss/securities/[security]
@TickerFunctionFactory(base_url='https://iss.moex.com/iss/securities/{}.csv?')
def security_specs(tickers: str | Iterable[str],
                   primary_board: bool | Iterable[bool] = True,
                   start: int | Iterable[int] = 0,
                   lang: str | Iterable[str]= 'en',
                   verbose: bool = True,
                   out: str | Iterable[str] = 'polars',
                   timeout: int = 5,
                   ) -> dict[str, pl.DataFrame | pl.LazyFrame | pd.DataFrame]:

    '''

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

    '''

    return locals()

#/iss/securities/[security]/indices
@TickerFunctionFactory(base_url="https://iss.moex.com/iss/securities/{}/indices.csv?")
def indxs4secs(tickers: str | Iterable[str],
               only_actual: bool | Iterable[bool] = True,
               lang: str | Iterable[str] = 'en',
               verbose: bool = True,
               out: str | Iterable[str] = 'polars',
               timeout: int = 5,
               ) -> dict[str, pd.DataFrame | pl.LazyFrame | pl.DataFrame]:

    '''

    Get the indices in which the given security(-ies) is(are) mentioned.
        Corresponds to the api call from docs: https://iss.moex.com/iss/reference/199

    Inputs:
        
        tickers:[str, list, np.ndarray] - ticker(-s) to consider

        only_actual:bool - flag to return only indices still in use, default is True

        verbose:bool - verbosity flag, default is False

    Outputs:
        
        ticker_data: dict[str, pd.DataFrame, pl.LazyFrame, pl.DataFrame] - python dictionary of
            structure ticker : ticker_data

    '''
    return locals()

#/iss/securities/[security]/aggregates
@TickerFunctionFactory(base_url='https://iss.moex.com/iss/securities/{}/aggregates.csv?')
def agg_info(tickers: str | Iterable[str],
             dates: str | Iterable[str] = ('2020-06-05',),
             lang: str | Iterable[str]= ('en',),
             verbose: bool = True,
             out: str | Iterable[str] = 'polars',
             timeout: int = 5,
             ) -> dict[str, str | bool | Iterable[str]]:
    '''

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
    '''
    return locals()

#/iss/index 
def market_info(is_traded: bool = True,
                hide_inactive: bool = True,
                lang: str = 'en'
                ) -> dict[str, pl.DataFrame]:

    '''

    Get general market info
    Correponds to https://iss.moex.com/iss/reference/543

    Inputs:
        is_traded:bool - flag to show only currently traded boardgroups, default is True
        
        hide_inactive:bool - hide inactive security groups, default is True
        
        verbose:bool - verbosity flag, default is False
        
        lang:str - language of output, can be 'en' or 'ru', default is en

    Outputs:
        dfs:dict - info about the market 

    '''

    check_connection()

    url=f'https://iss.moex.com/iss/index.json?lang={lang}&is_traded={is_traded}&hide_inactive={hide_inactive}'
    
    res = rq.get(url)
    res.raise_for_status()
   
    res = res.json()

    info = {}

    for k in res.keys():
        info[k] = pl.from_records(res[k]['data'], schema=res[k]['columns'], orient='row')

    return info

@OffsetFunctionFactory(base_url='https://iss.moex.com/iss/turnovers.csv?',
                       unrelated_args={'verbose', 'out', 'end', 'total', 'timeout'},
                       increment_arg='date',
                       increment=dt.timedelta(days=1))
def _pre_turnovers(is_tonight_session: bool = True,
                   start: dt.date | None = None,
                   end: dt.date = dt.datetime.now().date,
                   verbose: bool = False,
                   lang: str = 'en',
                   out: str = 'polars',
                   timeout: int = 5
                   ) -> dict[str, Any]:

    date = end - dt.timedelta(days=1) if start is None else start
    total = 1 if start is None else (end - start).days + 1 
    del start
    del end
   
    return locals()

#/iss/moex/turnovers
def turnovers(is_tonight_session: bool = True,
              start: dt.date | None = None,
              end: dt.date = dt.datetime.now(),
              verbose: bool = False,
              lang: str = 'en',
              out: str = 'polars',
              timeout: int = 5
              ) -> pl.DataFrame | pl.LazyFrame | pd.DataFrame:

    '''
    
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

    '''
    
    check_connection()

    start = end - dt.timedelta(days=1) if start is None else start

    kwargs = locals()
    df = _pre_turnovers(**kwargs)
    df = df.filter(~pl.col('NAME').is_in(['turnoversprevdate', 'turnovers', 'TOTALS'])).unique()
    return df.with_columns(pl.col('UPDATETIME').str.to_datetime(strict=False)).filter(pl.col('UPDATETIME') >= start)

#/iss/moex/turnovers/columns
def turnover_cols(lang:str='en',
                  timeout: int = 5
                  )->pl.DataFrame:
    '''

    Get turnover columns description

    Inputs:
        lang:str - language of output, can be 'en' or 'ru', default is en


    Outputs:
        df:pd.DataFrame - description of turnover columns in the selected language

    '''

    check_connection()
    query = rf"https://iss.moex.com/iss/engines/stock/turnovers/columns.csv?lang={lang}"
    res = rq.get(query, timeout=timeout)
    res.raise_for_status()
    return pl.read_csv(source=BytesIO(res.content),
                       encoding='cp1251',
                       sep=';', 
                       skip_rows=2, 
                       has_header=True
                       )

MOEX_ISS_ENDPOINTS = {
    "base": [
        "/iss/index",
        "/iss/securities",
        "/iss/securities/{security}",
        "/iss/turnovers",
        "/iss/turnovers/columns",
        "/iss/securitygroups",
        "/iss/sitenews",
        "/iss/events",
    ],
    
    "history": [
        "/iss/history/otc/providers/nsd/markets",
        "/iss/history/otc/providers/nsd/markets/{market}/daily",
        "/iss/history/otc/providers/nsd/markets/{market}/monthly",
        "/iss/history/engines/{engine}/markets/{market}/listing/columns",
        "/iss/history/engines/{engine}/markets/{market}/listing",
        "/iss/history/engines/{engine}/markets/{market}/sessions",
        "/iss/history/engines/{engine}/markets/{market}/sessions/{session}/securities",
        "/iss/history/engines/{engine}/markets/{market}/sessions/{session}/securities/{security}",
        "/iss/history/engines/{engine}/markets/{market}/dates",
        "/iss/history/engines/{engine}/markets/{market}/securities",
        "/iss/history/engines/{engine}/markets/{market}/yields",
        "/iss/history/engines/{engine}/markets/{market}/securities/{security}",
        "/iss/history/engines/{engine}/markets/{market}/securities/{security}/dates",
        "/iss/history/engines/{engine}/markets/{market}/boards/{board}/securities",
        "/iss/history/engines/{engine}/markets/{market}/boards/{board}/securities/{security}",
        "/iss/history/engines/{engine}/markets/{market}/boardgroups/{boardgroup}/securities",
        "/iss/history/engines/{engine}/markets/{market}/boardgroups/{boardgroup}/securities/{security}",
        "/iss/history/engines/stock/totals/boards",
        "/iss/history/engines/stock/totals/securities",
        "/iss/archives/engines/{engine}/markets/{market}/{datatype}/years",
    ],
    
    "engines": [
        "/iss/engines",
        "/iss/engines/{engine}/markets",
        "/iss/engines/{engine}/markets/{market}",
        "/iss/engines/{engine}/markets/{market}/securities",
        "/iss/engines/{engine}/markets/{market}/securities/{security}/trades",
        "/iss/engines/{engine}/markets/{market}/securities/{security}/orderbook",
        "/iss/engines/{engine}/markets/{market}/securities/{security}/candles",
        "/iss/engines/{engine}/markets/{market}/trades",
        "/iss/engines/{engine}/markets/{market}/boards",
        "/iss/engines/{engine}/markets/{market}/boards/{board}/securities/{security}/trades",
        "/iss/engines/{engine}/markets/{market}/boards/{board}/securities/{security}/orderbook",
        "/iss/engines/{engine}/markets/{market}/boardgroups",
        "/iss/engines/{engine}/markets/{market}/boardgroups/{boardgroup}/securities/{security}/trades",
        "/iss/engines/{engine}/markets/{market}/boardgroups/{boardgroup}/orderbook",
        "/iss/engines/{engine}/markets/{market}/{table}/columns",  # Cleaned from .*?/columns
        "/iss/statistics/engines/futures/promo",
        "/iss/statistics/engines/futures/markets/options/assets",
        "/iss/statistics/engines/futures/markets/options/assets/{asset}",
        "/iss/statistics/engines/futures/markets/options/assets/{asset}/volumes",
        "/iss/statistics/engines/futures/markets/options/assets/{asset}/optionboard",
        "/iss/statistics/engines/futures/markets/options/assets/{asset}/openpositions",
        "/iss/statistics/engines/futures/markets/options/assets/{asset}/turnovers",
        "/iss/statistics/engines/futures/markets/forts/series",
        "/iss/statistics/engines/futures/markets/options/series",
        "/iss/statistics/engines/futures/markets/options/series/{series_name}/securities",
        "/iss/statistics/engines/futures/markets/{market}/openpositions",
        "/iss/statistics/engines/futures/markets/{market}/openpositions/{asset}",
        "/iss/statistics/complex/securities",
        "/iss/statistics/engines/stock/markets/shares/correlations",
        "/iss/statistics/engines/currency/markets/selt/rates",
        "/iss/statistics/engines/stock/splits",
        "/iss/statistics/engines/state/markets/repo/mirp",
        "/iss/statistics/engines/stock/deviationcoeffs",
        "/iss/statistics/engines/stock/quotedsecurities",
        "/iss/statistics/engines/stock/currentprices",
        "/iss/statistics/engines/stock/markets/bonds/monthendaccints",
        "/iss/statistics/engines/stock/markets/index/analytics/columns",
        "/iss/statistics/engines/stock/markets/index/bulletins",
        "/iss/statistics/engines/stock/markets/index/rusfar",
        "/iss/statistics/engines/stock/markets/index/rusfar/attributes",
        "/iss/statistics/engines/{engine}/securitieslisting",
        "/iss/statistics/engines/stock/markets/bonds/aggregates",
        "/iss/statistics/engines/stock/markets/bonds/aggregates/columns",
        "/iss/statistics/engines/stock/markets/index/analytics",
        "/iss/statistics/engines/stock/capitalization",
        "/iss/rms/engines/{engine}/objects/irr",
        "/iss/rms/engines/{engine}/objects/settlementscalendar",
        "/iss/rms/engines/{engine}/objects/{object}",
        "/iss/statistics/engines/state/rates",
        "/iss/statistics/engines/state/rates/columns",
        "/iss/statistics/engines/{engine}/derivatives/{report_name}",
        "/iss/statistics/engines/{engine}/monthly/{report_name}",
        "/iss/statistics/engines/currency/markets/fixing/{security}",
        "/iss/statistics/engines/futures/markets/indicativerates/securities",
        "/iss/statistics/engines/currency/markets/fixing",
        "/iss/statistics/engines/{engine}/markets/{market}",
        "/iss/statistics/engines/{engine}/markets/{market}/securities",
        "/iss/statistics/engines/{engine}/markets/{market}/securities/{security}",
        "/iss/referencedata/engines/{engine}/markets/all/securitieslisting",
        "/iss/referencedata/engines/stock/markets/all/securities",
        "/iss/referencedata/engines/stock/markets/all/shorts",
        "/iss/referencedata/engines/futures/markets/{market}/risks",
        "/iss/referencedata/engines/futures/markets/{market}/params",
        "/iss/referencedata/engines/futures/markets/{market}/securities",
        "/iss/analyticalproducts/netflow2/securities",
        "/iss/analyticalproducts/futoi/securities",
    ],
    
    "cci": [
        "/iss/cci/info-nsd/companies",
        "/iss/cci/info-nsd/companies/{company}",
        "/iss/cci/reference/guides-treks",
        "/iss/cci/reference/periods",
        "/iss/cci/reference/nations",
        "/iss/cci/reference/sources",
        "/iss/cci/accounting/msfo-source/reports",
        "/iss/cci/accounting/msfo-source/periods/{period}/reports",
        "/iss/cci/accounting/msfo-source/companies/{company}/periods/{period}/reports",
        "/iss/cci/accounting/msfo-source/companies/{company}/reports",
        "/iss/cci/accounting/msfo-source/reports/{report_id}",
        "/iss/cci/accounting/msfo-source/periods/{period}/reports/{report_id}",
        "/iss/cci/accounting/msfo-source/companies/{company}/periods/{period}/reports/{report_id}",
        "/iss/cci/accounting/msfo-source/companies/{company}/reports/{report_id}",
        "/iss/cci/accounting/{accounting_type}/reports",
        "/iss/cci/accounting/{accounting_type}/periods/{period}/reports",
        "/iss/cci/accounting/{accounting_type}/companies/{company}/periods/{period}/reports",
        "/iss/cci/accounting/{accounting_type}/companies/{company}/reports",
        "/iss/cci/accounting/{accounting_type}/reports/{report_id}",
        "/iss/cci/accounting/{accounting_type}/periods/{period}/reports/{report_id}",
        "/iss/cci/accounting/{accounting_type}/companies/{company}/periods/{period}/reports/{report_id}",
        "/iss/cci/accounting/{accounting_type}/companies/{company}/reports/{report_id}",
        "/iss/cci/reference/rating-books",
        "/iss/cci/reference/rating-levels",
        "/iss/cci/reference/rating-books-rating-levels",
        "/iss/cci/rating/companies/{company_id}/securities",
        "/iss/cci/rating/companies/{company_id}/securities/{security_id}",
        "/iss/cci/rating/companies",
        "/iss/cci/rating/companies/{company_id}",
        "/iss/cci/rating/history/companies",
        "/iss/cci/rating/history/companies/{company_id}",
        "/iss/cci/rating/securities",
        "/iss/cci/rating/securities/{security_id}",
        "/iss/cci/rating/history/securities",
        "/iss/cci/rating/history/securities/{security_id}",
        "/iss/cci/info-nsd/securitybooks",
        "/iss/cci/info-nsd/securities",
        "/iss/cci/info-nsd/securitybooks/{securitybook}/securities",
        "/iss/cci/reporting/affiliates/reports",
        "/iss/cci/reporting/affiliates/reports/{report_id}",
        "/iss/cci/reporting/affiliates/companies/{company}/periods/{period}/reports",
        "/iss/cci/reporting/affiliates/companies/{company}/periods/{period}/reports/{report_id}",
        "/iss/cci/reporting/affiliates/periods/{period}/reports",
        "/iss/cci/reporting/affiliates/periods/{period}/reports/{report_id}",
        "/iss/cci/reporting/affiliates/companies/{company}/reports",
        "/iss/cci/reporting/affiliates/companies/{company}/reports/{report_id}",
        "/iss/cci/rating/agg/companies",
        "/iss/cci/rating/agg/companies/{company_id}",
        "/iss/cci/reference/industry-codes",
        "/iss/cci/info/companies/industry-codes",
        "/iss/cci/accounting/msfo-full/indicators",
        "/iss/cci/accounting/msfo-full/companies/{company}/indicators",
        "/iss/cci/accounting/msfo-full/indicators/{report_id}",
        "/iss/cci/reporting/corp-info/reports",
        "/iss/cci/reporting/corp-info/reports/{report_id}",
        "/iss/cci/reporting/corp-info/companies/{company}/periods/{period}/reports",
        "/iss/cci/reporting/corp-info/companies/{company}/periods/{period}/reports/{report_id}",
        "/iss/cci/reporting/corp-info/periods/{period}/reports",
        "/iss/cci/reporting/corp-info/periods/{period}/reports/{report_id}",
        "/iss/cci/reporting/corp-info/companies/{company}/reports",
        "/iss/cci/reporting/corp-info/companies/{company}/reports/{report_id}",
        "/iss/cci/rating/agg/securities",
        "/iss/cci/rating/agg/securities/{security_id}",
        "/iss/cci/accounting/msfo-full/industry-indicators/reports",
        "/iss/cci/accounting/msfo-full/industry-indicators/reports/{indicator_id}",
        "/iss/cci/info/companies",
        "/iss/cci/info/companies/{company}",
        "/iss/cci/calendars/ir-calendar",
        "/iss/cci/corp-actions/meetings",
        "/iss/cci/corp-actions/meetings/{corp_action_id}",
        "/iss/cci/corp-actions/coupons",
        "/iss/cci/corp-actions/coupons/{corp_action_id}",
        "/iss/cci/corp-actions/dividends",
        "/iss/cci/corp-actions/dividends/{corp_action_id}",
        "/iss/cci/corp-actions",
        "/iss/cci/corp-actions/{corp_action_id}",
        "/iss/cci/consensus/shares-price",
        "/iss/cci/consensus/shares-price/{security}",
        "/iss/cci/reference/relations",
        "/iss/cci/reference/trek-relations",
        "/iss/cci/reporting/group-related-data",
        "/iss/cci/reporting/group-related",
        "/iss/cci/reporting/group-related/{group_related_id}",
    ]
}

MOEX_ISS_WRAPPED_ENDPOINTS = {
    'base' : {
        "/iss/index" : market_info,
        "/iss/securities" : list_securities, 
        "/iss/securities/[security]" : security_specs, 
        "/iss/securities/[security]/indices" : indxs4secs,
        "/iss/securities/[security]/aggregates" : agg_info,
        "/iss/turnovers" : turnovers,
        "/iss/turnovers/columns" : turnover_cols,
        }

}
