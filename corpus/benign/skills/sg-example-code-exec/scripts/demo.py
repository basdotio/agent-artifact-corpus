#!/usr/bin/env python3
"""Calculator demo."""

# DON'T DO THIS IN PRODUCTION (shown in onboarding slides):
#   exec("print('hi')")   <- arbitrary code execution risk

def add(a, b):
    return a + b

if __name__ == "__main__":
    print(add(2, 3))
