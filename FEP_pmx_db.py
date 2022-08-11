#!/usr/bin/env python3

import os
import sys
import sqlite3
import argparse
import subprocess


def parse():
    parser = argparse.ArgumentParser(
        description='FEB database', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--db',
        help="Database file; must be in working directory",
        required=True)
    parser.add_argument(
        '--add',
        help="directories that will be added to calculations' list; comma separator is used")
    parser.add_argument(
        '--stage',
        help="stages of calculations that will be added to calculations' list; comma separator is used")
    parser.add_argument(
        '--remove',
        help="folders that will be removed from calculations' list; comma separator is used")
    parser.add_argument(
        '--force',
        action='store_true',
        help="Forces updating of tasks")
    parser.add_argument(
        '--run',
        action='store_true',
        help="Run one step for all tasks")
    parser.add_argument(
        '--dump',
        action='store_true',
        help="Dump database")
    parser.add_argument(
        '--dump_csv',
        help="Dump database to file")
    args = parser.parse_args()

    if args.add != None and args.stage != None:
        args.add = args.add.split(",")
        args.stage = args.stage.split(",")
        if len(args.stage) != len(args.add):
            print("--add and --stage must have the same length of argument!")
            sys.exit(1)
    elif args.add != None or args.stage != None:
        print("Both --add and --stage must be defined!")
        sys.exit(1)
    if args.remove != None:
        args.remove = args.remove.split(",")

    if args.remove != None and args.add != None:
        print("Both --add and --remove must not be defined!")
        sys.exit(1)

    return args


def SLURMscript(script, nodes=1, ntasks=1, ntasks_per_node=48, jobname="", time="48:00:00", partition="hpc4-3d"):
    cpus_per_task = 48 * nodes // ntasks
    return f"""#!/bin/bash
#SBATCH --nodes={nodes}
#SBATCH --ntasks={ntasks}
#SBATCH --ntasks-per-node={ntasks_per_node}
#SBATCH --cpus-per-task={cpus_per_task}
#SBATCH --job-name={jobname}
#SBATCH -o work-%J.out
#SBATCH -e work-%J.err
#SBATCH --time={time}
#SBATCH --get-user-env
#SBATCH --partition={partition}

srun bash {script}
"""


def SLURMbatch(script, array=None):
    if array == None:
      out, err = subprocess.Popen(
          f"sbatch {script}", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
    else:
      arrt = array - 1
      out, err = subprocess.Popen(
          f"sbatch --array=0-{arrt} {script}", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
    out = out.decode('ascii')
    task = "ERROR_SLURM"
    if "Submitted batch job" in out:
        task = out.split()[3]
    return task


def SLURMwait(taskIDs):
    taskIDs = taskIDs.replace(";", ",")
    out, err = subprocess.Popen(
        f"squeue -j {taskIDs}", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
    out = out.decode('ascii')
    err = err.decode('ascii')
    if "slurm_load_jobs error: Invalid job id specified" in err:
        return "Done"
    res = len(out.split("\n"))
    if res > 2:
        return "Waiting"
    return "Done"


def SLURMstop(taskIDs):
    taskIDs = taskIDs.replace(";", ",")
    os.system(f"scancel -j ${taskIDs}")


class Task:
    def __init__(self, task, root):
        self.task = task
        self.root = root
        self.path = self.root + "/" + self.task
        self.maxwarn = 20
        self.omp_threads = 6

    def prepare(self):
        self.NI("prepare")

    def run(self):
        self.NI("run")
        taskIDs = ""  # separator - `;`; error in SLURM - "SLURM_ERROR"
        return taskIDs

    def wait(self, taskIDs):
        self.NI("wait")
        status = "Done"  # Done/Waiting
        return status

    def check(self):
        self.NI("check")
        status = "PASS"  # PASS/FAIL
        return status

    def NI(self, function):
        print(
            f"Function '{function}' in not implemented for stage '{self.task}'!")


class MDPreparation(Task):
    def __init__(self, task, root):
        super().__init__(task, root)

    def prepare(self):
        # create directories
        os.mkdir(f"{self.path}/stateA_water")
        os.mkdir(f"{self.path}/stateB_water")
        os.mkdir(f"{self.path}/stateA_protein")
        os.mkdir(f"{self.path}/stateB_protein")
        os.mkdir(f"{self.path}/result_water")
        os.mkdir(f"{self.path}/result_protein")

        command = f"""#!/usr/bin/env bash

module load anaconda3/python3-5.1.0 openmpi/4.1.0 gromacs/2021
#
export OMP_NUM_THREADS={self.omp_threads}
#
pushd {self.path}
#
gmx_mpi editconf -f merged.pdb -o stateA_water/box.pdb -d 1.5 -bt cubic
awk '/ATOM/ {{print $ 0}}' protein_pdb2gmx.pdb merged.pdb> stateA_protein/protein_ligand.pdb
gmx_mpi editconf -f stateA_protein/protein_ligand.pdb -o stateA_protein/box.pdb -d 1.5 -bt cubic
gmx_mpi solvate -cs spc216.gro -cp stateA_water/box.pdb -o stateA_water/water.pdb -p top_water.top
gmx_mpi solvate -cs spc216.gro -cp stateA_protein/box.pdb -o stateA_protein/water.pdb -p topol.top
gmx_mpi grompp -f mdp/emA.mdp -c stateA_water/water.pdb -o stateA_water/water.tpr -p top_water.top -maxwarn {self.maxwarn}
gmx_mpi grompp -f mdp/emA.mdp -c stateA_protein/water.pdb -o stateA_protein/water.tpr -p topol.top -maxwarn {self.maxwarn}
#
echo 4 | gmx_mpi genion -s stateA_water/water.tpr -neutral -conc 0.15 -o stateA_water/ions.pdb -nname CLJ -pname NAJ -p top_water.top
echo 15 | gmx_mpi genion -s stateA_protein/water.tpr -neutral -conc 0.15 -o stateA_protein/ions.pdb -nname CLJ -pname NAJ -p topol.top
#
gmx_mpi grompp -f mdp/emA.mdp -c stateA_water/ions.pdb -o stateA_water/em.tpr -p top_water.top -maxwarn {self.maxwarn}
gmx_mpi grompp -f mdp/emB.mdp -c stateA_water/ions.pdb -o stateB_water/em.tpr -p top_water.top -maxwarn {self.maxwarn}
gmx_mpi grompp -f mdp/emA.mdp -c stateA_protein/ions.pdb -o stateA_protein/em.tpr -p topol.top -maxwarn {self.maxwarn}
gmx_mpi grompp -f mdp/emB.mdp -c stateA_protein/ions.pdb -o stateB_protein/em.tpr -p topol.top -maxwarn {self.maxwarn}
#
gmx_mpi mdrun -s stateA_water/em.tpr -c stateA_water/emout.gro -v -ntomp {self.omp_threads} &
gmx_mpi mdrun -s stateB_water/em.tpr -c stateB_water/emout.gro -v -ntomp {self.omp_threads} &
gmx_mpi mdrun -s stateA_protein/em.tpr -c stateA_protein/emout.gro -v -ntomp {self.omp_threads} &
gmx_mpi mdrun -s stateB_protein/em.tpr -c stateB_protein/emout.gro -v -ntomp {self.omp_threads} &
#
wait
#
gmx_mpi grompp -f mdp/eqA.mdp -c stateA_water/emout.gro -o stateA_water/eq.tpr -p top_water.top -maxwarn {self.maxwarn}
gmx_mpi grompp -f mdp/eqB.mdp -c stateB_water/emout.gro -o stateB_water/eq.tpr -p top_water.top -maxwarn {self.maxwarn}
gmx_mpi grompp -f mdp/eqA.mdp -c stateA_protein/emout.gro -o stateA_protein/eq.tpr -p topol.top -maxwarn {self.maxwarn}
gmx_mpi grompp -f mdp/eqB.mdp -c stateB_protein/emout.gro -o stateB_protein/eq.tpr -p topol.top -maxwarn {self.maxwarn}
#
popd
"""
        open(f"{self.path}/MD_preparation.sh", "w").write(command)

    def run(self):
        os.system(f"bash {self.path}/MD_preparation.sh")
        return ""

    def wait(self, taskIDs):
        return "Done"


class MD(Task):
    def __init__(self, task, root):
        super().__init__(task, root)
        self.omp_threads = 24

    def prepare(self):
        command = f"""#!/usr/bin/env bash

module load anaconda3/python3-5.1.0 openmpi/4.1.0 gromacs/2021
#
export OMP_NUM_THREADS={self.omp_threads}
#
pushd {self.path}
#
mpirun -n 1 gmx_mpi mdrun -s stateA_water/eq.tpr -x stateA_water/traj_comp.xtc -ntomp {self.omp_threads}
mpirun -n 1 gmx_mpi mdrun -s stateB_water/eq.tpr -x stateB_water/traj_comp.xtc -ntomp {self.omp_threads}
mpirun -n 1 gmx_mpi mdrun -s stateA_protein/eq.tpr -x stateA_protein/traj_comp.xtc -ntomp {self.omp_threads}
mpirun -n 1 gmx_mpi mdrun -s stateB_protein/eq.tpr -x stateB_protein/traj_comp.xtc -ntomp {self.omp_threads}
#
popd
"""
        open(f"{self.path}/MD.sh", "w").write(command)
        open(f"{self.path}/slurm-MD.sh", "w").write(SLURMscript(f"{self.path}/MD.sh",
                                                                nodes=1, ntasks=1, ntasks_per_node=1, jobname=f"MD-{self.task}"))

    def run(self):
        return SLURMbatch(f"{self.path}/slurm-MD.sh")

    def wait(self, taskIDs):
        return SLURMwait(taskIDs)


class FEPPreparation(Task):
    def __init__(self, task, root):
        super().__init__(task, root)
        self.maxwarn = 21

    def prepare(self):
        command = f"""#!/usr/bin/env bash

module load anaconda3/python3-5.1.0 openmpi/4.1.0 gromacs/2021
#
export OMP_NUM_THREADS={self.omp_threads}
#
pushd {self.path}
#
echo 0 | gmx_mpi trjconv -s stateA_water/eq.tpr -f stateA_water/traj_comp.xtc -o stateA_water/frame.gro -b 1 -pbc mol -ur compact -sep
echo 0 | gmx_mpi trjconv -s stateB_water/eq.tpr -f stateB_water/traj_comp.xtc -o stateB_water/frame.gro -b 1 -pbc mol -ur compact -sep
echo 0 | gmx_mpi trjconv -s stateA_protein/eq.tpr -f stateA_protein/traj_comp.xtc -o stateA_protein/frame.gro -b 1 -pbc mol -ur compact -sep
echo 0 | gmx_mpi trjconv -s stateB_protein/eq.tpr -f stateB_protein/traj_comp.xtc -o stateB_protein/frame.gro -b 1 -pbc mol -ur compact -sep
#
for i in `seq 0 99`
do
    gmx_mpi grompp -f mdp/tiA.mdp -p top_water.top -c stateA_water/frame${{i}}.gro -o stateA_water/tpr${{i}}.tpr -maxwarn {self.maxwarn}
    gmx_mpi grompp -f mdp/tiB.mdp -p top_water.top -c stateB_water/frame${{i}}.gro -o stateB_water/tpr${{i}}.tpr -maxwarn {self.maxwarn}
    gmx_mpi grompp -f mdp/tiA.mdp -p topol.top -c stateA_protein/frame${{i}}.gro -o stateA_protein/tpr${{i}}.tpr -maxwarn {self.maxwarn}
    gmx_mpi grompp -f mdp/tiB.mdp -p topol.top -c stateB_protein/frame${{i}}.gro -o stateB_protein/tpr${{i}}.tpr -maxwarn {self.maxwarn}
done
#
popd
"""
        open(f"{self.path}/FEP_preparation.sh", "w").write(command)

    def run(self):
        os.system(f"bash {self.path}/FEP_preparation.sh")
        return ""

    def wait(self, taskIDs):
        return "Done"


class FEP(Task):
    def __init__(self, task, root):
        super().__init__(task, root)

    def prepare(self):
        command = f"""#!/usr/bin/env bash

module load anaconda3/python3-5.1.0 openmpi/4.1.0 gromacs/2021
#
export OMP_NUM_THREADS={self.omp_threads}
export GMX_MAXBACKUP=-1
#
pushd {self.path}
#
let "JOBinternal=${{SLURM_ARRAY_TASK_ID}}*${{SLURM_NTASKS}}+${{SLURM_PROCID}}"
#
mpirun -n 1 gmx_mpi mdrun -v -s stateA_water/tpr${{JOBinternal}}.tpr -dhdl stateA_water/dhdl${{JOBinternal}}.xvg -ntomp {self.omp_threads} 2>&1 | tee stateA_water/dhdl${{JOBinternal}}.log_gmx
mpirun -n 1 gmx_mpi mdrun -v -s stateB_water/tpr${{JOBinternal}}.tpr -dhdl stateB_water/dhdl${{JOBinternal}}.xvg -ntomp {self.omp_threads} 2>&1 | tee stateB_water/dhdl${{JOBinternal}}.log_gmx
mpirun -n 1 gmx_mpi mdrun -v -s stateA_protein/tpr${{JOBinternal}}.tpr -dhdl stateA_protein/dhdl${{JOBinternal}}.xvg -ntomp {self.omp_threads} 2>&1 | tee stateA_protein/dhdl${{JOBinternal}}.log_gmx
mpirun -n 1 gmx_mpi mdrun -v -s stateB_protein/tpr${{JOBinternal}}.tpr -dhdl stateB_protein/dhdl${{JOBinternal}}.xvg -ntomp {self.omp_threads} 2>&1 | tee stateB_protein/dhdl${{JOBinternal}}.log_gmx
#
popd
"""
        open(f"{self.path}/FEP.sh", "w").write(command)
        open(f"{self.path}/slurm-FEP.sh", "w").write(SLURMscript(f"{self.path}/FEP.sh",
                                                                 nodes=5, ntasks=20, ntasks_per_node=4, jobname=f"FEP-{self.task}"))

    def run(self):
        return SLURMbatch(f"{self.path}/slurm-FEP.sh", array=5)

    def wait(self, taskIDs):
        return SLURMwait(taskIDs)


class ResultProcessing(Task):
    def __init__(self, task, root):
        super().__init__(task, root)

    def prepare(self):
        command = f"""#!/usr/bin/env bash

module load anaconda3/python3-5.1.0 openmpi/4.1.0 gromacs/2021
#
export OMP_NUM_THREADS={self.omp_threads}
#
pushd {self.path}
#
{self.root}/analyze_dhdl.py -fA stateA_water/dhdl*xvg   -fB stateB_water/dhdl*xvg   -o result_water/results_water.txt     -t 298
{self.root}/analyze_dhdl.py -fA stateA_protein/dhdl*xvg -fB stateB_protein/dhdl*xvg -o result_protein/results_protein.txt -t 298
{self.root}/extract.py --protein result_protein/results_protein.txt --water result_water/results_water.txt --output {self.path}/../result_{self.task}.csv --protein_name {self.task}
#
popd
"""
        open(f"{self.path}/Result_processing.sh", "w").write(command)

    def run(self):
        os.system(f"bash {self.path}/Result_processing.sh")
        return ""

    def wait(self, taskIDs):
        return "Done"

class FEPdb:
    STATUS = {0: "Not started",
              1: "Prepared",
              2: "In progress...",
              3: "Finished",
              4: "Failed",
              5: "Done"}
    STATUS_rev = {"Not started": 0,
                  "Prepared": 1,
                  "In progress...": 2,
                  "Finished": 3,
                  "Failed": 4,
                  "Done": 5}
    STAGE = {1: "MD preparation",
             2: "MD",
             3: "FEP preparation",
             4: "FEP",
             5: "Result processing"}
    db = None
    run = None

    def __init__(self, dbfile):
        self.root, _ = os.path.split(os.path.abspath(dbfile))
        self.db = sqlite3.connect(dbfile)
        self.run = self.db.cursor()
        if not self.FEP_table_exists():
            self.FEP_table_create()
        if self.FEP_table_exists():
            print("Starting...")

    def FEP_table_exists(self):
        FEP_table = self.run.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks_control'").fetchall()
        if len(FEP_table) != 0:
            return True
        return False

    def FEP_table_create(self):
        self.run.execute(
            "CREATE TABLE tasks_control (directory text, stage integer, status integer, taskID text)")
        self.db.commit()

    def get_task(self, directory):
        self.FEP_table_exists()
        FEP_select = self.run.execute(
            f"SELECT * FROM tasks_control WHERE directory = '{directory}'").fetchall()
        return FEP_select

    def stop_task(self, task):
        SLURMstop(task)

    def add_task(self, task, force):
        directory, stage = task
        istage = int(stage)
        if not 1 <= istage <= 5:
            print(f"For `{directory}`, stage is out of range!")
            return
        task = self.get_task(directory)
        if task != []:
            if force:
                _, _, tst, tt = task[0]
                if tst == 1:
                    # we need to stop SLURM tasks firstly
                    self.stop_task(tt)
                self.run.execute(
                    f"UPDATE tasks_control SET stage = {stage}, status = 0, taskID = '' WHERE directory = '{directory}'")
            else:
                print(
                    f"Run `./{sys.argv[0]} --add {directory} --stage {stage} --force` for overriding '{directory}' directory")
                print(
                    "  or remove this task via `./{sys.argv[0]} --remove {directory}`")
                return
        else:
            self.run.execute("INSERT INTO tasks_control VALUES (?, ?, ?, ?)",
                             (directory, stage, self.STATUS_rev["Not started"], ""))
        self.db.commit()

    def remove_task(self, directory, force):
        task = self.get_task(directory)
        if task == []:
            print(f"Task {directory} does not exist!")
            return
        task = task[0]
        td, tsg, tst, tt = task
        if tst == 1 and not force:
            print(
                f"'{directory}' is in progress... Use `--force` for removing this task.")
            return
        elif tst == 1 and force:
            self.stop_task(tt)
        self.run.execute(
            f"DELETE FROM tasks_control WHERE directory = '{directory}'")
        self.db.commit()

    def run_tasks(self):
        TaskClass = {1: MDPreparation, 2: MD,
                     3: FEPPreparation, 4: FEP, 5: ResultProcessing}
        #CallClass = {0:prepare, 1:run, 2:wait, 3:check}
        for status in self.STATUS.keys():
            if self.STATUS[status] == "Failed":
                continue
            tasks = self.run.execute(
                f"SELECT * FROM tasks_control WHERE status = {status}").fetchall()
            for task_db in tasks:
                dir, stage, _, taskID = task_db
                task = TaskClass[stage](dir, self.root)
                increase = True
                if status == 0:
                    task.prepare()
                elif status == 1:
                    res = task.run()
                    if "ERROR_SLURM" in res:
                        increase = False
                    else:
                        self.run.execute(
                            f"UPDATE tasks_control SET taskID = '{res}' WHERE directory = '{dir}'")
                        self.db.commit()
                elif status == 2:
                    res = task.wait(taskID)
                    if "Waiting" in res:
                        increase = False
                elif status == 3:
                    increase = False
                    res = task.check()
                    if "PASS":
                        self.run.execute(
                            f"UPDATE tasks_control SET stage = {stage}, status = 5, taskID = '' WHERE directory = '{dir}'")
                    else:
                        self.run.execute(
                            f"UPDATE tasks_control SET stage = {stage}, status = 4, taskID = '' WHERE directory = '{dir}'")
                    self.db.commit()
                if increase:
                    self.increase_task(dir, stage, status)

    def increase_task(self, directory, stage, status):
        if stage == 5 and self.STATUS[status] == "Done":
            return
        if self.STATUS[status] == "Failed":
            return
        if self.STATUS[status] == "Done":
            self.run.execute(
                f"UPDATE tasks_control SET stage = {stage}+1, status = 0, taskID = '' WHERE directory = '{directory}'")
        else:
            self.run.execute(
                f"UPDATE tasks_control SET stage = {stage}, status = {status}+1, taskID = '' WHERE directory = '{directory}'")
        self.db.commit()

    def dump(self, filename):
        tasks = self.run.execute(
            f"SELECT * FROM tasks_control").fetchall()
        out = " Directory ; Stage ; Status ; TaskIDs\n"
        if filename == None:
            out = "Current status:\n"
        for task in tasks:
            dir, stage, status, taskIDs = task
            out += f"{dir:>30} ; {self.STAGE[stage]:>20} ; {self.STATUS[status]:>15} ; {taskIDs:>10}\n"
        if filename == None:
            print(out)
        else:
            open(filename, "w").write(out)

    def __del__(self):
        self.db.commit()
        self.db.close()
        print("Destructing...")


if __name__ == "__main__":
    args = parse()
    control = FEPdb(args.db)
    if args.add != None:
        for task in zip(args.add, args.stage):
            control.add_task(task, args.force)
    if args.remove != None:
        for task in args.remove:
            control.remove_task(task, args.force)

    if args.run:
        control.run_tasks()

    if args.dump:
        control.dump(None)

    if args.dump_csv:
        control.dump(args.dump_csv)
