# Installation

Using with conda environment:
```
conda create -c conda-forge -c openbabel -c bioconda -c anaconda -n mmgbsa_env  python=3.7 openmm openmm-setup openbabel ambertools compilers pdbfixer gromacs babel rdkit
conda activate mmgbsa_env
```

# Usage
We can check the pipeline with sample data by using the command:
```
python MMGBSA.py --protein_pdb_file "protein.pdb" --ligand_pdb_file "ligand.pdb" --simulation_platform "CUDA" --AMBERHOME "~/"
```

# OpenMM_MMGBSA

# FAQ
https://github.com/openmm/openmm/issues/2880
https://github.com/openmm/openmm/issues/2842
https://github.com/pablo-arantes/making-it-rain/issues/79
https://github.com/quantaosun/Ambertools-OpenMM-MD/issues/1

# Reference codebase
[Google colab](https://colab.research.google.com/drive/1WDVIl5aHayk1_4BEbi27ZSBo7tDQcZ28?usp=share_link)
