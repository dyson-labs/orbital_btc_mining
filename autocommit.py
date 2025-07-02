# -*- coding: utf-8 -*-
"""
Created on Wed Jul  2 14:49:49 2025

@author: elder
"""
import os
import datetime

# Create a timestamped commit message
timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
commit_msg = f"Auto-commit: {timestamp}"

# Run Git add and commit
os.system("git add .")
os.system(f'git commit -m "{commit_msg}"')
