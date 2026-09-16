import os, subprocess
env = os.environ.copy()
env["BUILD_MODE"] = "release"
subprocess.run(["make", "build"], env=env)
