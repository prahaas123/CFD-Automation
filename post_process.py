import glob
import os
import sys

from paraview.simple import * # type: ignore

paraview.simple._DisableFirstRenderCameraReset()

# Run this script with: export PYTHONPATH="/usr/lib/python3/dist-packages:$PYTHONPATH"
# Then execute: LIBGL_ALWAYS_SOFTWARE=1 pvbatch render_views.py para.foam images

# ==============================================================================
# CONFIGURATION: CAMERA ANGLES & VIEWS
# ==============================================================================

# Global camera focus point (Center of your wing)
FOCAL_POINT = [0.15, 0.5, 0.18]

# Global output resolutions
VIEW_SIZE_HIRES = [15360, 8640]
VIEW_SIZE_STANDARD = [3840, 2160]

# The 5 primary views for 3D outputs (Geometry, Cp, Y+, Shear, Streamlines)
VIEWS_3D = {
    "diagonal": {"position": [-0.65, -0.49, 0.84], "view_up": [0.37, 0.31, 0.87]},
    "front":    {"position": [-1.10, 0.5, 0.05],  "view_up": [0, 0, 1]},
    "side":     {"position": [0.4, -0.95, 0.16],  "view_up": [0, 0, 1]},
    "top":      {"position": [0.29, 0.5, 1.83],   "view_up": [-1, 0, 0]}
}

# The camera used for 2D Slice outputs (Mesh, Pressure Slice, Velocity Slice)
VIEW_2D_SLICE = {
    "position": [0.22, 1.1, 0.05],
    "focal_point": [0.22, 0.0, 0.05],
    "view_up": [0, 0, 1],
    "slice-origin": [0.4, 0.6, 0.25],
    "slice-normal": [0, 1, 0]
}

# ==============================================================================

# validate inputs
if len(sys.argv) < 3:
    print("Usage: pvbatch script_name.py <path_to_your_openfoam_file> <folder_to_save_images>")
    sys.exit(1)

# parse inputs
input_filepath = sys.argv[1]
job_directory = sys.argv[2]
base_case_dir = os.path.dirname(input_filepath)

def get_latest_time(reader):
    """Helper function to find the final solved time step."""
    reader.UpdatePipelineInformation()
    times = reader.TimestepValues
    return times[-1] if len(times) > 0 else 0.0

def save_all_views(renderView, prefix):
    """Helper function to automatically loop through and save all 5 camera angles."""
    for view_name, cam in VIEWS_3D.items():
        renderView.CameraPosition = cam["position"]
        renderView.CameraFocalPoint = FOCAL_POINT
        renderView.CameraViewUp = cam["view_up"]
        Render()
        SaveScreenshot(f"{job_directory}/{prefix}-{view_name}.png", renderView, ImageResolution=renderView.ViewSize)

def geometry():
    reader = OpenDataFile(input_filepath)
    latest_time = get_latest_time(reader)

    renderView = CreateView("RenderView")
    renderView.ViewSize = VIEW_SIZE_HIRES
    renderView.ViewTime = latest_time

    reader.MeshRegions = ["patch/Wing"]
    reader.UpdatePipeline(latest_time)

    display = Show(reader, renderView)
    ColorBy(display, ("CELLS", ""))

    save_all_views(renderView, "geometry")
    ResetSession()
    
def mesh():
    reader1 = OpenDataFile(input_filepath)
    reader2 = OpenDataFile(input_filepath)
    latest_time = get_latest_time(reader1)

    renderView = CreateView("RenderView")
    renderView.ViewSize = VIEW_SIZE_STANDARD
    renderView.ViewTime = latest_time
    
    # Apply 2D Slice Camera
    renderView.CameraPosition = VIEW_2D_SLICE["position"]
    renderView.CameraFocalPoint = VIEW_2D_SLICE["focal_point"]
    renderView.CameraViewUp = VIEW_2D_SLICE["view_up"]
    renderView.OrientationAxesVisibility = 0

    # 1. Setup the internal mesh slice
    slice = Slice(Input=reader1)
    slice.SliceType = "Plane"
    slice.SliceType.Origin = [0.4, 0.6, 0.25]
    slice.SliceType.Normal = [0, 1, 0]
    slice.UpdatePipeline(latest_time)

    display1 = Show(slice, renderView)
    display1.Representation = "Surface With Edges"
    ColorBy(display1, ("CELLS", ""))

    # 2. Setup the Wing surface
    reader2.MeshRegions = ["patch/Wing"]
    reader2.UpdatePipeline(latest_time)

    display2 = Show(reader2, renderView)
    display2.Representation = "Surface With Edges"
    ColorBy(display2, ("CELLS", ""))

    Render()
    SaveScreenshot(f"{job_directory}/mesh.png", renderView, ImageResolution=renderView.ViewSize)
    ResetSession()
    
def cp_countour():
    reader = OpenDataFile(input_filepath)
    latest_time = get_latest_time(reader)
    
    reader.MeshRegions = ["patch/Wing"]
    reader.UpdatePipeline(latest_time)

    renderView = CreateView("RenderView")
    renderView.ViewSize = VIEW_SIZE_STANDARD
    renderView.ViewTime = latest_time

    pLUT = GetColorTransferFunction("p")
    HideScalarBarIfNotNeeded(pLUT, renderView)

    calculator1 = Calculator(registrationName="Calculator1", Input=reader)
    calculator1.ResultArrayName = "Cp"
    calculator1.Function = "(p - 0)/(0.5*1.225*100)"
    calculator1.AttributeType = "Cell Data"
    calculator1.UpdatePipeline(latest_time)
    
    cpLUT = GetColorTransferFunction("Cp")
    cpPWF = GetOpacityTransferFunction("Cp")

    display1 = Show(calculator1, renderView)
    display1.RescaleTransferFunctionToDataRange(True, False)
    display1.SetScalarBarVisibility(renderView, True)

    ColorBy(display1, ("CELLS", "Cp"))

    save_all_views(renderView, "cp-contour")
    ResetSession()
    
def pressure_slice():
    reader = OpenDataFile(input_filepath)
    latest_time = get_latest_time(reader)

    renderView = CreateView("RenderView")
    renderView.ViewSize = VIEW_SIZE_STANDARD
    renderView.ViewTime = latest_time
    
    # Apply 2D Slice Camera
    renderView.CameraPosition = VIEW_2D_SLICE["position"]
    renderView.CameraFocalPoint = VIEW_2D_SLICE["focal_point"]
    renderView.CameraViewUp = VIEW_2D_SLICE["view_up"]

    slice = Slice(Input=reader)
    slice.SliceType = "Plane"
    slice.SliceType.Origin = VIEW_2D_SLICE["slice-origin"]
    slice.SliceType.Normal = VIEW_2D_SLICE["slice-normal"]
    slice.UpdatePipeline(latest_time)

    pLUT = GetColorTransferFunction("p")
    HideScalarBarIfNotNeeded(pLUT, renderView)

    display1 = Show(slice, renderView)
    ColorBy(display1, ("CELLS", "p", "Magnitude"))
    display1.RescaleTransferFunctionToDataRange(True, False)
    display1.SetScalarBarVisibility(renderView, True)

    Render()
    SaveScreenshot(f"{job_directory}/slice-pressure.png", renderView, ImageResolution=renderView.ViewSize)
    ResetSession()

def velocity_slice():
    reader = OpenDataFile(input_filepath)
    latest_time = get_latest_time(reader)

    renderView = CreateView("RenderView")
    renderView.ViewSize = VIEW_SIZE_STANDARD
    renderView.ViewTime = latest_time
    
    # Apply 2D Slice Camera
    renderView.CameraPosition = VIEW_2D_SLICE["position"]
    renderView.CameraFocalPoint = VIEW_2D_SLICE["focal_point"]
    renderView.CameraViewUp = VIEW_2D_SLICE["view_up"]

    slice = Slice(Input=reader)
    slice.SliceType = "Plane"
    slice.SliceType.Origin = VIEW_2D_SLICE["slice-origin"]
    slice.SliceType.Normal = VIEW_2D_SLICE["slice-normal"]
    slice.UpdatePipeline(latest_time)

    display1 = Show(slice, renderView)
    ColorBy(display1, ("CELLS", "U", "Magnitude"))
    
    # MANUAL RANGE ASSIGNMENT: Velocity [10, 30]
    uLUT = GetColorTransferFunction("U")
    uLUT.RescaleTransferFunction(10.0, 30.0)
    
    display1.SetScalarBarVisibility(renderView, True)

    Render()
    SaveScreenshot(f"{job_directory}/slice-velocity.png", renderView, ImageResolution=renderView.ViewSize)
    ResetSession()

def streamlines():
    # reader1 is the internalMesh (for the fluid)
    reader1 = OpenDataFile(input_filepath)
    # reader2 is the patch (for the solid wing)
    reader2 = OpenDataFile(input_filepath)
    latest_time = get_latest_time(reader1)

    renderView = CreateView("RenderView")
    renderView.ViewSize = VIEW_SIZE_STANDARD
    renderView.ViewTime = latest_time
    
    # 1. Setup Wing
    reader2.MeshRegions = ["patch/Wing"]
    reader2.UpdatePipeline(latest_time)

    display2 = Show(reader2, renderView)
    ColorBy(display2, ("CELLS", ""))

    # 2. Setup Streamlines from the internal mesh directly
    reader1.UpdatePipeline(latest_time)

    streamTracer = StreamTracer(Input=reader1, SeedType="Line")
    
    # Seed points
    streamTracer.SeedType.Point1 = [-0.5, -0.05, 0.03]
    streamTracer.SeedType.Point2 = [-0.5, 1.1, 0.03]
    streamTracer.SeedType.Resolution = 200
    streamTracer.Vectors = ["POINTS", "U"]
    
    streamTracer.MaximumStreamlineLength = 300.0  # Make this larger than your domain length
    streamTracer.MaximumSteps = 10000

    tube = Tube(Input=streamTracer)
    tube.Radius = 0.001
    tube.UpdatePipeline(latest_time)

    tubeDisplay = Show(tube, renderView)
    ColorBy(tubeDisplay, ("POINTS", "U", "Magnitude"))
    
    # MANUAL RANGE ASSIGNMENT
    uLUT = GetColorTransferFunction("U")
    uLUT.RescaleTransferFunction(15.0, 25.0)
    
    tubeDisplay.SetScalarBarVisibility(renderView, True)

    save_all_views(renderView, "streamline")
    ResetSession()

def wall_shear():
    reader = OpenDataFile(input_filepath)
    latest_time = get_latest_time(reader)

    renderView = CreateView("RenderView")
    renderView.ViewSize = VIEW_SIZE_STANDARD
    renderView.ViewTime = latest_time

    reader.MeshRegions = ["patch/Wing"]
    reader.UpdatePipeline(latest_time)

    wallShearStressLUT = GetColorTransferFunction("wallShearStress")
    HideScalarBarIfNotNeeded(wallShearStressLUT, renderView)

    display1 = Show(reader, renderView)
    UpdateScalarBarsComponentTitle(wallShearStressLUT, display1)

    ColorBy(display1, ("CELLS", "wallShearStress", "X"))
    display1.RescaleTransferFunctionToDataRange(True, False)
    display1.SetScalarBarVisibility(renderView, True)

    save_all_views(renderView, "wall-shear")
    ResetSession()

def yplus():
    reader = OpenDataFile(input_filepath)
    latest_time = get_latest_time(reader)

    renderView = CreateView("RenderView")
    renderView.ViewSize = VIEW_SIZE_STANDARD
    renderView.ViewTime = latest_time

    reader.MeshRegions = ["patch/Wing"]
    reader.UpdatePipeline(latest_time)

    display1 = Show(reader, renderView)
    ColorBy(display1, ("CELLS", "yPlus"))
    
    # MANUAL RANGE ASSIGNMENT: yPlus [1, 30]
    yPlusLUT = GetColorTransferFunction("yPlus")
    yPlusLUT.RescaleTransferFunction(1.0, 30.0)
    
    display1.SetScalarBarVisibility(renderView, True)

    save_all_views(renderView, "yplus")
    ResetSession()
    
def print_and_plot_stats():
    print("\n" + "="*50)
    print("📊 EXTRACTING FINAL STATS & PLOTTING CONVERGENCE")
    print("="*50)

    # 1. EXTRACT Y+ FROM TEXT DATA
    avg_yp, max_yp = 0.0, 0.0
    try:
        y_files = glob.glob(f"{base_case_dir}/postProcessing/yPlus/*/yPlus.dat")
        if y_files:
            latest_y_file = sorted(y_files)[-1]
            with open(latest_y_file, 'r') as f:
                for line in f:
                    if line.startswith('#'): continue
                    parts = line.split()
                    if len(parts) >= 4 and parts[1] == "Wing":
                        avg_yp = float(parts[4])
                        max_yp = float(parts[3])
    except Exception as e:
        print(f"Warning: Could not extract yPlus data from mesh. Error: {e}")

    # 2. EXTRACT AND PLOT FORCE COEFFICIENTS
    cl_val, cd_val, cm_val = 0.0, 0.0, 0.0
    try:
        import matplotlib.pyplot as plt
        
        times, cls, cds = [], [], []
        coeff_files = glob.glob(f"{base_case_dir}/postProcessing/forceCoeffsWing/*/coefficient.dat")
        if coeff_files:
            latest_coeff_file = sorted(coeff_files)[-1]
            with open(latest_coeff_file, 'r') as f:
                for line in f:
                    if line.startswith('#'): continue
                    parts = line.split()
                    if len(parts) >= 8:
                        times.append(float(parts[0]))
                        cds.append(float(parts[1]))
                        cls.append(float(parts[4]))
                        cd_val = float(parts[1])
                        cl_val = float(parts[4])
                        cm_val = float(parts[7])
            
            # Generate CL Plot
            plt.figure(figsize=(8, 5))
            plt.plot(times, cls, label="Cl", color="#1f77b4", linewidth=2)
            plt.xlabel("Iteration")
            plt.ylabel("Lift Coefficient (Cl)")
            plt.title("Lift Coefficient Convergence")
            plt.grid(True, linestyle="--", alpha=0.7)
            plt.ylim(-1.5, 2.5)
            plt.savefig(f"{job_directory}/convergence_Cl.png", dpi=300, bbox_inches="tight")
            plt.close()

            # Generate CD Plot
            plt.figure(figsize=(8, 5))
            plt.plot(times, cds, label="Cd", color="#d62728", linewidth=2)
            plt.xlabel("Iteration")
            plt.ylabel("Drag Coefficient (Cd)")
            plt.title("Drag Coefficient Convergence")
            plt.grid(True, linestyle="--", alpha=0.7)
            plt.ylim(0, 1.5)
            plt.savefig(f"{job_directory}/convergence_Cd.png", dpi=300, bbox_inches="tight")
            plt.close()
    except Exception as e:
        print(f"Warning: Could not process/plot coefficients. Ensure matplotlib is installed. Error: {e}")

    # 3. EXTRACT RAW FORCES
    lift_force, drag_force = 0.0, 0.0
    try:
        force_files = glob.glob(f"{base_case_dir}/postProcessing/forcesWing/*/force.dat")
        if force_files:
            latest_force_file = sorted(force_files)[-1]
            with open(latest_force_file, 'r') as f:
                lines = [l for l in f.readlines() if not l.startswith('#')]
                if lines:
                    last_line = lines[-1]
                    clean_line = last_line.replace('(', ' ').replace(')', ' ')
                    parts = clean_line.split()
                    
                    if len(parts) >= 4:
                        drag_force = float(parts[1]) # Flow is along X
                        lift_force = float(parts[3]) # Lift is along Z
    except Exception as e:
        print(f"Warning: Could not process raw forces. Error: {e}")

    # 4. TERMINAL OUTPUT
    print("\n" + "═"*40)
    print(" 🏁 SIMULATION RESULTS SUMMARY")
    print("═"*40)
    print(f"  Lift Coefficient (CL) :  {cl_val:.5f}")
    print(f"  Drag Coefficient (CD) :  {cd_val:.5f}")
    print(f"  Lift-to-Drag Ratio    :  {cl_val/cd_val if cd_val != 0 else 'N/A'}")
    print(f"  Pitch Moment (CM)     :  {cm_val:.5f}")
    print("-" * 40)
    print(f"  Total Lift Force (Z)  :  {lift_force:.2f} N")
    print(f"  Total Drag Force (X)  :  {drag_force:.2f} N")
    print("-" * 40)
    print(f"  Average y+            :  {avg_yp:.3f}")
    print(f"  Maximum y+            :  {max_yp:.3f}")
    print("═"*40 + "\n")
    
    # 5. APPEND TO CSV
    try:
        import csv
        ld_ratio = cl_val / cd_val if cd_val != 0 else 0.0
        case_name = os.path.basename(base_case_dir)
        alpha = case_name.replace("run_alpha_", "")
        project_dir = os.path.dirname(base_case_dir) or "."
        csv_file_path = os.path.join(project_dir, "results.csv")
        file_exists = os.path.isfile(csv_file_path)
        
        with open(csv_file_path, mode='a', newline='') as csv_file:
            writer = csv.writer(csv_file)
            if not file_exists:
                writer.writerow(["Alpha", "CL", "CD", "L/D", "CM", "Lift_N", "Drag_N", "Avg_yPlus", "Max_yPlus"])
            
            # Write the data row
            writer.writerow([
                alpha,
                f"{cl_val:.5f}",
                f"{cd_val:.5f}",
                f"{ld_ratio:.5f}",
                f"{cm_val:.5f}",
                f"{lift_force:.2f}",
                f"{drag_force:.2f}",
                f"{avg_yp:.3f}",
                f"{max_yp:.3f}"
            ])
    except Exception as e:
        print(f"Warning: Could not write to CSV. Error: {e}")
    
if __name__ == "__main__":
    geometry()
    mesh()
    cp_countour()
    pressure_slice()
    velocity_slice()
    streamlines()
    wall_shear()
    yplus()
    print_and_plot_stats()