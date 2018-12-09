"""
Extrapolation
=============

Shows the usage of the different types of extrapolation.
"""

# Author: Pablo Marcos Manchón
# License: MIT

# sphinx_gallery_thumbnail_number = 2

import fda
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d


###############################################################################
#
# The extrapolation defines how to evaluate points that are
# outside the domain range of a
# :class:`FDataBasis <fda.basis.FDataBasis>` or a
# :class:`FDataGrid <fda.grid.FDataGrid>`.
#
# Objects have a predefined extrapolation which is applied in :func:´evaluate´
# if the argument `extrapolation` is not specified. This default value
# could be specified when a :class:`FData` object is created or changing the
# attribute `extrapolation` of the object.
#
#
# To show how it works we will create a dataset with two unidimensional curves
# defined in (0,1), and we will represent using a grid and different types of
# basis.
#

fdgrid = fda.datasets.make_sinusoidal_process(n_samples=2, error_std=0, random_state=0)
fdgrid.dataset_label = "Grid"

fd_fourier = fdgrid.to_basis(fda.basis.Fourier())
fd_fourier.dataset_label = "Fourier Basis"

fd_monomial = fdgrid.to_basis(fda.basis.Monomial(nbasis=5))
fd_monomial.dataset_label = "Monomial Basis"

fd_bspline = fdgrid.to_basis(fda.basis.BSpline(nbasis=5))
fd_bspline.dataset_label = "BSpline Basis"


# Plot of diferent representations
fig, ax = plt.subplots(2,2)
fdgrid.plot(ax[0][0])
fd_fourier.plot(ax[0][1])
fd_monomial.plot(ax[1][0])
fd_bspline.plot(ax[1][1])

# Disable xticks of first row
ax[0][0].set_xticks([])
ax[0][1].set_xticks([])

###############################################################################
#
# If the extrapolation if not specified when a list of points if evaluated and
# and the default extrapolation of the objects has not been specified it is used
# the type `"none"`, which will evaluate the points outside the domain without
# any kind of control.
#
# For this reason the behavior outside the domain will change depending on the
# representation, obtaining a periodic behavior in the case of the Fourier
# basis and polynomial behaviors in the rest of the examples.
#

t = np.linspace(-0.2,1.2, 100)

fig, ax = plt.subplots(2,2)

# Plot extrapolated values
ax[0][0].plot(t, fdgrid(t).T, linestyle='--')
ax[0][1].plot(t, fd_fourier(t).T, linestyle='--')
ax[1][0].plot(t, fd_monomial(t).T, linestyle='--')
ax[1][1].plot(t, fd_bspline(t).T, linestyle='--')

# Plot configuration
for axes in fig.axes:
    axes.set_prop_cycle(None)
    axes.set_ylim((-1.5,1.5))
    axes.set_xlim((-0.25,1.25))

# Disable xticks of first row
ax[0][0].set_xticks([])
ax[0][1].set_xticks([])


# Plot objects in the domain range
fdgrid.plot(ax[0][0])
fd_fourier.plot(ax[0][1])
fd_monomial.plot(ax[1][0])
fd_bspline.plot(ax[1][1])


###############################################################################
#
# Periodic extrapolation will extend the domain range periodically.
# The following example shows the periodical extension of an FDataGrid.
#
# It should be noted that the Fourier basis is periodic in itself, but the
# period does not have to coincide with the domain range, obtaining different
# results applying or not extrapolation in case of not coinciding.
#

plt.figure()

# Evaluation of the grid
values = fdgrid(t, extrapolation="periodic")
plt.plot(t, values.T, linestyle='--')

plt.gca().set_prop_cycle(None) # Reset color cycle

fdgrid.plot() # Plot dataset

plt.title("Periodic extrapolation")


###############################################################################
#
# Another possible extrapolation, "bounds", will use the values of the interval
# bounds for points outside the domain range.
#

plt.figure()

# Evaluation of the grid
values = fdgrid(t, extrapolation="bounds")
plt.plot(t, values.T, linestyle='--')

plt.gca().set_prop_cycle(None) # Reset color cycle

fdgrid.plot() # Plot dataset

plt.title("Boundary extrapolation")

###############################################################################
#
# The :class:`FillExtrapolation` will fill the points extrapolated with the
# same value. The case of filling with zeros could be specified with the string
# zeros, which is equivalent to `extrapolation=FillExtrapolation(0)`.
#
# The string "nan" is equivalent to `FillExtrapolation(np.nan)`.
#

plt.figure()

# Evaluation of the grid filling with zeros
values = fdgrid(t, extrapolation="zeros")
plt.plot(t, values.T, linestyle='--')

plt.gca().set_prop_cycle(None) # Reset color cycle

fdgrid.plot() # Plot dataset

plt.title("Fill extrapolation")

###############################################################################
#
# It is possible to configure the extrapolation to raise an exception in case
# of evaluating a point outside the domain.
#

try:
    res = fd_fourier(t, extrapolation="exception")

except ValueError as e:
    print(e)

###############################################################################
#
# All the extrapolators will work for multidimensional objects.
# In the following example it is shown a periodic extension of a 2d-surface

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Make data.
t = np.arange(-2.5, 2.5, 0.25)
X, Y = np.meshgrid(t, t)
RSQ = X**2 + Y**2
Z = 0.1 * np.sqrt(np.exp(-RSQ))

# Creation of FDataGrid
fd_surface = fda.FDataGrid([Z], (t, t))

t = np.arange(-7, 7, 0.4)

# Evaluation with periodic extrapolation
values =  fd_surface((t,t), grid=True, extrapolation="periodic")
T, S = np.meshgrid(t, t)


ax.plot_wireframe(T, S, values[0], alpha=.3, color="C0")
ax.plot_surface(X, Y, Z, color="C0")

plt.show()
