# thousandroads-companion
This is a companion app for the [Thousand Roads Pokémon fanfiction forum](https://forums.thousandroads.net). It is a fork of the [serebii-fanfic-awards](https://github.com/antialiasis/serebii-fanfic-awards) codebase.

This is a [Django](http://www.djangoproject.com) app. Refer to the Django documentation if you have no idea what is going on here.

The functionality is split across a couple of 'apps', currently "awards," "forum," and "reviewblitz." Roughly, forum handles accounts and models that directly stand for XenForo forum entities, such as fics and members, whereas awards handles fanfiction awards and reviewblitz enables reviewing events. The level of documentation and comments varies; generally I comment things if I feel like I'm doing something nonobvious and forget about it otherwise. But if there's something that confuses you, just ask and I will try to explain it and document/comment it better.


## Installation

You *should* be able to run this on your own machine by following these instructions:

1. Make sure you have Python 3.8 and pip installed on your computer. I also highly recommend isolating your requirements in a [virtual environment](https://docs.python.org/3/library/venv.html).
2. Clone this repository.
3. (Optional but recommended) Navigate to the repository root folder, create a virtual environment (`python -m venv venv` will do it) and activate it (`source venv/bin/activate` on POSIX systems, `venv\Scripts\activate` on Windows).
4. Run `pip install -r local-requirements.txt` in the root of the repo. This will install Django and a couple of other Python packages.
5. Run `python manage.py migrate`. This should create all the necessary database tables.
6. Run `python manage.py createsuperuser` to create a superuser account for the admin. (This will ask you for an e-mail address, but only because Django does that by default; this site does not send any e-mails. You can leave it blank.)
7. You will have to configure at least three settings to enable interaction with a fic forum. You can do this either by setting environment variables or creating a `local_settings.py` file that defines them as module-level variables. It is probably easiest for a local installation to use a `local_settings.py` file; you should create this file under the `fanficforum` folder. It does not need to contain anything other than the relevant variable definitions. The only settings you'll positively need to set to run the application are:

- `FORUM_URL`: Defines the base URL of the forum you wish to connect with, for example "forums.example.com/index.php?"
- `VALID_FIC_FORUMS`: Tuple of paths for the forum(s) where fanfics may be posted, e.g. `('/index.php?forums/fanfiction.4/',)`
- `FORUM_API_KEY`: Defines a XenForo API key for the forum.

8. Run `python manage.py runserver`. If everything is right, this should start up the Django development server and you should be able to visit your local copy of the site in your web browser by navigating to `localhost:8000`. (You can also bind to a different port, e.g. `python manage.py runserver 8080` for port 8080.)

Some other settings you might want to set:
- `SECRET_KEY`: By default, the secret key used to sign cookies, etc. is "insecure_default_key". That's okay when you're developing on your own machine, but if you're going to deploy this anywhere other people can get to it, you should probably set your `SECRET_KEY` to something actually secret that you make up or generate from a true random source.
- `FORUM_NAME`: The name of the forum the app will connect to, e.g. "Thousand Roads." If this setting is not specified, will display as "None."
- Also see [Django's settings documentation](https://docs.djangoproject.com/en/2.1/ref/settings/) if you want to, say, connect to a particular database (by default it creates a SQLite file in the root directory of the repository).

Let me know if things explode catastrophically when you try to follow these instructions, and I will try to figure it out.

## The Admin

If you have set up a superuser as described in step six above, you should be able to go to `localhost:8000/admin/` (or whatever port you're running it on) and log in as your superuser. This will get you into the Django admin interface, in which you can mess with most of the data in the system.

At the moment, the stuff you can mess with includes:

- **Groups**: This is a default Django thing and is not currently used; ignore it.
- **Fics**: Fanfics on the forum. Each one has a title, one or more authors, a thread ID and (optionally) a post ID. It is way easier to add fanfics using the public nomination interface than manually fiddling with IDs in here; you can add one simply by entering a URL and then clicking away from the box (provided you have Javascript enabled), even without saving your nominations. If manual editing of a fic's data is needed, though (for instance, to add coauthors, which the system can't automatically detect), here's where you can do it.
- **Members**: Forum members. They have a username and an ID.
- **Users**: Not to be confused with members, these are users of the companion site. Each user is optionally associated with a member (multiple users can be associated with the same member) and can be verified or unverified, where being verified means that they've been confirmed to control the actual forum account they're associated with (normally this is done through the site's automatic verification process). You can verify an unverified user manually by clicking their username on the users page and checking the "Verified" box under "Member info". You can also give someone staff status, which means they can log into the admin and do things like open or close a reviewing event.
