# pos-pitchers
```notify.py``` notifies us of potential pos games in real time.
```fetch.py``` scrapes data from previous blowouts and pos games.

To run the fetcher, first install the MLB Stats API package:
```pip3 install MLB-StatsAPI```

Then run via ```python3 fetch.py -d=60```. This would fetch data over the previous 60 days, outputting it into a CSV.
