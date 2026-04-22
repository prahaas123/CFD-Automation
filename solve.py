import os
import subprocess
import shutil
from PyFoam.RunDictionary.SolutionDirectory import SolutionDirectory
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.Execution.BasicRunner import BasicRunner

GEOMETRY_STL = "Wing.stl"

def main():
    processors_per_job = 4
    
    # Parameters
    cg = 0.25        # Center of gravity x-coordinate
    u = 50.0         # Freestream velocity (MagUInf)
    c = 1.0          # Reference chord (lRef)
    S = 1.0          # Reference area (Aref)
    
    alphas = [0.0, 5.0, 10.0]

    for alpha in alphas:
        job_id = f"run_alpha_{int(alpha)}"
        job_directory = f"./{job_id}"
        
        print(f"\n{'='*40}")
        print(f"Starting Simulation: {job_id} | Alpha: {alpha}°")
        print(f"{'='*40}")

        # 1. Prepare Case Directory
        print("[1/5] Preparing case from template...")
        if not prepare(job_directory, processors_per_job, cg, u, c, S):
            print(f"Error: Failed to prepare case for {job_id}. Skipping...")
            continue
            
        # 2. Setup Geometry
        geom_target_path = os.path.join(job_directory, f"{job_id}.stl")
        shutil.copy(GEOMETRY_STL, geom_target_path)

        # 3. Mesh Generation
        print("[2/5] Generating mesh (blockMesh, snappyHexMesh)...")
        try:
            if not mesh(job_directory, job_id, alpha, processors_per_job):
                print(f"Error: Meshing failed to produce polyMesh for {job_id}. Skipping...")
                continue
        except Exception as e:
            print(f"Exception during meshing: {e}")
            continue

        # 4. Solve
        print("[3/5] Solving (foamRun)...")
        try:
            if not solve(job_directory, processors_per_job):
                print(f"Error: Solver failed to complete for {job_id}. Skipping...")
                continue
        except Exception as e:
            print(f"Exception during solving: {e}")
            continue

        # 5. Post-Process
        print("[4/5] Running ParaView post-processing...")
        try:
            if not postprocess(job_directory):
                print(f"Warning: Post-processing failed or images not generated for {job_id}.")
        except Exception as e:
            print(f"Exception during post-processing: {e}")

        # 6. Clean Up
        print("[5/5] Cleaning up heavy mesh/processor files...")
        cleanup(job_directory)
        
        print(f"Successfully completed {job_id}!")

def prepare(job_directory, processors_per_job, cg, u, c, S):
    try:
        case_template = SolutionDirectory("case_template")
        case_template.cloneCase(job_directory)
        
        # decomposParDict
        decompose_par_dict_filepath = f"{job_directory}/system/decomposeParDict"
        decompose_par_dict = ParsedParameterFile(decompose_par_dict_filepath)
        decompose_par_dict["numberOfSubdomains"] = processors_per_job
        decompose_par_dict.writeFile()
        
        # controlDict
        control_dict_filepath = f"{job_directory}/system/controlDict"
        control_dict_file = ParsedParameterFile(control_dict_filepath)
        control_dict_file["functions"]["forceCoeffs_Wing"]["lRef"] = c
        control_dict_file["functions"]["forceCoeffs_Wing"]["Aref"] = S
        control_dict_file["functions"]["forceCoeffs_Wing"]["MagUInf"] = u
        CofR = f"({cg} 0 0)"
        control_dict_file["functions"]["forceCoeffs_Wing"]["CofR"] = CofR
        control_dict_file["functions"]["forces_Wing"]["CofR"] = CofR
        control_dict_file.writeFile()
        
        run_ok = True
    except:
        run_ok = False
        
    return run_ok

def mesh(job_directory, job_id, alpha, processors_per_job):
    COMMANDS = [
        f"surfaceTransformPoints -case {job_directory} -rotate-angle '((0 1 0) {alpha})' {job_directory}/{job_id}.stl {job_directory}/aoa.stl",
        f"blockMesh -case {job_directory}",
        f"surfaceFeatures -case {job_directory}",
        f"decomposePar -case {job_directory}",
        f"mpirun -np {processors_per_job} snappyHexMesh -case {job_directory} -parallel",
        f"reconstructPar -case {job_directory} -constant",
        f"rm -rf {job_directory}/processor*",
    ]

    for command in COMMANDS:
        runner = BasicRunner(argv=command.split(" "))
        runner.start()
        if not runner.runOK():
            raise Exception(f"{command} failed")

    run_ok = True
    if not os.path.isdir(f"{job_directory}/constant/polyMesh"):
        run_ok = False
    return run_ok

def solve(job_directory, processors_per_job):
    COMMANDS = [
        f"decomposePar -case {job_directory}",
        f"mpirun --oversubscribe -np {processors_per_job} foamRun -case {job_directory} -parallel > log.foamRun &",
        f"reconstructPar -case {job_directory} -constant",
        f"rm -rf {job_directory}/proc*",
    ]

    for command in COMMANDS:
        runner = BasicRunner(argv=command.split(" "))
        runner.start()
        if not runner.runOK():
            raise Exception(f"{command} failed")

    run_ok = True
    if not os.path.isdir(f"{job_directory}/40"):
        run_ok = False
    return run_ok

def postprocess(job_directory):
    COMMANDS = [
        f"export PYTHONPATH=\"/usr/lib/python3/dist-packages:$PYTHONPATH\"",
        f"mkdir -p {job_directory}/images",
        f"LIBGL_ALWAYS_SOFTWARE=1 pvbatch post_process.py {job_directory}/para.foam {job_directory}/images"
    ]

    for command in COMMANDS:
        runner = BasicRunner(argv=command.split(" "))
        runner.start()
        if not runner.runOK():
            raise Exception(f"{command} failed")

    run_ok = True
    if not os.path.isdir(f"{job_directory}/images"):
        run_ok = False
    return run_ok

def cleanup(job_directory):
    COMMANDS = (
        f"pyFoamClearCase.py {job_directory} --keep-postprocessing --processors-remove",
        f"rm -rf {job_directory}/constant/polyMesh",
    )

    for command in COMMANDS:
        subprocess.run(command.split(" "), capture_output=True, text=True, check=True)

if __name__ == "__main__":
    main()