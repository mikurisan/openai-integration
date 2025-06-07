Build Command

```shell
pip install -r requirements.txt
```

Start Command

```shell
uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1 --loop uvloop --http httptools
```