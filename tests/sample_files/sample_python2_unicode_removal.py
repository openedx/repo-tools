"""
Test file for the script remove_python2_unicode_compatible.py
"""
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class Test:
    """
    Random Test class
    """
    def __init__(self):
        pass


@python_2_unicode_compatible
@login_required
class Test2:
    """
    Random Test class
    """
    def __init__(self):
        pass


@login_required
class Test3:
    """
    Random Test class
    """
    def __init__(self):
        pass
