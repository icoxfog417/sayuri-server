"""Python Rekognition API Wrapper."""

__version__ = '0.0.1'
__all__ = ['Client']

USER_AGENT = 'Rekognition Python API Wrapper %s' % __version__

from rekognition.attribute_dict import AttributeDict
from rekognition.client import Client
