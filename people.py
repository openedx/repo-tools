"""Access to the people.yaml database."""

import yamldata


class People(yamldata.YamlData):
    """
    A database of people.
    """

    @classmethod
    def people(cls):
        return cls.the_data("people.yaml")

    def get(self, who, when=None):
        """
        Get the details for a person, optionally at a point in the past.
        """
        user_info = self.data.get(who)
        if user_info is None:
            user_info = {"institution": "unsigned", "agreement": "none"}

        if when is not None and "before" in user_info:
            # There's history, let's get the institution as of the pull
            # request's created date.
            when = when.date()  # Get just the date from a datetime.
            history = sorted(user_info["before"].items(), reverse=True)
            for then, info in history:
                if then < when:
                    break
                user_info.update(info)
        return user_info
