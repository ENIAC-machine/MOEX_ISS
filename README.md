# MOEX API Wrapper

![tests](https://github.com/ENIAC-machine/MOEX_ISS/actions/workflows/tests.yml/badge.svg)

## Description

This library is the wrapper for the MOEX free ISS API. There are many like this, but this one is mine. Current implementation features only the most basic functions, but it will expand over time.

## Installation

```bash
pip install git+https://github.com/ENIAC-machine/MOEX_ISS
```

## Quick start

Below you can find some example python code to load a history of the 'YNDX' stock:

```python
from iss import download

df = download(sec='YNDX', st='2020-01-01')

print(df.head())
```

