# Harness: run main.py with every data source returning nothing (simulates no API key + no network).
import os, runpy, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, ROOT)
os.environ.pop("CRYPTOCOMPARE_API_KEY", None)
import pandas as pd
import functions
functions._from_yahoo = lambda symbol, limit: pd.DataFrame()
functions.get_historical_data.clear()
runpy.run_path(os.path.join(ROOT, "main.py"), run_name="__main__")
