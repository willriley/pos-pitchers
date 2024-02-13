# pos-pitchers
Background: My friends and I figured out that in blowout baseball games, teams would often put in position players to pitch (e.g. an outfielder or 3rd baseman) so that they wouldn't tire out their real pitchers' arms. Position players were pretty horrible pitchers, and the opposing team would have Babe Ruth-like numbers against them. However, the sportsbooks weren't taking this into account, and so when there was a blowout game, we'd bet that it would become an even bigger blowout, since a position player was likely to come in and pitch. We did pretty well for ourselves until the sportsbooks limited us and eventually stopped offering these lines late in games.

```notify.py``` notifies us of potential pos games in real time.
```fetch.py``` scrapes data from previous blowouts and pos games.

To run the fetcher, first install the MLB Stats API package:
```pip3 install MLB-StatsAPI```

Then run via ```python3 fetch.py -d=60```. This would fetch data over the previous 60 days, outputting it into a CSV.
