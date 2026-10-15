# pitch-audit in a box: Chromium, Node (local Lighthouse), poppler (extra PDF check), Python deps.
#   docker build -t pitch-audit .
#   docker run --rm -v "$PWD/work:/work" pitch-audit python3 /skill/scripts/build.py /work/clients/<slug>
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils nodejs npm fonts-inter \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /skill/requirements.txt
RUN pip install --no-cache-dir -r /skill/requirements.txt && npm i -g lighthouse@13
COPY . /skill
ENV PITCH_BROWSER=chromium PITCH_PROFILE=/work/pitch-profile
WORKDIR /work
CMD ["python3", "/skill/scripts/doctor.py"]
