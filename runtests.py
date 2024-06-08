#!/usr/bin/python3
import sys, os, warnings
import unittest
from urllib3.connectionpool import InsecureRequestWarning


tbroot = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(tbroot)

testbase = 'trailbot.tests.test_'

# requests run through the local proxy with an unknown cert
warnings.simplefilter(
    "ignore", 
    category=InsecureRequestWarning,
    lineno=1099
)

if __name__ == '__main__':
    specs = sys.argv[1:]
    loader = unittest.TestLoader()

    if not specs:
        tests = loader.discover(tbroot)
    else:
        tests = loader.loadTestsFromNames([testbase+s for s in specs])

    runner = unittest.TextTestRunner(sys.stdout, verbosity=1)
    runner.run(tests)