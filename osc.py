import json
import random
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import operator
from functools import reduce


def build_dictionary_filter_from_kwargs(**filter_kwargs):
    def _filter_fun(field, value):
        return lambda d: d[field].lower() == value.lower()
    return [_filter_fun(k, v) for k, v in filter_kwargs.items() if v]


def filter_packages(packages, **filter_kwargs):
    new_packages = []
    filters = build_dictionary_filter_from_kwargs(**filter_kwargs)
    for package in packages:
        if len(filters) == 0 or reduce(operator.and_, [filter_(package) for filter_ in filters]):
            new_packages.append(package)
    return new_packages


class API:
    packages = None
    themes_packages = None
    package_of_the_day = None
    newest_packages = None

    def __init__(self):
        scheduler = BackgroundScheduler()
        # Schedule packages list for refresh once per 30 minutes
        scheduler.add_job(func=self.load_packages, trigger="interval", minutes=30)
        # Schedule newest app for refresh once per 30 minutes
        scheduler.add_job(func=self.newest_apps, trigger="interval", minutes=30)
        # Schedule app of the day for refresh once per day at 2:00
        scheduler.add_job(func=self.set_package_of_the_day, trigger='cron', hour='2', minute='00')
        scheduler.start()

    def load_packages(self):
        self.packages = json.loads(requests.get(f"https://api.oscwii.org/v2/primary/packages").text)
        self.themes_packages = json.loads(requests.get(f"https://api.oscwii.org/v2/themes/packages").text)

    def get_packages(self, developer=None, category=None):
        filtered = filter_packages(self.packages, coder=developer, category=category)
        return filtered

    def get_themes(self, developer=None, category=None):
        filtered = filter_packages(self.themes_packages, coder=developer, category=category)
        return filtered

    def package_by_name(self, name):
        for package in self.packages:
            if package["internal_name"].lower() == name.lower():
                try:
                    package["release_date"] = datetime.fromtimestamp(int(package["release_date"])).strftime(
                        '%B %e, %Y')
                except ValueError:
                    pass
                return package

    def theme_by_name(self, name):
        for package in self.themes_packages:
            if package["internal_name"].lower() == name.lower():
                try:
                    package["release_date"] = datetime.fromtimestamp(int(package["release_date"])).strftime(
                        '%B %e, %Y')
                except ValueError:
                    pass
                return package

    def newest_apps(self):
        newest_apps = {"newest": None,
                       "demos": None,
                       "utilities": None,
                       "emulators": None,
                       "games": None,
                       "media": None}
        for key, value in newest_apps.items():
            date = 0
            for package in self.packages:
                if (package["category"] == key) or (key == "newest"):
                    if date < package["release_date"]:
                        date = package["release_date"]
                        newest_apps[key] = package

        self.newest_packages = newest_apps

    def set_package_of_the_day(self):
        # some quality assurance, some of the apps have covid
        while True:
            package = random.choice(self.packages)
            # they do not have covid, just did not specify a description
            if package["short_description"] == "No description provided.":
                continue
            # they do not have covid, just simply a demo and we can't have that
            if package["category"] == "demos":
                continue
            # they do not have covid, but don't support wii remotes
            if "w" not in package["controllers"]:
                continue
            # they do not have covid, but the developer is Danbo
            if package["coder"] == "Danbo":
                continue
            break
        self.package_of_the_day = package
