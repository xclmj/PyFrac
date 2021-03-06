# -*- coding: utf-8 -*-
"""
This file is part of PyFrac.

Created by Haseeb Zia on Tue Dec 27 17:41:56 2016.
Copyright (c) "ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE, Switzerland, Geo-Energy Laboratory", 2016-2019.
All rights reserved. See the LICENSE.TXT file for more details.
"""

import numpy as np
import json
import subprocess
import pickle
from array import array
import os, sys

def load_isotropic_elasticity_matrix(Mesh, Ep):
    """
    Evaluate the elasticity matrix for the whole mesh.
    Arguments:
        Mesh (object CartesianMesh):    -- a mesh object describing the domain.
        Ep (float):                     -- plain strain modulus.
    Returns:
        ndarray-float:                  -- the elasticity martix.
    """

    a = Mesh.hx / 2.
    b = Mesh.hy / 2.
    Ne = Mesh.NumberOfElts

    C = np.empty([Ne, Ne], dtype=np.float32)

    for i in range(0, Ne):
        x = Mesh.CenterCoor[i, 0] - Mesh.CenterCoor[:, 0]
        y = Mesh.CenterCoor[i, 1] - Mesh.CenterCoor[:, 1]

        C[i] = (Ep / (8. * np.pi)) * (
                np.sqrt(np.square(a - x) + np.square(b - y)) / ((a - x) * (b - y)) + np.sqrt(
            np.square(a + x) + np.square(b - y)
        ) / ((a + x) * (b - y)) + np.sqrt(np.square(a - x) + np.square(b + y)) / ((a - x) * (b + y)) + np.sqrt(
            np.square(a + x) + np.square(b + y)) / ((a + x) * (b + y)))

    return C


# -----------------------------------------------------------------------------------------------------------------------
def get_Cij_Matrix(youngs_mod, nu):

    k = youngs_mod / (3 * (1 - 2 * nu))
    la = (3 * k * (3 * k - youngs_mod)) / (9 * k - youngs_mod)
    mu = 3 / 2 * (k - la)

    Cij = np.zeros((6, 6), dtype=np.float64)
    Cij[0][0] = (la + 2 * mu) * (1 + 0.00007)
    Cij[0][2] = la * (1 + 0.00005)
    Cij[2][2] = (la + 2 * mu) * (1 + 0.00009)
    Cij[3][3] = mu * (1 + 0.00001)
    Cij[5][5] = mu * (1 + 0.00003)
    Cij[0][1] = Cij[0][0] - 2 * Cij[5][5]

    return Cij


# --------------------------------------------------------------------------------------------------------------------------
def load_TI_elasticity_matrix(Mesh, mat_prop, sim_prop):
    """
    Create the elasticity matrix for transversely isotropic materials.  It is under development and will be refactored
    soon.

    Args:
        Mesh (object CartesianMesh):        -- a mesh object describing the domain.
        mat_prop (MaterialProperties):      -- the MaterialProperties object giving the material properties.
        sim_prop (SimulationProperties):    -- the SimulationProperties object giving the numerical parameters to be
                                               used in the simulation.

    Returns:
        C (ndarray):                        -- the elasticity matrix.
    """

    data = {'Solid parameters': {'C11': mat_prop.Cij[0][0],
                                 'C12': mat_prop.Cij[0][1],
                                 'C13': mat_prop.Cij[0][2],
                                 'C33': mat_prop.Cij[2][2],
                                 'C44': mat_prop.Cij[3][3]},
            'Mesh':             {'L1': Mesh.Lx,
                                 'L3': Mesh.Ly,
                                 'n1': Mesh.nx,
                                 'n3': Mesh.ny}
            }

    print('Writing parameters to a file...')
    curr_directory = os.getcwd()
    os.chdir(sim_prop.TI_KernelExecPath)
    with open('stiffness_matrix.json', 'w') as outfile:
        json.dump(data, outfile, indent=3)

    if "win32" in sys.platform or "win64" in sys.platform:
        suffix = ""
    else:
        suffix = "./"

    # Read the elasticity matrix from the npy file
    print('running C++ process...')
    subprocess.run(suffix + 'TI_elasticity_kernel', shell=True)

    print('Reading global TI elasticity matrix...')
    try:
        file = open('StrainResult.bin', "rb")
        C = array('d')
        C.fromfile(file, pow(data['Mesh']['n1'] * data['Mesh']['n3'], 2))
        C = np.reshape(C,
                       (data['Mesh']['n1'] * data['Mesh']['n3'],
                        data['Mesh']['n1'] * data['Mesh']['n3']))

    except FileNotFoundError:
        # if 'CMatrix' file is not found
        raise SystemExit('file not found')

    os.chdir(curr_directory)

    return C


# ----------------------------------------------------------------------------------------------------------------------


def load_elasticity_matrix(Mesh, EPrime):
    """
    The function loads the elasticity matrix from the saved file. If the loaded matrix is not compatible with respect
    to the current mesh or plain strain modulus, the compatible matrix is computed and saved in a file. If the file is
    not found, the elasticity matrix is computed and saved in a file with the name 'CMatrix'.
    
    Arguments:
        Mesh (CartesianMesh):           -- a mesh object describing the domain.
        EPrime (float):                 -- plain strain modulus.
    
    Returns:
         C (ndarray):                   -- the elasticity matrix.
    """
    print('Reading global elasticity matrix...')
    try:
        with open('CMatrix', 'rb') as input_file:
            (C, MeshLoaded, EPrimeLoaded) = pickle.load(input_file)
        # check if the loaded matrix is correct with respect to the current mesh and plain strain modulus
        if (Mesh.nx, Mesh.ny, Mesh.Lx, Mesh.Ly, EPrime) == (MeshLoaded.nx, MeshLoaded.ny, MeshLoaded.Lx,
                                                            MeshLoaded.Ly, EPrimeLoaded):
            return C
        else:
            print(
                'The loaded matrix is not correct with respect to the current mesh or the current plain strain modulus.'
                '\nMaking global matrix...')
            C = load_isotropic_elasticity_matrix(Mesh, EPrime)
            Elast = (C, Mesh, EPrime)
            with open('CMatrix', 'wb') as output:
                pickle.dump(Elast, output, -1)
            print("Done!")
            return C
    except FileNotFoundError:
        # if 'CMatrix' file is not found
        print('file not found\nBuilding the global elasticity matrix...')
        C = load_isotropic_elasticity_matrix(Mesh, EPrime)
        Elast = (C, Mesh, EPrime)
        with open('CMatrix', 'wb') as output:
            pickle.dump(Elast, output, -1)
        print("Done!")
        return C


