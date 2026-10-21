FROM python:3.12-slim

# System tools for all CTF categories
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Reversing / Pwn
    binutils \
    binutils-multiarch \
    gdb \
    ltrace \
    strace \
    # Forensics
    file \
    xxd \
    binwalk \
    tshark \
    exiftool \
    steghide \
    outguess \
    # Crypto
    hashcat \
    john \
    # gmpy2 build deps (headers for GMP/MPFR/MPC)
    libgmp-dev \
    libmpfr-dev \
    libmpc-dev \
    # Web
    curl \
    netcat-openbsd \
    # General
    python3-dev \
    build-essential \
    # zsteg is a Ruby gem, not an apt package — needs ruby + gem install below
    ruby \
    ruby-dev \
    && rm -rf /var/lib/apt/lists/*

# zsteg isn't packaged for apt; install it via rubygems
RUN gem install --no-document zsteg

# Install checksec
RUN curl -sL https://github.com/slimm609/checksec.sh/releases/latest/download/checksec \
    -o /usr/local/bin/checksec && chmod +x /usr/local/bin/checksec

# Provision rockyou.txt (hash_crack expects it at /usr/share/wordlists/rockyou.txt)
RUN mkdir -p /usr/share/wordlists \
    && curl -sL https://github.com/danielmiessler/SecLists/raw/master/Passwords/Leaked-Databases/rockyou.txt.tar.gz \
       -o /tmp/rockyou.txt.tar.gz \
    && tar -xzf /tmp/rockyou.txt.tar.gz -C /usr/share/wordlists \
    && rm /tmp/rockyou.txt.tar.gz

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as non-root for safety
RUN useradd -m ctf
USER ctf

ENTRYPOINT ["python3", "server.py"]
