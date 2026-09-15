
## Overview

This repository contains my Data Engineering solution for the LPDG Innovation Hub Selection Challenge 2026.

I selected **Data Engineering** as my focus area.

The main objective of the solution is to build a reproducible data pipeline for gateway telemetry and related operational data. The pipeline cleans the data, creates gateway-level features, prepares the available engineer-review data, performs feature analysis, and generates weekly gateway rankings from telemetry behaviour.

The challenge dataset is **not included in this repository** because the challenge instructions explicitly state that the dataset must not be published.

---

## Pipeline

The implementation is divided into separate stages:

```text
Input Data
    |
    v
Data Cleaning
    |
    v
Feature Engineering
    |
    v
Target Creation
    |
    v
Feature Analysis
    |
    v
Weekly Scoring
    |
    v
Predictions / Gateway Ranking
    |
    v
Validation