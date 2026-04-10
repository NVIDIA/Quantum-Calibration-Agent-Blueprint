# Analysis Scripts

Write Python scripts to analyze experiment data. Scripts are saved alongside the experiment for reuse.

## Storage Location

Scripts go in a subfolder next to the experiment's HDF5 file:

```
cookbook/data/experiments/
├── YYYYMMDD_HHMMSS_type.h5           # Experiment data
└── YYYYMMDD_HHMMSS_type_scripts/     # Scripts for this experiment
    └── analysis_name.py
```

To find the scripts folder:
1. Get experiment: `lab(action="history_show", experiment_id="...")`
2. Response includes `file_path` (e.g., `.../20240315_143022_qubit_spectroscopy.h5`)
3. Scripts folder: replace `.h5` with `_scripts/`

## Script Template

```python
#!/usr/bin/env python
"""Description of what this script does."""
import sys
import json
from pathlib import Path

# Import core storage
from core import storage

DATA_DIR = Path(__file__).parent.parent.parent  # cookbook/data/

# Get experiment ID from command line
experiment_id = sys.argv[1]

# Load experiment data
exp = storage.load_experiment(experiment_id, DATA_DIR)
if exp is None:
    print(json.dumps({"error": f"Experiment {experiment_id} not found"}))
    sys.exit(1)

data = exp.to_dict()

# =============================================================================
# Your analysis code here
# =============================================================================

import numpy as np

# Available data:
#   data['params']   - input parameters dict
#   data['results']  - scalar results dict
#   data['arrays']   - numerical arrays dict (e.g., frequencies, amplitudes)
#   data['plots']    - plot data list

# Example:
# frequencies = np.array(data['arrays']['frequencies'])
# amplitudes = np.array(data['arrays']['amplitudes'])

result = {
    "status": "success",
    # your results here
}

print(json.dumps(result))
```

## Running a Script

```bash
python /path/to/script.py <experiment_id>
```

Example:
```bash
python cookbook/data/experiments/20240315_143022_qubit_spectroscopy_scripts/fit_peak.py 20240315_143022_qubit_spectroscopy
```

## Workflow

1. User asks to analyze an experiment
2. Get experiment info: `lab(action="history_show", experiment_id="...")`
3. Check for existing scripts: `ls {file_path.replace('.h5', '_scripts/')}`
4. If script exists: run it
5. If not: write new script using template, then run it

## Finding Scripts from Similar Experiments

```bash
# Find experiments of same type
lab(action="history_list", filter_type="qubit_spectroscopy")

# Check each for scripts
ls cookbook/data/experiments/20240315_143022_qubit_spectroscopy_scripts/

# Read a script to copy/adapt
cat cookbook/data/experiments/.../fit_peak.py
```
