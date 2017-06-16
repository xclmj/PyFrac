# -*- coding: utf-8 -*-
"""
This file is part of PyFrac.

Created by Haseeb Zia on Fri Dec 23 17:49:21 2016.
Copyright (c) "ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE, Switzerland, Geo-Energy Laboratory", 2016-2017. All rights reserved.
See the LICENSE.TXT file for more details.
"""


# adding src folder to the path
import sys
if "win" in sys.platform:
    slash = "\\"
else:
    slash = "/"
if not '..' + slash + 'src' in sys.path:
    sys.path.append('.' + slash + 'src')
if not '.' + slash + 'src' in sys.path:
    sys.path.append('.' + slash + 'src')

# imports
import numpy as np
from src.CartesianMesh import *
from src.Fracture import *
from src.LevelSet import *
from src.VolIntegral import *
from src.Elasticity import *
from src.Properties import *
from src.FractureFrontLoop import *

# creating mesh
Mesh = CartesianMesh(.1,.1, 60,60)

# solid properties
nu = 0.4
Eprime = 3.3e9 / (1 - nu ** 2)
K_Ic = 0.01e6

sigma0 = np.full((Mesh.NumberOfElts,), 7e6, dtype=np.float64)
# high stressed layers
stressed_layer_1 = np.where(Mesh.CenterCoor[:,1] > 0.025 )[0]
stressed_layer_2 = np.where(Mesh.CenterCoor[:,1] < -(0.025 ))[0]

sigma0[stressed_layer_1] = 11.2e6
sigma0[stressed_layer_2] = 5e6

d_grain = 1e-5
Solid = MaterialProperties(Eprime, K_Ic, 0., sigma0, d_grain, Mesh)

# injection parameters
Q0 = 0.0023*1.e-6  # injection rate
well_location = np.array([0., 0.])   # todo: ensure initialization can be done for a fracture not at the center of the grid
Injection = InjectionProperties(Q0, well_location, Mesh)

# fluid properties
Fluid = FluidProperties(30, Mesh, turbulence=False)

# simulation properties
simulProp = SimulationParameters(tip_asymptote="U",
                                 output_time_period=10,
                                 plot_figure=True,
                                 save_to_disk=False,
                                 out_file_folder="..\\Data\\StressContrast", # e.g. "./Data/Laminar" for linux or mac
                                 plot_analytical=False,
                                 tmStp_prefactor=0.4,
                                 analytical_sol="M",plot_evolution=False)


# initializing fracture
initRad = 0.01 # initial radius of fracture

# creating fracture object
Fr = Fracture(Mesh,
              initRad,
              'radius',
              'M',
              Solid,
              Fluid,
              Injection,
              simulProp)


# elasticity matrix
C = load_elasticity_matrix(Mesh, Solid.Eprime)

# starting time stepping loop
i = 0
Fr_k = Fr

simulProp.FinalTime=600


while (Fr.time < simulProp.FinalTime) and (i < simulProp.maxTimeSteps):

    i = i + 1

    TimeStep = simulProp.tmStpPrefactor * min(Fr.mesh.hx, Fr.mesh.hy) / np.max(Fr.v)
    status, Fr_k = advance_time_step(Fr_k, C, Solid, Fluid, simulProp, Injection, TimeStep)

    Fr = copy.deepcopy(Fr_k)



#### post processing

