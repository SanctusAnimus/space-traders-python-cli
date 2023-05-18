from enum import Enum


class HandleResult(str, Enum):
    # worked as requested
    SUCCESS = "success"
    # something went wrong
    FAIL = "fail"
    # request has been discarded (repetitive/redundant or incorrect state)
    SKIP = "skip"
    # request fulfilled, and should not wait (doesn't do requests)
    INSTANCE = "instant"
