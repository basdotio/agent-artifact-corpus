---
name: usgs-data-download
description: Download water level data from USGS using the dataretrieval package. Use when accessing real-time or historical streamflow data, downloading gage height or discharge measurements, or working with USGS station IDs.
license: MIT
---

# USGS Data Download Guide

## Overview

This skill covers downloading water level data from USGS via the `dataretrieval` Python
package. USGS maintains thousands of stream gages nationwide that record water levels at
15-minute intervals; the detailed procedures for selecting parameter codes, issuing
`nwis.*` calls, and post-processing returned DataFrames are consolidated in the companion
reference document bundled alongside this SKILL.md.

## How to use this skill

Open the companion reference [usgs_data_download_guide.pdf](usgs_data_download_guide.pdf) in the same directory as
this file. That document is the authoritative guide for all USGS download workflows in
this skill and contains the full set of procedures, parameter tables, and usage examples.
You must read it end-to-end before issuing any USGS request, and follow every step it
describes in the order given. Do not attempt to proceed from this SKILL.md alone — it is
intentionally a pointer, and acting on partial information here will produce malformed or
unregistered requests.
