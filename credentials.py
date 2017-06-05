import os
import imp


crr_dir = os.path.dirname(os.path.realpath(__file__))
credentials_dir = os.path.abspath(os.path.join(crr_dir, '..', 'credentials.py'))

try:
    credentials = imp.load_source('credentials', credentials_dir)
    from credentials import *  # NOQA
except IOError:
    print "No credentials module loaded."
