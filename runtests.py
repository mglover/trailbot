#!/usr/bin/python3
import sys, os
import unittest

tbroot = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(tbroot)


if __name__ == '__main__':
    tests = unittest.TestLoader().discover(tbroot)
    runner = unittest.TextTestRunner(sys.stdout, verbosity=1)
    runner.run(tests)