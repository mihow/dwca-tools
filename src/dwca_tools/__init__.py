"""
dwca-tools: Tools for working with Darwin Core Archive and iNaturalist open data.
"""

__version__ = "0.1.0"
__author__ = "Mihow"

from dwca_tools.config import Settings
from dwca_tools.models import Example

__all__ = ["Example", "Settings", "__version__"]
