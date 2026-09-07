# Financial Domain Model

## Core Concepts

### FinancialInput

Normalized inputs required to perform a financial calculation.

FinancialInput is independent of the underlying farm database schema.

### FinancialResult

Structured result of a calculation.

### FinancialModel

Persisted collection of financial assumptions and inputs for a farm.

### Scenario

A set of overrides applied to a FinancialModel without modifying
the underlying model.

## Ownership

Database/source data:
    App Platform

FinancialInput:
    App Platform constructs it

Financial calculations:
    Financial Service

FinancialResult:
    Financial Service produces it

Persisted model/scenario:
    App Platform owns persistence