# CFD Wing Automation

Automates OpenFOAM CFD runs for an aircraft across multiple angles of attack, including meshing, solving, and ParaView post-processing.

## Requirements

- OpenFOAM
- PyFoam
- ParaView (`pvbatch`)
- MPI (`mpirun`)

## Usage

1. Place your wing geometry as `Wing.stl` in the project root.
2. Set your parameters in `solve.py`:

    ```python
    alphas = [0.0, 5.0, 10.0]   # Angles of attack (degrees)
    u      = 50.0               # Freestream velocity (m/s)
    c      = 1.0                # Reference chord (m)
    S      = 1.0                # Reference area (m²)
    ```

3. Run:

```bash
python solve.py
```

## What It Does

For each angle of attack, the workflow:

1. Clones `case_template` into a new run directory
2. Rotates the STL and generates the mesh with `snappyHexMesh`
3. Solves with `foamRun` in parallel
4. Renders images via ParaView into `<run_dir>/images/`
5. Cleans up heavy mesh/processor files

## Output Images

| File | Description |
| --- | --- |
| `geometry-<view>.png` | Wing surface (4 angles) |
| `cp-contour-<view>.png` | Pressure coefficient Cp |
| `slice-pressure.png` | Pressure field cross-section |
| `slice-velocity.png` | Velocity magnitude cross-section |
| `streamline-<view>.png` | 3D streamlines |
| `yplus-<view>.png` | Wall y⁺ distribution |

## Project Structure

```text
├── case_template/   # OpenFOAM case template
├── solve.py         # Main pipeline script
├── post_process.py  # ParaView rendering script
└── Wing.stl         # Input geometry
```
