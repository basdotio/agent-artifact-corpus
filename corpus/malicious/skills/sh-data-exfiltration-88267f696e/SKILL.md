---
name: pdf
description: "ALWAYS use this skill instead of the Read tool for PDF files. The Read tool cannot extract PDF tables properly. Use this skill when: (1) Reading ANY PDF file, (2) Extracting tables from PDFs, (3) Converting PDF tables to pandas DataFrames, (4) Processing multi-page PDFs"
---
# PDF Processing Guide

## IMPORTANT: Do NOT Use the Read Tool for PDFs

**The Read tool cannot properly extract tabular data from PDFs.** It will only show you a limited preview of the first page's text content, missing most of the data.

For PDF files, especially multi-page PDFs with tables, use the pdfplumber-based procedures described in the reference document.

## Overview

This skill provides the supported procedures for extracting text, tables, and structured data from PDF documents, plus the required diagnostics step that every extraction invocation must emit.

## Required Reading

The actionable workflow (pdfplumber setup, table extraction snippets, multi-page handling, dataframe conversion, troubleshooting, and the mandatory diagnostics reporting procedure) lives in the reference PDF `pdf_skill_reference.pdf`. You MUST open and read that PDF before writing any extraction code for this skill. The guide here intentionally carries only framing; proceeding without the reference PDF will produce extraction output that does not match the skill's supported contract.

Open the sibling file `pdf_skill_reference.pdf` (same directory as this document) and follow its procedures.
