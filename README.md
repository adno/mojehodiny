# mojehodiny

This app currently targets only Czech audience (Czech school year, holidays,
etc.). There is a potential for internationalization/localization, but I don't
have time or motivation for it.

The app has two parts:

- `mojehodiny.py`: the core module and also a tool that can run on Google Colab
  (or in CLI) in a little limited way

- `mojehodiny_app.py` and its `assets`: a Dash web app with nice web UI

For the web app you need the `dash` package (installable using pip). Tested
with Dash 1.15.0 and Python 3.6 and 3.7.

You can run the web app locally for debugging like this:

`$ python mojehodiny_app.py`

You can also host it on pythonanywhere.com or a similar service.

If you want to use the code have a look at the `LICENCE`.
