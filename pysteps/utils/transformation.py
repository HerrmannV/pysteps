"""Methods for transforming data values."""

import numpy as np
import scipy.stats as scipy_stats
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning) # To deactivate warnings for comparison operators with NaNs

def dB_transform(R, metadata=None, threshold=None, zerovalue=None, inverse=False):
    """Methods to transform to/from dB units.

    Parameters
    ----------
    R : array-like
        Array of any shape to be (back-)transformed.
    metadata : dict
        The metadata dictionary contains all data-related information.
    threshold : float
        Optional value that is used for thresholding with the same units as R.
        If None, the threshold contained in metadata is used.
    zerovalue : float
        Optional value to be assigned to no rain pixels as defined by the threshold.
    inverse : bool
        Optional, if set to True, it performs the inverse transform

    Returns
    -------
    R : array-like
        Array of any shape containing the (back-)transformed units.
    metadata : dict
        The metadata with updated attributes.

    """

    R = R.copy()

    if metadata is None:
        if inverse:
            metadata = {"transform": "dB"}
        else:
            metadata = {"transform": None}
    else:
        metadata = metadata.copy()

    # to dB units
    if not inverse:

        if metadata["transform"] is "dB":
            return R, metadata

        if threshold is None:
            threshold = metadata.get("threshold", 0.1)

        zeros = R < threshold

        # Convert to dB
        R[~zeros] = 10.0*np.log10(R[~zeros])
        threshold = 10.0*np.log10(threshold)

        # Set value for zeros
        if zerovalue is None:
            zerovalue = threshold - 1 # TODO: set to a more meaningful value
        R[zeros] = zerovalue

        metadata["transform"] = "dB"
        metadata["zerovalue"] = zerovalue
        metadata["threshold"] = threshold

        return R, metadata

    # from dB units
    elif inverse:

        if metadata["transform"] is not "dB":
            return R, metadata

        if threshold is None:
            threshold = metadata.get("threshold", -10.)
        if zerovalue is None:
            zerovalue = 0.0
            
        R = 10.0**(R/10.0)
        threshold = 10.0**(threshold/10.0)
        R[R < threshold] = zerovalue
        
        metadata["transform"] = None
        metadata["threshold"] = threshold
        metadata["zerovalue"] = zerovalue

        return R, metadata

def boxcox_transform(R, metadata=None, Lambda=None, threshold=None,
                     zerovalue=None, inverse=False):
    """The one-parameter Box-Cox transformation.

    Parameters
    ----------
    R : array-like
        Array of any shape to be transformed.
    metadata : dict
        The metadata dictionary contains all data-related information.
    Lambda : float
        Parameter lambda of the Box-Cox transformation.
    threshold : float
        Optional value that is used for thresholding with the same units as R.
        If None, the threshold contained in metadata is used.
    zerovalue : float
        Optional value to be assigned to no rain pixels as defined by the threshold.
    inverse : bool
        Optional, if set to True, it performs the inverse transform

    Returns
    -------
    R : array-like
        Array of any shape containing the (back-)transformed units.
    metadata : dict
        The metadata with updated attributes.

    """

    R = R.copy()
    if metadata is None:
        if inverse:
            metadata = {"transform": "BoxCox"}
        else:
            metadata = {"transform": None}
    else:
        metadata = metadata.copy()

    if not inverse:

        if metadata["transform"] is "BoxCox":
            return R, metadata

        if Lambda is None:
            Lambda = metadata.get("BoxCox_lambda", 0)

        if threshold is None:
            threshold = metadata.get("threshold", 0.1)

        zeros = R < threshold

        # Apply Box-Cox transform
        if Lambda==0:
            R[~zeros] = np.log(R[~zeros])
            threshold = np.log(threshold)

        else:
            R[~zeros] = (R[~zeros]**Lambda - 1)/Lambda
            threshold = (threshold**Lambda - 1)/Lambda

        # Set value for zeros
        if zerovalue is None:
            zerovalue = threshold - 1 # TODO: set to a more meaningful value
        R[zeros] = zerovalue

        metadata["transform"] = "BoxCox"
        metadata["BoxCox_lambda"] = Lambda
        metadata["zerovalue"] = zerovalue
        metadata["threshold"] = threshold

    elif inverse:

        if metadata["transform"] is not "BoxCox":
            return R, metadata

        if Lambda is None:
            Lambda = metadata.pop('BoxCox_lambda')
        if threshold is None:
            threshold = metadata.get("threshold", -10.)
        if zerovalue is None:
            zerovalue = 0.0

        # Apply inverse Box-Cox transform
        if Lambda==0:
            R = np.exp(R)
            threshold = np.exp(threshold)

        else:
            R = np.exp(np.log(Lambda*R + 1)/Lambda)
            threshold = np.exp(np.log(Lambda*threshold + 1)/Lambda)

        R[R < threshold] = zerovalue

        metadata["transform"] = None
        metadata["zerovalue"] = zerovalue
        metadata["threshold"] = threshold

    return R, metadata

def boxcox_transform_test_lambdas(R, Lambdas=None, threshold=0.1):
    """Test and plot various lambdas for the Box-Cox transformation."""

    import matplotlib.pyplot as plt

    R = R[R>threshold].flatten()

    if Lambdas is None:
        Lambdas = np.linspace(-1,1,11)

    data = []
    labels=[]
    sk=[]
    for i, Lambda in enumerate(Lambdas):
        R_, _ = boxcox_transform(R, {"transform":None}, Lambda, threshold)
        R_ = (R_ - np.mean(R_))/np.std(R_)
        data.append(R_)
        labels.append('{0:.1f}'.format(Lambda))
        sk.append(scipy_stats.skew(R_)) # skewness

    fig = plt.figure()

    bp = plt.boxplot(data, labels=labels)

    ylims = np.percentile(data,0.99)
    plt.title('Box-Cox transform')
    plt.xlabel(r'Lambda, $\lambda$ []')

    ymax = np.zeros(len(data))
    for i in range(len(data)):
        y = sk[i]
        x = i+1
        plt.plot(x, y, 'ok', ms=5, markeredgecolor='k') # plot skewness
        fliers = bp['fliers'][i].get_ydata()
        if len(fliers>0):
            ymax[i] = np.max(fliers)
    ylims = np.percentile(ymax,60)
    plt.ylim((-1*ylims,ylims))
    plt.ylabel(r'Standardized values [$\sigma]$')

    plt.savefig("box-cox-transform-test-lambdas.png", bbox_inches="tight")
    print("Saved: box-cox-transform-test-lambdas.png")

    plt.close()
