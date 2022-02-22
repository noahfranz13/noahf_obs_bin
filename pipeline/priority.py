#!/usr/bin/env python
"""
Prioritizing which sessions should be processed.
priority.txt contains a simple list of the high-priority sessions that acts as a queue.
It's okay to manually edit that list.
"""

import os
import random

DIR = os.path.dirname(os.path.realpath(__file__))
PRIORITY_FILENAME = os.path.join(DIR, "priority.txt")

def get_all_sessions():
    return [line.strip() for line in open(PRIORITY_FILENAME) if "GBT" in line]
    
def choose_session(condition=None):
    """
    Returns a high-priority session.
    If condition is provided, condition(session) must be true.
    """
    sessions = get_all_sessions()
    for session in sessions:
        if condition is None or condition(session):
            return session
    raise ValueError("There are no matching high-priority sessions left.")

def remove_session(session):
    """
    Removes a session from the high-priority list.
    """
    sessions = get_all_sessions()
    assert session in sessions
    new_sessions = [s for s in sessions if s != session]
    with open(PRIORITY_FILENAME, "w") as f:
        for s in new_sessions:
            f.write(s + "\n")
