#!/usr/bin/env python3
"""Horizontal sweep coverage helper for the pcap-analysis skill.

Distributed and "low-and-slow" port scans are designed to evade per-source
heuristics by rotating the probe traffic across many source IPs, so that no
single source crosses entropy / unique-port / SYN-only thresholds. The
defensive response is to complement per-source checks with a capture-wide
coverage view: if the aggregate set of destination ports touched across the
whole capture is wide enough, a sweep is occurring regardless of which
source initiated any individual probe.

This module exposes a single predicate, ``has_horizontal_sweep``, which is
called from :func:`pcap_utils.detect_port_scan` after the per-source loop."""

from scapy.all import TCP

DEFAULT_COVERAGE_THRESHOLD = 100


def collect_destination_ports(tcp_packets):
    """Return the set of distinct TCP destination ports observed in the capture."""
    seen = set()
    for pkt in tcp_packets:
        if TCP in pkt:
            seen.add(int(pkt[TCP].dport))
    return seen


def has_horizontal_sweep(tcp_packets, coverage_threshold=DEFAULT_COVERAGE_THRESHOLD):
    """Return True when the capture covers enough distinct destination ports
    to be considered a horizontal sweep."""
    return len(collect_destination_ports(tcp_packets)) > coverage_threshold
