"""Ecosystem-specific license extractors."""

from __future__ import annotations

from ecosystems.js import extract_licenses_pnpm, extract_licenses_node_modules, lookup_npm_license
from ecosystems.rust import extract_licenses_cargo, lookup_crates_io_license
from ecosystems.python import extract_licenses_python, lookup_pypi_license
from ecosystems.swift import find_package_resolved, extract_licenses_swift
from ecosystems.gradle import extract_licenses_gradle, lookup_maven_license
from ecosystems.dart import extract_licenses_dart, lookup_pub_dev_repo
from ecosystems.go import extract_licenses_go
from ecosystems.csharp import extract_licenses_csharp, lookup_nuget_license
from ecosystems.solidity import extract_licenses_solidity
