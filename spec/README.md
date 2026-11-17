# Specification

The specification and the test matrix are built from one source file.

| File | Content |
|---|---|
| `requirements.yaml` | Epics, features, functional and non-functional requirements, glossary, sources |
| `build.py` | Checks the IDs and the writing style, then writes `docs/spec/M4-Parking-Spec-v<version>.html` |
| `tools/ste-lint/` | ASD-STE100 style checker from [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill) (MIT licence) |

## Make a new version

1. Change `requirements.yaml`.
2. Raise `version` in `requirements.yaml`.
3. Run `python3 spec/build.py` from the repository root.
4. Commit the YAML file and the new HTML file.

The build stops if an ID is wrong or used twice, or if a requirement fails the style check.
The build never overwrites a version. Quoted on-screen texts are not style-checked.

Published versions: https://marwa112.github.io/m4-parking/spec/
