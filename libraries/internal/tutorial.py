import numpy as np
import pandas as pd

from sciplex import nodify


@nodify(
        icon="tutorial"
)
def DragMeIn():
    """
    Node for the first tutorial. Execute to start!
    """
    return



@nodify(
        icon="dataset"
)
def UnivariateDataset() -> pd.DataFrame:
    """
    This is a dataset of a single variable with Gaussian distribution. Great for histograms.

    Returns:
        table: The data set.
    """
    np.random.seed(42)
    data = {
    "value": np.random.normal(2.4, 0.8, 150)
    }

    return pd.DataFrame(data)


@nodify(
        icon="dataset"
)
def CategoricalDataset() -> pd.DataFrame:
    """
    This is a simple dataaset with numeric and categorical columns. Good to test groupby, boxplots, etc.#

    Returns:
        table: The data set.
    """
    data = {
    "Month": ["Jan", "Jan", "Jan", "Feb", "Feb", "Feb", "Mar", "Mar", "Mar"],
    "Category": ["Apples", "Bananas", "Cherries"] * 3,
    "Sales": [23, 17, 35, 30, 20, 40, 25, 15, 38],
    "Profit": [5, 3, 8, 6, 4, 10, 7, 2, 9]
    }

    return pd.DataFrame(data)


@nodify(
        icon="dataset"
)
def ClassificationDataset() -> pd.DataFrame:
    """
    This is a synthetic dataset for classification tasks. Try to predict the "Fail" column based on the other ones. For this, you need classification methods in the Machine Learning section. Also, don't forget to first encode the material column.

    Returns:
        table: The data set.
    """

    np.random.seed(42)
    n = 1000

    # Quantitative features
    length = np.random.uniform(50, 200, size=n)  # in cm
    diameter = np.random.uniform(5, 20, size=n)  # in mm

    # Categorical feature
    material = np.random.choice(['Steel', 'Aluminum', 'Titanium'], size=n)

    # Simple failure probability model (not physical exact, but meaningful)
    fail_prob = []
    for length_cm, diameter_mm, mat in zip(length, diameter, material):
        base_prob = 0.2
        if mat == "Aluminum":
            base_prob += 0.2
        elif mat == "Titanium":
            base_prob -= 0.1
        # Longer and thinner rods are more likely to fail
        base_prob += 0.003 * (length_cm - 50)  # longer rods -> more likely
        base_prob += 0.05 * (10 - diameter_mm)  # thinner rods -> more likely
        # Clip probabilities between 0 and 1
        base_prob = max(0, min(1, base_prob))
        fail_prob.append(base_prob)

    # Target variable
    fail = [1 if np.random.rand() < p else 0 for p in fail_prob]

    # Create DataFrame
    df = pd.DataFrame({
        'Length_cm': length,
        'Diameter_mm': diameter,
        'Material': material,
        'Fail': fail
    })
    return df



@nodify(
        icon="dataset"
)
def RegressionDataset() -> pd.DataFrame:
    """
    Data Set for a simple regression task x=f(x). Check it out with a scatter plot and try to make a model with a regressor from the Machine Learning section.

    Returns:
        table: The data set.
    """

    np.random.seed(42)
    x = np.random.uniform(0, 20, 100)
    y = 2 *x + 5*np.sin(2*np.pi*x/5) + 2*np.random.normal(0.2, 0.5, 100)
    return pd.DataFrame({'x': x, 'y': y})


@nodify(
        icon="dataset"
)
def IrisDataset() -> pd.DataFrame:
    """
    Load the famous Iris dataset with sklearn. Check out these links for more info:
    - https://en.wikipedia.org/wiki/Iris_flower_data_set
    - https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_iris.html

    Returns:
        table: The data set.
    """

    from sklearn.datasets import load_iris

    iris = load_iris(as_frame=True)
    df = iris.frame
    return df


@nodify(
        icon="dataset"
)
def CaliforniaHousingDataset() -> pd.DataFrame:
    """
    Load the famous Calofornia Housing dataset with sklearn. Check out these links for more info:
    - https://scikit-learn.org/stable/modules/generated/sklearn.datasets.fetch_california_housing.html

    Returns:
        table: The data set.
    """

    from sklearn.datasets import fetch_california_housing

    iris = fetch_california_housing(as_frame=True)
    df = iris.frame
    return df


