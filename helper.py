import os

from simtk.openmm import *
from simtk.openmm.app import *
from simtk.unit import *

from rdkit import Chem


def mkdir_if_missing(path):
    if not os.path.exists(path):
        os.makedirs(path)


def count_ligands(sdf_file):
    suppl = Chem.SDMolSupplier(sdf_file)
    ligand_count = 0
    for mol in suppl:
        if mol is None:
            continue
        ligand_count += 1
    return ligand_count


def split_ligands(sdf_file):
    ligand_pdb_file_list = []
    suppl = Chem.SDMolSupplier(sdf_file)
    for mol in suppl:
        if mol is None:
            continue
        for i, ligand in enumerate(mol.GetMolFrags()):
            # ligand_file = f"{mol.GetProp('_Name')}_ligand_{i+1}.pdb"
            ligand_file = os.path.join(
                data_path, '{}_ligand_{}.pdb'.format(mol.GetProp('_Name'), i+1))
            ligand_pdb_file_list.append(ligand_file)
            writer = Chem.PDBWriter(ligand_file)
            writer.write(ligand)
            writer.close()
    return ligand_pdb_file_list


def download_pdb_from_rcsb(pdb_id, data_path):
    input_protein_pdb_path = os.path.join(data_path, pdb_id+'.pdb')
    if os.path.isfile(input_protein_pdb_path) == False:
        os.system(
            'wget https://files.rcsb.org/download/{} -P {}'.format(pdb_id, data_path))
    return input_protein_pdb_path


def generate_pdb_4tleap(input_pdb, output_pdb):
    '''
    Source: https://github.com/choderalab/kinase-benchmark/issues/3
    '''
    infile = open(input_pdb, 'r')
    lines = infile.readlines()
    infile.close()

    outfile = open(output_pdb, 'w')
    for line in lines:
        if line[0:6] == 'ATOM  ':
            if line[13] != 'H':  # might have this column wrong
                outfile.write(line)
        else:
            outfile.write(line)
    outfile.close()


def generate_protein_tleapin(tleap_protein_in, protein_pdb, protein_prmtop, protein_inpcrd):
    f = open(tleap_protein_in, "w")
    f.write("""source leaprc.protein.ff14SB
    pdb = loadpdb {}
    saveamberparm pdb {} {}
    quit""".format(protein_pdb, protein_prmtop, protein_inpcrd))
    f.close()


def generate_complex_tleapin(input_pdb, prepi_file, frcmod_file,  tleap_in, topology_amber_prmtop, coordinate_amber_inpcrd):
    com_file = open(tleap_in, 'w')
    com_file.write('''
    source leaprc.protein.ff14SB #Source leaprc file for ff14SB protein force field
    source leaprc.gaff #Source leaprc file for gaff
    source leaprc.water.tip3p #Source leaprc file for TIP3P water model
    loadamberprep {} #Load the prepi file for the ligand
    loadamberparams {} #Load the additional frcmod file for ligand
    mol = loadpdb {} #Load PDB file for protein-ligand complex
    solvatebox mol TIP3PBOX 8 #Solvate the complex with a cubic water box
    addions mol Cl- 0 #Add Cl- ions to neutralize the system
    saveamberparm mol {} {} #Save AMBER topology and coordinate files
    quit #Quit tleap program
    '''.format(prepi_file, frcmod_file, input_pdb, topology_amber_prmtop, coordinate_amber_inpcrd))
    com_file.close()


def simulation_openMM(output_dir: str, complex_prmtop: str = 'complex.prmtop', complex_inpcrd: str = 'complex.inpcrd',
                      rigidWater: bool = True, ewaldErrorTolerance: float = 0.0005, constraintTolerance: float = 0.000001,
                      steps: int = 1000000, equilibrationSteps: int = 1000, platform_name: str = 'CPU',
                      dcdReporter_step: int = 10000, dataReporter_step: int = 1000, checkpointReporter_step: int = 10000):
    # This script was generated by OpenMM-Setup on 2021-12-15.
    # Input Files
    prmtop = AmberPrmtopFile(complex_prmtop)
    inpcrd = AmberInpcrdFile(complex_inpcrd)

    # System Configuration
    nonbondedMethod = PME
    nonbondedCutoff = 1.0*nanometers
    constraints = HBonds
    hydrogenMass = 1.5*amu

    # Integration Options
    dt = 0.004*picoseconds
    temperature = 300*kelvin
    friction = 1.0/picosecond
    pressure = 1.0*atmospheres
    barostatInterval = 25

    # Simulation Options
    platform = Platform.getPlatformByName(platform_name)
    trajectory_file = os.path.join(output_dir, 'trajectory.dcd')
    dcdReporter = DCDReporter(trajectory_file, dcdReporter_step)
    log_file = os.path.join(output_dir, 'log.txt')
    dataReporter = StateDataReporter(log_file, dataReporter_step, totalSteps=steps,
                                     step=True, speed=True, progress=True, potentialEnergy=True, temperature=True, separator='\t')
    checkpointReporter_file = os.path.join(output_dir, 'checkpoint.chk')
    checkpointReporter = CheckpointReporter(
        checkpointReporter_file, checkpointReporter_step)

    # Prepare the Simulation
    print('Building system...')
    topology = prmtop.topology
    positions = inpcrd.positions
    system = prmtop.createSystem(nonbondedMethod=nonbondedMethod, nonbondedCutoff=nonbondedCutoff,
                                 constraints=constraints, rigidWater=rigidWater, ewaldErrorTolerance=ewaldErrorTolerance, hydrogenMass=hydrogenMass)
    system.addForce(MonteCarloBarostat(
        pressure, temperature, barostatInterval))
    integrator = LangevinMiddleIntegrator(temperature, friction, dt)
    integrator.setConstraintTolerance(constraintTolerance)
    simulation = Simulation(topology, system, integrator, platform)
    simulation.context.setPositions(positions)
    if inpcrd.boxVectors is not None:
        simulation.context.setPeriodicBoxVectors(*inpcrd.boxVectors)

    # Minimize and Equilibrate
    print('Performing energy minimization...')
    simulation.minimizeEnergy()
    print('Equilibrating...')
    simulation.context.setVelocitiesToTemperature(temperature)
    simulation.step(equilibrationSteps)

    # Simulate
    print('Simulating...')
    simulation.reporters.append(dcdReporter)
    simulation.reporters.append(dataReporter)
    simulation.reporters.append(checkpointReporter)
    simulation.currentStep = 0
    simulation.step(steps)
    return trajectory_file, log_file, checkpointReporter_file


def create_mmpbsa_in(mmpbsa_infile: str, igb: int = 5, number_frames_analysis: int = 10, salt_concentration: float = 0.15, strip_mask:str =":WAT:Na+:Cl-:Mg+:K+"):
    if igb == 1:
        mbondi = 'mbondi'
    elif (igb == 2) or (igb == 5):
        mbondi = 'mbondi2'
    elif igb == 7:
        mbondi = 'bondi'
    elif igb == 8:
        mbondi = 'mbondi3'
    else:
        pass

    if number_frames_analysis > 10:
        stride = number_frames_analysis/10
    else:
        stride = 1

    f = open(mmpbsa_infile, "w")
    f.write("""&general """ + "\n"
            """  endframe=""" + str(int(number_frames_analysis)) + """,  interval=""" + str(
                int(stride)) + """, strip_mask="""+str(strip_mask) + """, """ + "\n"
            """/ """ + "\n"
            """&gb """ + "\n"
            """ igb=""" + str(igb) + """, saltcon=""" +
            str(salt_concentration) + """, """ + "\n"
            """/ """ + "\n"
            """&pb """ + "\n"
            """ istrng=""" + str(salt_concentration) +
            """, inp=2, radiopt=0, prbrad=1.4, """ + "\n"
            """/""")
    f.close()
    return mbondi