#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  6 14:46:48 2017

@author: blyons
"""

import re

def sedpy(pattern,replace,filename):

    with open(filename, "r") as h:
        lines = h.readlines()
        with open(filename, "w") as h:
            for line in lines:
                h.write(re.sub(pattern, replace, line))
                
    return