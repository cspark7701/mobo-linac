import numpy as np
import scipy.constants as spc

def get_gamma(kinetic_energy):
    m_e = spc.electron_mass * spc.c * spc.c / spc.electron_volt
    gamma = 1 + kinetic_energy / m_e
    return (gamma)

def get_beta(gamma):
    beta = np.sqrt(gamma * gamma - 1) / gamma
    return (beta)

def get_normalized_emittance(unnorm_emittance, kinetic_energy):
    gamma = get_gamma(kinetic_energy)
    beta = get_beta(gamma)
    norm_emittance = beta * gamma * unnorm_emittance
    return (norm_emittance)
