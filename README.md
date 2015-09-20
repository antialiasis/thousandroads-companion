# serebii-fanfic-awards
The website for the Serebii.net forums fanfiction awards. This project is maintained by Dragonfree (antialiasis), but pull requests are welcome (so long as they're good pull requests).

## Installation

You *should* be able to run this on your own machine by following these instructions:

1. Make sure you have Python 2.7 and pip installed on your computer (and preferably virtualenv).
2. Clone the repository.
3. (Optional but recommended) Create a virtualenv for it and activate it.
4. Run `pip install -r requirements.txt` in the root of the repo. This will install Django and some other Python packages.
5. Run `python manage.py migrate`. This should create all the necessary database tables.
6. Run `python manage.py createsuperuser` to create a superuser account for the admin. (This will ask you for an e-mail address, but only because Django does that by default; the awards site does not send any e-mails.)
7. You will have to configure a few settings. You can do this either by setting environment variables or creating a `local_settings.py` file that sets them as variables. It is probably easiest for a local installation to use a `local_settings.py` file; this should be located under the `sppfawards` folder. The settings you almost definitely need are:
  - `PHASE`: Indicates the current phase of the awards. This can be set as `None` (when the awards have not yet started), `'nomination'` (in the nomination phase), `'voting'` (in the voting phase), or `'finished'` (when the awards are over). Changing this is how you can tinker with functionality from different phases.
  - `SEREBII_USER_ID` and `SEREBII_USER_PWHASH`: Forum credentials that the site will use to fetch threads/profiles. You should be able to get the appropriate values by inspecting your cookies for serebiiforums.com; these will be called `bb_userid` and `bb_password`. Without setting these, you're going to get errors when the site tries to fetch profiles, because guests can't view profiles.
8. Run `python manage.py runserver`. If everything is right, this should start up the Django development server and you should be able to visit your local copy of the awards site in your web browser by navigating to `localhost:8000`. (You can also bind to a different port, e.g. `python manage.py runserver 8080` for port 8080.)

Some other settings you might want to set:
- `YEAR`: Defines what the site thinks is the current awards year. This defaults to 2015 (or, more specifically, to the `MAX_YEAR` setting).
- `DISCUSSION_THREAD`, `NOMINATION_THREAD`, `VOTING_THREAD` and `RESULTS_THREAD`: Links to the relevant forum threads, to be used whenever the site needs to link to them. These settings are blank by default, which works just fine for testing, but it does mean these links will not work unless you set these settings.
- `SECRET_KEY`: By default, the secret key used to sign cookies, etc. is "insecure_default_key". That's okay when you're developing on your own machine, but if you're going to deploy this anywhere other people can get to it, you should probably set your `SECRET_KEY` to something actually secret that you make up.
- Also see [Django's settings documentation](https://docs.djangoproject.com/en/1.8/ref/settings/) if you want to, say, connect to a particular database (by default it creates a SQLite file in the root directory of the repository).

Let me know if things explode catastrophically when you try to follow these instructions, and I will try to figure it out.


## Administration

If you have set up a superuser as described in step six above, you should be able to go to `localhost:8000/admin` (or whatever port you're running it on) and log in as your superuser. There, you can mess with all the data.

In particular, you're going to need some actual awards. The repository includes a `data-dump.json` file that contains data about the awards and nominations from the 2013 awards, which I used for testing when developing the site; you should be able to load this data into the database with `python manage.py loaddata data-dump.json`. This is probably easier than creating categories and awards yourself, but of course you can do that if you want; the admin interface should be reasonably self-explanatory.

In order to work with a year that is not 2013, you're going to have to tell the site what awards will be awarded that year. From the admin main page, click "Year awards" under "Awards" and then use the little "Mass-edit awards for year" form near the top right corner of the page to pick a year and press "Go". This will redirect you to a page where you can simply check or uncheck which awards should be included for that year and then press Save at the bottom. Once this is done, you should be able to submit nominations through the regular site interface (provided you've set the `PHASE` setting to `'nomination'`).
