"""Access to the orgs.yaml data."""

import yamldata


class Orgs(yamldata.YamlData):
    """
    Information about organizations.
    """

    @classmethod
    def orgs(cls):
        return cls.the_data("orgs.yaml")

    def get(self, org):
        org_info = self.data.get(org)
        if org_info is None:
            org_info = {
                "internal": False,
                }

        return org_info
