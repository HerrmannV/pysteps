"""Evaluation and skill scores for ensemble forecasts."""

import numpy as np
from .interface import get_method

def ensemble_skill(X_f, X_o, metric, **kwargs):
    """Compute mean ensemble skill for a given skill metric.

    Parameters
    ----------
    X_f : array-like
        Array of shape (l,m,n) containing the forecast fields of shape (m,n)
        from l ensemble members.
    X_o : array_like
        Array of shape (m,n) containing the observed field corresponding to
        the forecast.
    metric : str
        The deterministic skill metric to be used (list available in
        :func:`~pysteps.verification.interface.get_method`)

    Other Parameters
    ----------------
    thr : float
        Intensity threshold for categorical scores.
    scale : int
        The spatial scale to verify in px. In practice it represents the size of
        the moving window that it is used to compute the fraction of pixels above
        the threshold for the FSS.

    Returns
    -------
    out : float
        The mean skill of all ensemble members that is used as defintion of
        ensemble skill (as in Zacharov and Rezcova 2009 with the FSS).

    References
    ----------
    :cite:`ZR2009`

    """

    if len(X_f.shape) != 3:
        raise ValueError("the number of dimensions of X_f must be equal to 3, but %i dimensions were passed"
                         % len(X_f.shape))
    if X_f.shape[1:] != X_o.shape:
        raise ValueError("the shape of X_f does not match the shape of X_o (%d,%d)!=(%d,%d)"
                         % (X_f.shape[1], X_f.shape[2], X_o.shape[0], X_o.shape[1]))

    thr = kwargs.get("thr", None)
    scale = kwargs.get("scale", None)

    compute_skill = get_method(metric, type="deterministic")

    l = X_f.shape[0]
    skill = []
    for member in range(l):
        skill_ = compute_skill(X_f[member, :, :], X_o, thr=thr, scale=scale)
        skill.append(skill_)

    return np.mean(skill)

def ensemble_spread(X_f, metric, **kwargs):
    """Compute mean ensemble spread for a given skill metric.

    Parameters
    ----------
    X_f : array-like
        Array of shape (l,m,n) containing the forecast fields of shape (m,n)
        from l ensemble members.
    metric : str
        The skill metric to be used, the list includes:

    Other Parameters
    ----------------
    thr : float
        Intensity threshold for categorical scores.
    scale : int
        The spatial scale to verify in px. In practice it represents the size of
        the moving window that it is used to compute the fraction of pixels above
        the threshold for the FSS.

    Returns
    -------
    out : float
        The mean skill compted between all possible pairs of the ensemble members,
        which can be used as definition of mean ensemble spread (as in Zacharov
        and Rezcova 2009 with the FSS).

    References
    ----------
    :cite:`ZR2009`

    """
    if len(X_f.shape) != 3:
        raise ValueError("the number of dimensions of X_f must be equal to 3, but %i dimensions were passed"
                         % len(X_f.shape))
    if X_f.shape[0] < 2:
        raise ValueError("the number of members in X_f must be greater than 1, but %i members were passed"
                         % X_f.shape[0])

    thr = kwargs.get("thr", None)
    scale = kwargs.get("scale", None)

    compute_skill = get_method(metric, type="deterministic")

    l = X_f.shape[0]
    skill = []
    for member in range(l):
        for othermember in range(member + 1, l):
            skill_ = compute_skill(X_f[member, :, :], X_f[othermember, :, :], thr=thr, scale=scale)
            skill.append(skill_)

    return np.mean(skill)

def rankhist_init(num_ens_members, X_min):
    """Initialize a rank histogram object.

    Parameters
    ----------
    num_ens_members : int
        Number ensemble members in the forecasts to accumulate into the rank
        histogram.
    X_min : float
        Threshold for minimum intensity. Forecast-observation pairs, where all
        ensemble members and verifying observations are below X_min, are not
        counted in the rank histogram.

    Returns
    -------
    out : dict
        The rank histogram object.

    """
    rankhist = {}

    rankhist["num_ens_members"] = num_ens_members
    rankhist["n"] = np.zeros(num_ens_members+1, dtype=int)
    rankhist["X_min"] = X_min

    return rankhist

def rankhist_accum(rankhist, X_f, X_o):
    """Accumulate forecast-observation pairs to the given rank histogram.

    Parameters
    ----------
    X_f : array-like
        Array of shape (n,m) containing the values from n ensemble forecasts
        with m members.
    X_o : array_like
        Array of length n containing the observed values corresponding to the
        forecast.

    """
    if X_f.shape[1] != rankhist["num_ens_members"]:
        raise ValueError("the number of ensemble members in X_f does not match the number of members in the rank histogram (%d!=%d)" % (X_f.shape[1], rankhist["num_ens_members"]))

    X_min = rankhist["X_min"]

    mask = np.logical_and(np.isfinite(X_o), np.all(np.isfinite(X_f), axis=1))
    X_f = X_f[mask, :].copy()
    X_o = X_o[mask]

    mask_nz = np.logical_or(X_o >= X_min, np.all(X_f >= X_min, axis=1))

    X_f.sort(axis=1)
    bin_idx = [np.digitize([v], f)[0] for v,f in zip(X_o[mask_nz], X_f[mask_nz, :])]

    # handle ties, where the verifying observation lies between ensemble
    # members having the same value
    # ignore the cases where the verifying observations and all ensemble
    # members are below the threshold X_min
    for i in np.where(~mask_nz)[0]:
        if np.any(X_f[i, :] >= X_min):
            i_eq = np.where(X_f[i, :] < X_min)[0]
            if len(i_eq) > 1 and X_o[i] < X_min:
                bin_idx.append(np.random.randint(low=np.min(i_eq),
                                                 high=np.max(i_eq)+1))

    for bi in bin_idx:
        rankhist["n"][bi] += 1

def rankhist_compute(rankhist, normalize=True):
    """Return the rank histogram counts and optionally normalize the histogram.

    Parameters
    ----------
    rankhist : dict
        A rank histogram object created with rankhist_init.
    normalize : bool
        If True, normalize the rank histogram so that the bin counts sum to one.

    Returns
    -------
    out : array_like
        The counts for the n+1 bins in the rank histogram, where n is the number
        of ensemble members.

    """
    if normalize:
        return 1.0*rankhist["n"] / sum(rankhist["n"])
    else:
        return rankhist["n"]
