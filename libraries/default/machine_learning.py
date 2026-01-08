"""
This file is part of the Sciplex default library and serves as a reference for creating new nodes.

When you delete default libraries from the workspace, they are automatically restored on the next startup.

Library files that expose functions and are imported into the sidebar become available in the flow. Files whose names start with an underscore (e.g., `_helpers.py`) are skipped.

The following helpers are provided by `sciplex` (you can import them directly and the backend wires this up for you):
- `@nodify`: decorate a function to define a node (see the examples below).
- `Attribute`: describe the widgets that appear in the properties panel.
- `workspace`: a global dictionary for sharing values between nodes (`workspace['foo'] = 2`).

Every Sciplex node is just a Python function. Attributes control widget types in the properties panel, and parameters without defaults map to input sockets while those with defaults become editable parameters.

Type hints are optional. Use extractors when you need to probe incoming data (e.g., pull column names from a dataframe).

Common attribute widgets:
- `lineedit`: text input
- `pylineedit`: Python-style input (lists, expressions, access to globals)
- `spinbox`: integer input
- `doublespinbox`: float input
- `combobox`: dropdown
- `checkable-combobox`: dropdown with multiple selections
- `filepath`: file chooser input
- `filesave`: file chooser output
- `colorpicker`: color picker widget

About figures:
- You can return Matplotlib or Plotly figures from node functions (see `visuals.py` for examples).
"""


import numbers

import numpy as np
import pandas as pd
from _helpers import MLModel, MLTransform, assign_name
from sklearn.model_selection import train_test_split

from sciplex import Attribute, nodify


@nodify(
        icon="score",
        y_true=Attribute("combobox", source="data", extractor="dataframe_columns"),
        y_pred=Attribute("combobox", source="data", extractor="dataframe_columns"),
        op=Attribute("combobox", value = "Acc", options=["Acc", "Prec", "Rec", "F1"])
)
def ClassificationMetric(data: pd.DataFrame, y_true: str=None, y_pred: str=None, op: str="Acc") -> numbers.Number:
    """
    Computes popular classification metrics.

    Args:
        data (table): Input data.
        y_true (str): Name of the column with the true labels.
        y_predict (str): Name of the column with the predicted labels.
        op (str): One of "Acc" (Accuracy), "Prec" (Precision), "Rec" (Recall), "F1" (F1 score)

    Returns:
        number: The metric score.
    """
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    y_true = data[y_true]
    y_pred = data[y_pred]

    metric_map = {
        "Acc": accuracy_score,
        "Prec": precision_score,
        "Rec": recall_score,
        "F1": f1_score
    }
    return metric_map[op](y_true, y_pred)


@nodify(
        icon="table",
        y_true=Attribute("combobox", source="data", extractor="dataframe_columns"),
        y_pred=Attribute("combobox", source="data", extractor="dataframe_columns"),
        normalize=Attribute("combobox", options=["None", "true", "pred", "all"]),
)
def ConfusionMatrix(data: pd.DataFrame, y_true: str, y_pred: str, normalize: str="None") -> pd.DataFrame:
    """
    Compute the Confusion Matrix of a classification. View the matrix on the output socket (double-click).

    Args:
        data (table): The input data.
        y_true (str): Name of column with true labels.
        y_pred (str): Name of column with predicted labels.
        normalize (str): Confusion matrix can be normalized by rows (true), columns (pred) or all entries.

    Returns:
        table: the confusion matrix, where the entry (row,column)=(i,j) corresponds to true label i and predicted label j.
    """
    from sklearn.metrics import confusion_matrix
    if normalize=="None":
        res = confusion_matrix(data[y_true], data[y_pred])
    else:
        res = confusion_matrix(data[y_true], data[y_pred], normalize=normalize)
    return res


@nodify(
        icon="decisiontree",
        features=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        targets=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        criterion=Attribute("combobox", options=["gini", "entropy", "log_loss"]),
        max_depth=Attribute("spinbox", value=10, range=[1, 1000]),
        min_samples_split=Attribute("spinbox", value=2, range=[1, 1000]),
        min_samples_leaf=Attribute("spinbox", value=1, range=[1, 1000]),
        random_state=Attribute("spinbox", value=42, range=[-int(1e9), int(1e9)]),
)
def DecisionTreeClassifier(
    train_data: pd.DataFrame,
    features: list=[],
    targets: list=[],
    criterion: str="gini",
    max_depth: int=10,
    min_samples_split: int=2,
    min_samples_leaf: int=1,
    random_state: int=42
    ) -> MLModel:
    """
    Preforms a Decision Tree Classification. Input data needs to have >1 column.

    Args:
        train_data (table): Input data for training.
        features (list): Features / inputs for the model.
        targets (list): Targets to predict with the model. Values are expected to be discrete numerical values.
        max_depth (int): Maximum depth of the tree.
        min_samples_split (int): Minimum number of samples required to split a node.
        min_samples_leaf (int): Minimum number of samples per branch after a split.
        random_state (int): Random state for the algorithm.

    Returns:
        model: The fitted model as an input for a predict node.
    """
    from sklearn.tree import DecisionTreeClassifier
    X = train_data[features]
    y = train_data[targets]
    clf = DecisionTreeClassifier(
        criterion=criterion,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state,
    )
    clf.fit(X, y)
    return MLModel("DecTrClf", clf, features, targets)


@nodify(
        icon="decisiontree",
        features=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        targets=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        max_depth=Attribute("spinbox", value=10, range=[1, 1000]),
        min_samples_split=Attribute("spinbox", value=2, range=[1, 1000]),
        min_samples_leaf=Attribute("spinbox", value=1, range=[1, 1000]),
        random_state=Attribute("spinbox", value=42, range=[-int(1e9), int(1e9)]),
)
def DecisionTreeRegressor(
    train_data: pd.DataFrame,
    features: list=[],
    targets: list=[],
    max_depth: int=10,
    min_samples_split: int=2,
    min_samples_leaf: int=1,
    random_state: int=42
    ) -> MLModel:
    """
    Preforms a Decision Tree Regression. Input data needs to have >1 column.

    Args:
        train_data (table): Input data for training.
        features (list): Features / inputs for the model.
        targets (list): Targets to predict with the model.
        max_depth (int): Maximum depth of the tree.
        min_samples_split (int): Minimum number of samples required to split a node.
        min_samples_leaf (int): Minimum number of samples per branch after a split.
        random_state (int): Random state for the algorithm.

    Returns:
        model: The fitted model as an input for a predict node.
    """
    from sklearn.tree import DecisionTreeRegressor
    X = train_data[features]
    y = train_data[targets]
    regr = DecisionTreeRegressor(
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state)
    regr.fit(X, y)
    return MLModel("DecTrRegr", regr, features, targets)


@nodify(
        icon="encoder",
        columns=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
)
def OrdinalEncoder(train_data, columns: list = []):
    """
    Perform an ordinal encoding to categrical columns. The output is a fit+transform operation.

    Args:
        train_data (column or table): The input data.
        columns (list): The columns to apply the encoder to.

    Returns:
        table: The transformed train data.
        transform: The fitted encoder to connect to a 'Transform' Node.
    """
    from sklearn.preprocessing import OrdinalEncoder
    encoder = OrdinalEncoder()
    _train_data = train_data.copy()
    _train_data[columns] = encoder.fit_transform(_train_data[columns])
    ml_transform = MLTransform("OrdinalEncoder", encoder, columns)
    return _train_data, ml_transform


@nodify(
        icon="transform"
)
def Transform(transform: MLTransform, test_data):
    """
    Apply a transformation with a fitted transformer (e.g. encoder).

    Note that feature column names are parsed from the trained model instance. If these are not present in tabluar test_data, then an error is thrown. For array- or number-like input data, feature columns are not checked.

    Args:
        transform (transform): The output of a transform node, e.g. encoder.
        test_data (numeric or str): The data to transform.
        name (str): optional, column name of prediction

    Returns:
        table: Input data containing the transformed values.
    """
    if isinstance(test_data, pd.Series):
        test_data = test_data.to_frame()
    elif isinstance(test_data, numbers.Number) or isinstance(test_data, str):
        test_data=np.array([test_data])
    elif isinstance(test_data, list):
        test_data=np.array(test_data)

    if isinstance(test_data, np.ndarray) or isinstance(test_data, list):
        if test_data.ndim==1:
            test_data = test_data.reshape(1,-1)
        if test_data.shape[1] != len(transform.features):
            raise ValueError("Input dimension of array does not match number of expected features.")

        test_data = pd.DataFrame(columns=transform.features, data=test_data)

    if all([f in test_data.columns for f in transform.features]):
        test = test_data[transform.features]
    else:
        raise ValueError(f"Feature columns {transform.features} not present.")

    _test_data = test_data.copy()
    _test_data[transform.features] = transform.transform.transform(test)
    return _test_data


@nodify(
        icon="linreg",
        features=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        targets=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        fit_intercept=Attribute("combobox", value="True", options=["True", "False"])
)
def LinearRegression(
    train_data: pd.DataFrame,
    features: list=[],
    targets: list=[],
    fit_intercept: str="True"
    ) -> MLModel:
    """
    Performs a linear regression. Input data needs to have >1 column.

    Args:
        train_data (table): Input data for training.
        features (list): Features / inputs for the model.
        targets (list): Targets to predict with the model. Values are expected to be discrete numerical values.
        fit_intercept (bool): If intercept is fitted or set to zero.

    Returns:
        model: The fitted model as an input for a predict node.
    """
    from sklearn.linear_model import LinearRegression

    X = train_data[features]
    y = train_data[targets]

    fit_intercept = fit_intercept=="True"
    regr = LinearRegression(fit_intercept=fit_intercept)
    regr.fit(X, y)
    return MLModel("LinReg", regr, features, targets)


@nodify(
        icon="poly",
        features=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        targets=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        degree=Attribute("spinbox", value=1, range=[1, 20]),
        fit_intercept=Attribute("combobox", value="True", options=["True", "False"])
)
def PolynomialRegression(
        train_data: pd.DataFrame,
        features: list=[],
        targets: list=[],
        degree: int=1,
        fit_intercept: str="True",
) -> MLModel:

    """
    Performs a polynomial regression. Input data needs to have >1 column.

    Args:
        train_data (table): Input data for training.
        features (list): Features / inputs for the moidel.
        targets (list): Targets to predict with the model. Values are expected to be discrete numerical values.
        degree (int): The polynomial degree.
        fit_intercept (bool): If intercept is fitted or set to zero.

    Returns:
        model: The fitted model as an input for a predict node.
    """

    from sklearn.linear_model import LinearRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import PolynomialFeatures

    X = train_data[features]
    y = train_data[targets]

    fit_intercept = fit_intercept=="True"
    regr = make_pipeline(PolynomialFeatures(degree), LinearRegression(fit_intercept=fit_intercept))
    regr.fit(X, y)

    return MLModel("PolyReg", regr, features, targets)


@nodify(
        icon="predict"
        )
def Predict(model: MLModel, test_data) -> pd.DataFrame:
    """
    Make predictions using a trained model.

    Note that feature column names are parsed from the trained model instance. If these are not present in tabluar test_data, then an error is thrown.  For array- or number-like input data, feature columns are not checked.

    Args:
        model (model): The output of a model node.
        test_data (numeric): The data to make predictions on.

    Returns:
        table: Input Table containing the predictions.
    """
    if isinstance(test_data, pd.Series):
        test_data = test_data.to_frame()
    elif isinstance(test_data, numbers.Number):
        test_data=np.array([test_data])
    elif isinstance(test_data, list):
        test_data=np.array(test_data)

    if isinstance(test_data, np.ndarray) or isinstance(test_data, list):
        if test_data.ndim==1:
            test_data = test_data.reshape(1,-1)
        if test_data.shape[1] != len(model.features):
            raise ValueError("Input dimension of array does not match number of expected features.")

        test_data = pd.DataFrame(columns=model.features, data=test_data)

    if all([f in test_data.columns for f in model.features]):
        test = test_data[model.features]
    else:
        raise ValueError(f"Feature columns {model.features} not present.")

    new_col_names = [assign_name(test_data.columns, target_name+'_prediction') for target_name in model.targets]

    _test_data=test_data.copy()
    if len(new_col_names)==1:
        _test_data[new_col_names[0]] = model.model.predict(test)
    else:
        _test_data[new_col_names] = model.model.predict(test)
    return _test_data


@nodify(
        icon="randomforest",
        features=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        targets=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        n_estimators=Attribute("spinbox", value=10, range=[1, 1000]),
        criterion=Attribute("combobox", options=["gini", "entropy", "log_loss"]),
        max_depth=Attribute("spinbox", value=10, range=[1, 1000]),
        min_samples_split=Attribute("spinbox", value=2, range=[1, 1000]),
        min_samples_leaf=Attribute("spinbox", value=1, range=[1, 1000]),
        random_state=Attribute("spinbox", value=42, range=[-int(1e9), int(1e9)]),
)
def RandomForestClassifier(
    train_data: pd.DataFrame,
    features: list=[],
    targets: list=[],
    n_estimators: int=10,
    criterion: str="gini",
    max_depth: int=10,
    min_samples_split: int=2,
    min_samples_leaf: int=1,
    random_state: int=42
    ) -> MLModel:

    """
    Preforms a Random Forest Classification. Input data needs to have >1 column.

    Args:
        train_data (table): Input data for training.
        features (list): Features / inputs for the moidel.
        targets (list): Targets to predict with the model. Values are expected to be discrete numerical values.
        n_estimators (int): Number of trees in the forest.
        criterion (str): Criterion for splits.
        max_depth (int): Maximum depth of the tree.
        min_samples_split (int): Minimum number of samples required to split a node.
        min_samples_leaf (int): Minimum number of samples per branch after a split.
        random_state (int): Random state for the algorithm.

    Returns:
        model: The fitted model as an input for a predict node.
    """

    from sklearn.ensemble import RandomForestClassifier

    X = train_data[features]
    y = train_data[targets]
    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        criterion=criterion,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state,
    )

    clf.fit(X, y)
    return MLModel("RandForClf", clf, features, targets)


@nodify(
        icon="randomforest",
        features=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        targets=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        n_estimators=Attribute("spinbox", value=10, range=[1, 1000]),
        max_depth=Attribute("spinbox", value=10, range=[1, 1000]),
        min_samples_split=Attribute("spinbox", value=2, range=[1, 1000]),
        min_samples_leaf=Attribute("spinbox", value=1, range=[1, 1000]),
        random_state=Attribute("spinbox", value=42, range=[-int(1e9), int(1e9)]),
)
def RandomForestRegressor(
    train_data: pd.DataFrame,
    features: list=[],
    targets: list=[],
    n_estimators: int=10,
    max_depth: int=10,
    min_samples_split: int=2,
    min_samples_leaf: int=1,
    random_state: int=42
    ) -> MLModel:

    """
    Preforms a Random Forest Regression. Input data needs to have >1 column.

    Args:
        train_data (table): Input data for training.
        features (list): Features / inputs for the moidel.
        targets (list): Targets to predict with the model. Values are expected to be discrete numerical values.
        n_estimators (int): Number of trees in the forest.
        max_depth (int): Maximum depth of the tree.
        min_samples_split (int): Minimum number of samples required to split a node.
        min_samples_leaf (int): Minimum number of samples per branch after a split.
        random_state (int): Random state for the algorithm.

    Returns:
        model: The fitted model as an input for a predict node.
    """
    from sklearn.ensemble import RandomForestRegressor

    X = train_data[features]
    y = train_data[targets]
    clf = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state,
    )

    clf.fit(X, y)
    return MLModel("RandForRegr", clf, features, targets)


@nodify(
        icon="score",
        y_true=Attribute("combobox", source="data", extractor="dataframe_columns"),
        y_pred=Attribute("combobox", source="data", extractor="dataframe_columns"),
        op=Attribute("combobox", value = "MSE", options=["MSE", "RMSE", "MAE", "MAPE", "R2"])
)
def RegressionMetric(data: pd.DataFrame, y_true: str=None, y_pred: str=None, op: str="MSE") -> numbers.Number:
    """
    Computes popular regression metrics.

    Args:
        y_true (str): Name of the column carrying the true values.
        y_predict (str): Name of the column with predictions.
        op (str): One of "MSE", "RMSE", "MAE", "MAPE", "R2"

    Returns:
        number: The metric score
    """

    from sklearn.metrics import (
        mean_absolute_error,
        mean_squared_error,
        r2_score,
        root_mean_squared_error,
    )

    y_true = data[y_true]
    y_pred = data[y_pred]

    def mape(y_true, y_pred):
        return mean_absolute_error(y_true, y_pred) / np.mean(np.abs(y_true)) * 100

    metric_map = {
        "MSE": mean_squared_error,
        "RMSE": root_mean_squared_error,
        "MAE": mean_absolute_error,
        "MAPE": mape,
        "R2": r2_score
    }
    return metric_map[op](y_true, y_pred)


@nodify(
        icon="split",
        test_size=Attribute("doublespinbox", value=0.3, range=[0, 1]),
        random_state=Attribute("spinbox", value=42, range=[-int(1e9), int(1e9)]),
        shuffle = Attribute("combobox", value="True", options=["True", "False"])
        )
def TrainTestSplit(data, test_size: float=0.3, random_state: int=42, shuffle: str="True"):
    """
    Split data into training and testing sets.

    Args:
        data (column or table): The input data.
        test_size (float): The proportion of the dataset to allocate to the test split (the second output).
        shuffle (bool): If True, data is shuffled. If false, sequential order is preserved.

    Returns:
        column or table: Table containing the training data.
        column or table: Table containint the test data.
    """

    shuffle = shuffle=="True"
    train_df, test_df = train_test_split(data, test_size=test_size, random_state=random_state, shuffle=shuffle)
    return train_df, test_df


@nodify(
        icon="xgboost",
        features=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        targets=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        n_estimators=Attribute("spinbox", value=10, range=[1, 1000]),
        max_depth=Attribute("spinbox", value=10, range=[1, 1000]),
        learning_rate=Attribute("doublespinbox", value=0.3, range=[1,10]),
        random_state=Attribute("spinbox", value=42, range=[-int(1e9), int(1e9)])
)
def XGBoostClassifier(
    train_data: pd.DataFrame,
    features: list=[],
    targets: list=[],
    n_estimators: int=10,
    max_depth: int=10,
    learning_rate: float=0.3,
    random_state: int=42
    ) -> MLModel:
    """
    Train an XGBoost clasifier model. Input data needs to have >1 column.

    Args:
        train_data (table): Input data for training.
        features (list): Features / inputs for the moidel.
        targets (list): Targets to predict with the model. Values are expected to be discrete numerical values.
        n_estimators (int): Number of trees in the forest.
        max_depth (int): Maximum depth of the tree.
        learning_rate (float): Learning rate of the model.
        random_state (int): Random state for the algorithm.

    Returns:
        model: The fitted model as an input for a predict node.
    """

    X = train_data[features]
    y = train_data[targets]

    from xgboost import XGBClassifier

    clf = XGBClassifier(n_estimators=n_estimators, max_depth=max_depth, learning_rate=learning_rate, random_state=random_state)
    clf.fit(X, y)
    return MLModel("XGBClf", clf, features, targets)


@nodify(
        icon="xgboost",
        features=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        targets=Attribute("checkable-combobox", source="train_data", extractor="dataframe_columns"),
        n_estimators=Attribute("spinbox", value=10, range=[1, 1000]),
        max_depth=Attribute("spinbox", value=10, range=[1, 1000]),
        learning_rate=Attribute("doublespinbox", value=0.3, range=[1,10]),
        random_state=Attribute("spinbox", value=42, range=[-int(1e9), int(1e9)])
)
def XGBoostRegressor(
    train_data: pd.DataFrame,
    features: list=[],
    targets: list=[],
    n_estimators: int=10,
    max_depth: int=10,
    learning_rate: float=0.3,
    random_state: int=42
    ) -> MLModel:
    """
    Train an XGBoost regression model. Input data needs to have >1 column.

    Args:
        train_data (table): Input data for training.
        features (list): Features / inputs for the moidel.
        targets (list): Targets to predict with the model. Values are expected to be discrete numerical values.
        n_estimators (int): Number of trees in the forest.
        max_depth (int): Maximum depth of the tree.
        learning_rate (float): Learning rate of the model.
        random_state (int): Random state for the algorithm.

    Returns:
        model: The fitted model as an input for a predict node.
    """

    X = train_data[features]
    y = train_data[targets]

    from xgboost import XGBRegressor

    regr = XGBRegressor(n_estimators=n_estimators, max_depth=max_depth, learning_rate=learning_rate, random_state=random_state)
    regr.fit(X, y)
    return MLModel("XGBRegr", regr, features, targets)


