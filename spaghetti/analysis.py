import numpy


class FuncBase(object):
    """Base object for performing network analysis on a
    ``spaghetti.Network`` object.
    
    Parameters
    ----------
    
    ntw : spaghetti.Network
        A spaghetti network object.
    
    pointpattern : spaghetti.network.PointPattern
        A spaghetti point pattern object.
    
    nsteps : int
        The number of steps at which the count of the nearest
        neighbors is computed. Default is 10.
        
    permutations : int
        The number of permutations to perform. Default is 99.
    
    threshold : float
        The level at which significance is computed.
        (0.5 would be 97.5% and 2.5%). Default is 0.5.
    
    distribution : str
        The distribution from which random points are sampled.
        Currently, the only supported distribution is uniform.
    
    upperbound : float
        The upper bound at which the `K`-function is computed.
        Defaults to the maximum observed nearest neighbor distance.
    
    Attributes
    ----------
    
    sim : numpy.ndarray
        A simulated distance matrix.
    
    npts : int
        The number of points (``pointpattern.npoints``).
    
    xaxis : numpy.ndarray
        The observed x-axis of values.
    
    observed : numpy.ndarray
        The observed y-axis of values.
    
    """

    def __init__(
        self,
        ntw,
        pointpattern,
        nsteps=10,
        permutations=99,
        threshold=0.5,
        distribution="uniform",
        upperbound=None,
    ):

        # set initial class attributes
        self.ntw = ntw
        self.pointpattern = pointpattern
        self.nsteps = nsteps
        self.permutations = permutations
        self.threshold = threshold

        # set and validate the distribution
        self.distribution = distribution.lower()
        self.validatedistribution()

        # create an empty array to store the simulated points
        self.sim = numpy.empty((permutations, nsteps))
        self.pts = self.pointpattern
        self.npts = self.pts.npoints

        # set the upper bounds
        self.upperbound = upperbound

        # compute the statistic K
        self.computeobserved()
        self.computepermutations()

        # compute the envelope vectors
        self.computeenvelope()

    def validatedistribution(self):
        """enusure statistical distribution is supported
        """

        valid_distributions = ["uniform"]
        if not self.distribution in valid_distributions:
            msg = "%s distribution not currently supported." % self.distribution
            raise RuntimeError(msg)

    def computeenvelope(self):
        """compute upper and lower bounds of envelope
        """

        upper = 1.0 - self.threshold / 2.0
        lower = self.threshold / 2.0

        self.upperenvelope = numpy.nanmax(self.sim, axis=0) * upper
        self.lowerenvelope = numpy.nanmin(self.sim, axis=0) * lower

    def setbounds(self, distances):
        """set upper bound
        """
        if self.upperbound is None:
            self.upperbound = numpy.nanmax(distances)


class GlobalAutoK(FuncBase):
    """See full description in ``network.Network.GlobalAutoK()``.
    
    Attributes
    ----------
    
    lam : float
        The ``lambda`` value.
    
    """

    def computeobserved(self):
        """Compute the observed nearest.
        """

        # pairwise distances
        distances = self.ntw.allneighbordistances(self.pointpattern, fill_diagonal=0.0)

        self.setbounds(distances)

        # set the intensity (lambda)
        self.lam = self.npts / sum(self.ntw.arc_lengths.values())

        # compute a Global Auto K-Function
        observedx, observedy = global_auto_k(
            self.npts, distances, self.upperbound, self.lam, nsteps=self.nsteps
        )

        # set observed values
        self.observed = observedy
        self.xaxis = observedx

    def computepermutations(self):
        """Compute permutations (Monte Carlo simulation) of the points.
        """

        # for each round of permutations
        for p in range(self.permutations):

            # simulate a point pattern
            sim = self.ntw.simulate_observations(
                self.npts, distribution=self.distribution
            )

            # distances
            distances = self.ntw.allneighbordistances(sim, fill_diagonal=0.0)

            # compute a Global Auto K-Function
            simx, simy = global_auto_k(
                self.npts, distances, self.upperbound, self.lam, nsteps=self.nsteps
            )

            # label the permutation
            self.sim[p] = simy


def global_auto_k(n_obs, dists, upperbound, intensity, nsteps=10):
    """Compute a `K`-function.

    Parameters
    ----------
    
    n_obs : int
        The number of observations. See ``self.npts``.
    
    dists : numpy.ndarray
        A matrix of pairwise distances.
    
    upperbound : int or float
        The end value of the sequence.
    
    intensity : float
        lambda value
    
    nsteps : int
        The number of distance bands. Default is 10. Must be
        non-negative.
    
    Returns
    -------
    
    x : numpy.ndarray
        The x-axis of values.
    
    y : numpy.ndarray
        The y-axis of values.
    
    """

    # create interval for x-axis
    x = numpy.linspace(0, upperbound, nsteps)

    # create empty y-axis vector and iterate over x-axis interval
    # -- here we should also not consider self-neighbors (the diagonal)
    y = numpy.array([dists[dists <= r].shape[0] - n_obs for r in x]).astype(float)

    # compute k for y-axis vector
    y /= n_obs * intensity

    return x, y
