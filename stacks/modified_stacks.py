from .chromium import Chromium
from .mvfst import Mvfst

class ChromiumN1(Chromium):
    """
    Modified chromium stack where the number of emulated connections
    is changed from 2 (default) to 1
    """
    NAME = "chromium-n1"

class ChromiumAF2(Chromium):
    """
    Modified chromium stack where the ACK frequency is changed from
    10 (default) to 2
    """
    NAME = "chromium-af2"

class MvfstPR100(Mvfst):
    """
    Modified mvfst stack where the scaling of the pacing rate is
    changed back to 100% (i.e. removed)
    """
    NAME = "mvfst-pr100"

class MvfstAF2(Mvfst):
    """
    Modified mvfst stack where the ACK frequency is changed from
    10 (default) to 2
    """
    NAME = "mvfst-af2"
