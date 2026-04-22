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

    # Reflect the Wing
    reflect = Reflect(Input=reader)
    reflect.Plane = 'Y Min'
    reflect.CopyInput = 1
    reflect.UpdatePipeline(latest_time)

    # Tell ParaView to display the reflection, NOT the original reader
    display = Show(reflect, renderView)
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

    # 1. Setup and Reflect the internal mesh slice
    slice = Slice(Input=reader1)
    slice.SliceType = "Plane"
    slice.SliceType.Origin = [0.4, 0.6, 0.25]
    slice.SliceType.Normal = [0, 1, 0]
    slice.UpdatePipeline(latest_time)

    slice_reflect = Reflect(Input=slice)
    slice_reflect.Plane = 'Y Min'
    slice_reflect.CopyInput = 1
    slice_reflect.UpdatePipeline(latest_time)

    display1 = Show(slice_reflect, renderView)
    display1.Representation = "Surface With Edges"
    ColorBy(display1, ("CELLS", ""))

    # 2. Setup and Reflect the Wing surface
    reader2.MeshRegions = ["patch/Wing"]
    reader2.UpdatePipeline(latest_time)

    wing_reflect = Reflect(Input=reader2)
    wing_reflect.Plane = 'Y Min'
    wing_reflect.CopyInput = 1
    wing_reflect.UpdatePipeline(latest_time)

    display2 = Show(wing_reflect, renderView)
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

    # Reflect the calculated fields
    reflect = Reflect(Input=calculator1)
    reflect.Plane = 'Y Min'
    reflect.CopyInput = 1
    reflect.UpdatePipeline(latest_time)

    cpLUT = GetColorTransferFunction("Cp")
    cpPWF = GetOpacityTransferFunction("Cp")

    # Display the reflection
    display1 = Show(reflect, renderView)
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

    # Reflect the slice
    reflect = Reflect(Input=slice)
    reflect.Plane = 'Y Min'
    reflect.CopyInput = 1
    reflect.UpdatePipeline(latest_time)

    pLUT = GetColorTransferFunction("p")
    HideScalarBarIfNotNeeded(pLUT, renderView)

    display1 = Show(reflect, renderView)
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

    # Reflect the slice
    reflect = Reflect(Input=slice)
    reflect.Plane = 'Y Min'
    reflect.CopyInput = 1
    reflect.UpdatePipeline(latest_time)

    display1 = Show(reflect, renderView)
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
    
    # 1. Setup and reflect Wing
    reader2.MeshRegions = ["patch/Wing"]
    reader2.UpdatePipeline(latest_time)

    wing_reflect = Reflect(Input=reader2)
    wing_reflect.Plane = 'Y Min'
    wing_reflect.CopyInput = 1
    wing_reflect.UpdatePipeline(latest_time)

    display2 = Show(wing_reflect, renderView)
    ColorBy(display2, ("CELLS", ""))

    # 2. Setup Streamlines from the internal mesh directly (Matches your GUI!)
    reader1.UpdatePipeline(latest_time)

    streamTracer = StreamTracer(Input=reader1, SeedType="Line")
    
    # Seed points
    streamTracer.SeedType.Point1 = [-1.23, -0.07, 0.035]
    streamTracer.SeedType.Point2 = [-1.23, 1.13, 0.035]
    streamTracer.SeedType.Resolution = 100
    streamTracer.Vectors = ["POINTS", "U"]
    
    streamTracer.MaximumStreamlineLength = 100.0  # Make this larger than your domain length
    streamTracer.MaximumSteps = 10000

    tube = Tube(Input=streamTracer)
    tube.Radius = 0.001
    tube.UpdatePipeline(latest_time)

    # Reflect the tubes so they mirror across the symmetry plane
    tube_reflect = Reflect(Input=tube)
    tube_reflect.Plane = 'Y Min'
    tube_reflect.CopyInput = 1
    tube_reflect.UpdatePipeline(latest_time)

    tubeDisplay = Show(tube_reflect, renderView)
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

    # Reflect the wing data
    reflect = Reflect(Input=reader)
    reflect.Plane = 'Y Min'
    reflect.CopyInput = 1
    reflect.UpdatePipeline(latest_time)

    wallShearStressLUT = GetColorTransferFunction("wallShearStress")
    HideScalarBarIfNotNeeded(wallShearStressLUT, renderView)

    display1 = Show(reflect, renderView)
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

    # Reflect the wing data
    reflect = Reflect(Input=reader)
    reflect.Plane = 'Y Min'
    reflect.CopyInput = 1
    reflect.UpdatePipeline(latest_time)

    display1 = Show(reflect, renderView)
    ColorBy(display1, ("CELLS", "yPlus"))
    
    # MANUAL RANGE ASSIGNMENT: yPlus [1, 30]
    yPlusLUT = GetColorTransferFunction("yPlus")
    yPlusLUT.RescaleTransferFunction(1.0, 30.0)
    
    display1.SetScalarBarVisibility(renderView, True)

    save_all_views(renderView, "yplus")
    ResetSession()
    
if __name__ == "__main__":
    geometry()
    # mesh()
    cp_countour()
    pressure_slice()
    velocity_slice()
    streamlines()
    # wall_shear()
    yplus()