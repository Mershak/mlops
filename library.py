import pandas as pd
import numpy as np
import sklearn
sklearn.set_config(transform_output="pandas")  #says pass pandas tables through pipeline instead of numpy matrices
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
import subprocess
import sys
subprocess.call([sys.executable, '-m', 'pip', 'install', 'category_encoders'])  #replaces !pip install
import category_encoders as ce
from sklearn.impute import KNNImputer
from sklearn.metrics import f1_score  
from sklearn.neighbors import KNeighborsClassifier 
from sklearn.model_selection import train_test_split

class CustomMappingTransformer(BaseEstimator, TransformerMixin):

  def __init__(self, mapping_column, mapping_dict:dict):
    assert isinstance(mapping_dict, dict), f'{self.__class__.__name__} constructor expected dictionary but got {type(mapping_dict)} instead.'
    self.mapping_dict = mapping_dict
    self.mapping_column = mapping_column  #column to focus on

  def fit(self, X, y = None):
    print(f"\nWarning: {self.__class__.__name__}.fit does nothing.\n")
    return self

  def transform(self, X):
    assert isinstance(X, pd.core.frame.DataFrame), f'{self.__class__.__name__}.transform expected Dataframe but got {type(X)} instead.'
    assert self.mapping_column in X.columns.to_list(), f'{self.__class__.__name__}.transform unknown column "{self.mapping_column}"'  #column legit?

    #Set up for producing warnings. First have to rework nan values to allow set operations to work.
    #In particular, the conversion of a column to a Series, e.g., X[self.mapping_column], transforms nan values in strange ways that screw up set differencing.
    #Strategy is to convert empty values to a string then the string back to np.nan
    placeholder = "NaN"
    column_values = X[self.mapping_column].fillna(placeholder).tolist()  #convert all nan values to the string "NaN" in new list
    column_values = [np.nan if v == placeholder else v for v in column_values]  #now convert back to np.nan
    keys_values = self.mapping_dict.keys()

    column_set = set(column_values)  #without the conversion above, the set will fail to have np.nan values where they should be.
    keys_set = set(keys_values)      #this will have np.nan values where they should be so no conversion necessary.

    #now check to see if all keys are contained in column.
    keys_not_found = keys_set - column_set
    if keys_not_found:
      print(f"\nWarning: {self.__class__.__name__}[{self.mapping_column}] these mapping keys do not appear in the column: {keys_not_found}\n")

    #now check to see if some keys are absent
    keys_absent = column_set -  keys_set
    if keys_absent:
      print(f"\nWarning: {self.__class__.__name__}[{self.mapping_column}] these values in the column do not contain corresponding mapping keys: {keys_absent}\n")

    #do actual mapping
    X_ = X.copy()
    X_[self.mapping_column].replace(self.mapping_dict, inplace=True)
    return X_

  def fit_transform(self, X, y = None):
    #self.fit(X,y)
    result = self.transform(X)
    return result



#This class will rename one or more columns.
class CustomRenamingTransformer(BaseEstimator, TransformerMixin):

  def __init__(self, mapping_dict:dict):
    assert isinstance(mapping_dict, dict), f'{self.__class__.__name__} constructor expected dictionary but got {type(mapping_dict)} instead.'
    self.mapping_dict = mapping_dict

  def fit(self, X, y = None):
    print(f"\nWarning: {self.__class__.__name__}.fit does nothing.\n")
    return self

  def transform(self, X):
    assert isinstance(X, pd.core.frame.DataFrame), f'{self.__class__.__name__}.transform expected Dataframe but got {type(X)} instead.'

    #Set up for producing warnings. First have to rework nan values to allow set operations to work.
    #In particular, the conversion of a column to a Series, e.g., X[self.mapping_column], transforms nan values in strange ways that screw up set differencing.
    #Strategy is to convert empty values to a string then the string back to np.nan
    placeholder = "NaN"
    keys_values = self.mapping_dict.keys()

    keys_set = set(keys_values)      #this will have np.nan values where they should be so no conversion necessary.
    column_set = set(X.columns.to_list())

    #now check to see if all keys are contained in column.
    columns_not_found = keys_set - column_set
    assert not columns_not_found, (f"\nWarning: {self.__class__.__name__}.transform these columns do not appear in the dataframe: {columns_not_found}\n")

    #do actual mapping
    X_ = X.copy()
    X_.rename(columns=self.mapping_dict, inplace=True)
    return X_

  def fit_transform(self, X, y = None):
    #self.fit(X,y)
    result = self.transform(X)
    return result



class CustomOHETransformer(BaseEstimator, TransformerMixin):
  def __init__(self, target_column, dummy_na=False, drop_first=False):
    self.target_column = target_column
    self.dummy_na = dummy_na
    self.drop_first = drop_first
    self.prefix_sep = "_"
    self.prefix = target_column

  #fill in the rest below
  def fit(self,x,y=None):
    return self

  def transform(self,X):
    assert isinstance(X, pd.core.frame.DataFrame), f'{self.__class__.__name__}.transform expected Dataframe but got {type(X)} instead.'
    assert self.target_column in X.columns.to_list(), f'{self.__class__.__name__}.transform the targeted column "{self.target_column}" is not in the given dataframe columns.'

    # Do the magic
    X_ = X.copy()
    X_ = pd.get_dummies(X_,
                   columns=[self.target_column],
                   prefix=self.prefix,
                   prefix_sep=self.prefix_sep,
                   dummy_na=self.dummy_na,
                   drop_first=self.drop_first
                   )
    return X_

    def fit_transform(self, X, y = None):
      #self.fit(X,y)
      result = self.transform(X)
      return result


class CustomTukeyTransformer(BaseEstimator, TransformerMixin):
  def __init__(self, target_column, fence='outer'):
    assert fence in ['inner', 'outer']
    self.fitted = False
    self.target_column = target_column
    self.fence = fence

  def fit(self,df):
    assert isinstance(df, pd.core.frame.DataFrame), f'expected Dataframe but got {type(df)} instead.'
    assert self.target_column in df.columns, f'unknown column {self.target_column}'
    assert all([isinstance(v, (int, float)) for v in df[self.target_column].to_list()])

    q1 = df[self.target_column].quantile(0.25)
    q3 = df[self.target_column].quantile(0.75)
    iqr = q3-q1
    if self.fence == "outer":
      self.low = q1-3*iqr
      self.high = q3+3*iqr
    else:
      # print("asd")
      self.low = q1-1.5*iqr
      self.high = q3+1.5*iqr
    self.fitted = True
    return self

  def transform(self, df):
    assert self.fitted, f'NotFittedError: This {self.__class__.__name__} instance is not fitted yet. Call "fit" with appropriate arguments before using this estimator.'
    self.df = df.copy()
    self.df[self.target_column] = self.df[self.target_column].clip(lower=self.low, upper=self.high)
    # self.df.reset_index(drop=True)
    return self.df

  def fit_transform(self, df, x=None):
    self.fit(df)
    return self.transform(df)


class CustomSigma3Transformer(BaseEstimator, TransformerMixin):
  def __init__(self, target_column):
    self.target_column = target_column
    self.fitted = False

  def fit(self, df):
    assert isinstance(df, pd.core.frame.DataFrame), f'expected Dataframe but got {type(df)} instead.'
    assert self.target_column in df.columns, f'unknown column {self.target_column}'
    assert all([isinstance(v, (int, float)) for v in df[self.target_column].to_list()])

    #your code below
    sigma = df[self.target_column].std()
    mean = df[self.target_column].mean()
    self.sigma_low = mean - 3 * sigma
    self.sigma_high = mean + 3 * sigma
    self.fitted = True

  def transform(self, df):
    assert self.fitted, f'NotFittedError: This {self.__class__.__name__} instance is not fitted yet. Call "fit" with appropriate arguments before using this estimator.'
    self.df = df.copy()
    self.df[self.target_column] = self.df[self.target_column].clip(lower=self.sigma_low, upper=self.sigma_high)
    self.df.reset_index(drop=True)
    return self.df

  def fit_transform(self, df):
    self.fit(df)
    return self.transform(df)


class CustomRobustTransformer(BaseEstimator, TransformerMixin):
  def __init__(self, column):
    self.column = column
    #fill in rest below

  def fit (self,df, y=None):
    self.iqr = float(df[self.column].quantile(.75) - df[self.column].quantile(.25))
    self.med = df[self.column].median()
    return self
  
  def transform(self,df):
    self.df = df.copy()
    self.df[self.column] -= self.med
    self.df[self.column] /= self.iqr
    return self.df

  def fit_transform(self,df,y=None):
    self.fit(df)
    return self.transform(df)

def find_random_state(features_df, labels, n=200):
  model = KNeighborsClassifier(n_neighbors=5)  #instantiate with k=5.
  var = []  #collect test_error/train_error where error based on F1 score

  #2 minutes
  for i in range(1, n):
      train_X, test_X, train_y, test_y = train_test_split(features_df, labels, test_size=0.2, shuffle=True,
                                                      random_state=i, stratify=labels)
      model.fit(train_X, train_y)  #train model
      train_pred = model.predict(train_X)           #predict against training set
      test_pred = model.predict(test_X)             #predict against test set
      train_f1 = f1_score(train_y, train_pred)   #F1 on training predictions
      test_f1 = f1_score(test_y, test_pred)      #F1 on test predictions
      f1_ratio = test_f1/train_f1          #take the ratio
      var.append(f1_ratio)

  rs_value = sum(var)/len(var)  #get average ratio value
  rs_value  #0.8501547035464532
  idx = np.array(abs(var - rs_value)).argmin()  #find the index of the smallest value
  return idx

titanic_variance_based_split = 107

customer_variance_based_split = 113

titanic_transformer = Pipeline(steps=[
    ('map_gender', CustomMappingTransformer('Gender', {'Male': 0, 'Female': 1})),
    ('map_class', CustomMappingTransformer('Class', {'Crew': 0, 'C3': 1, 'C2': 2, 'C1': 3})),
    ('target_joined', ce.TargetEncoder(cols=['Joined'],
                           handle_missing='return_nan', #will use imputer later to fill in
                           handle_unknown='return_nan'  #will use imputer later to fill in
    )),
    ('tukey_age', CustomTukeyTransformer(target_column='Age', fence='outer')),
    ('tukey_fare', CustomTukeyTransformer(target_column='Fare', fence='outer')),
    ('scale_age', CustomRobustTransformer('Age')),  #from chapter 5
    ('scale_fare', CustomRobustTransformer('Fare')),  #from chapter 5
    ('imputer', KNNImputer(n_neighbors=5, weights="uniform", add_indicator=False))  #from chapter 6
    ], verbose=True)


customer_transformer = Pipeline(steps=[
    ('map_os', CustomMappingTransformer('OS', {'Android': 0, 'iOS': 1})),
    ('target_isp', ce.TargetEncoder(cols=['ISP'],
                           handle_missing='return_nan', #will use imputer later to fill in
                           handle_unknown='return_nan'  #will use imputer later to fill in
    )),
    ('map_level', CustomMappingTransformer('Experience Level', {'low': 0, 'medium': 1, 'high':2})),
    ('map_gender', CustomMappingTransformer('Gender', {'Male': 0, 'Female': 1})),
    ('tukey_age', CustomTukeyTransformer('Age', 'inner')),  #from chapter 4
    ('tukey_time spent', CustomTukeyTransformer('Time Spent', 'inner')),  #from chapter 4
    ('scale_age', CustomRobustTransformer('Age')), #from 5
    ('scale_time spent', CustomRobustTransformer('Time Spent')), #from 5
    ('impute', KNNImputer(n_neighbors=5, weights="uniform", add_indicator=False)),
    ], verbose=True)

def dataset_setup(original_table, label_column_name:str, the_transformer, rs, ts=.2):
  #your code below
  X_train, X_test, y_train, y_test = train_test_split(original_table.drop(columns=label_column_name), original_table[label_column_name].to_list(), test_size=ts, shuffle=True,
                                                    random_state=rs, stratify=original_table[label_column_name].to_list())
  
  X_train_transformed = the_transformer.fit_transform(X_train, y_train)
  X_test_transformed = the_transformer.transform(X_test)

  X_train_numpy = X_train_transformed.to_numpy()
  X_test_numpy = X_test_transformed.to_numpy()
  y_train_numpy = np.array(y_train)
  y_test_numpy = np.array(y_test)

  return X_train_numpy, X_test_numpy, y_train_numpy, y_test_numpy

def titanic_setup(titanic_table, transformer=titanic_transformer, rs=titanic_variance_based_split, ts=.2):
  return dataset_setup(titanic_table, 'Survived', transformer, rs=rs, ts=ts)

def customer_setup(customer_table, transformer=customer_transformer, rs=customer_variance_based_split, ts=.2):
  return dataset_setup(customer_table, 'Rating', transformer, rs=rs, ts=ts)


from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
def threshold_results(thresh_list, actuals, predicted):
  result_df = pd.DataFrame(columns=['threshold', 'precision', 'recall', 'f1', 'accuracy'])
  for t in thresh_list:
    yhat = [1 if v >=t else 0 for v in predicted]
    #note: where TP=0, the Precision and Recall both become 0. And I am saying return 0 in that case.
    precision = precision_score(actuals, yhat, zero_division=0)
    recall = recall_score(actuals, yhat, zero_division=0)
    f1 = f1_score(actuals, yhat)
    accuracy = accuracy_score(actuals, yhat)
    result_df.loc[len(result_df)] = {'threshold':t, 'precision':precision, 'recall':recall, 'f1':f1, 'accuracy':accuracy}

  result_df = result_df.round(2)

  #Next bit fancies up table for printing. See https://betterdatascience.com/style-pandas-dataframes/
  #Note that fancy_df is not really a dataframe. More like a printable object.
  headers = {
    "selector": "th:not(.index_name)",
    "props": "background-color: #800000; color: white; text-align: center"
  }
  properties = {"border": "1px solid black", "width": "65px", "text-align": "center"}

  fancy_df = result_df.style.format(precision=2).set_properties(**properties).set_table_styles([headers])
  return (result_df, fancy_df)

from sklearn.experimental import enable_halving_search_cv
from sklearn.model_selection import HalvingGridSearchCV

def halving_search(model, grid, x_train, y_train, factor=2, min_resources="exhaust", scoring='roc_auc'):
  #your code below
  halving_cv = HalvingGridSearchCV(
    model, grid,  #our model and the parameter combos we want to try
    scoring=scoring,  #from chapter 10
    n_jobs=-1,  #use all available cpus
    min_resources=min_resources,  #"exhaust" sets this to 20, which is non-optimal. Possible bug in algorithm.
    factor=factor,  #double samples and take top half of combos on each iteration
    cv=5, random_state=1234,
    refit=True,  #remembers the best combo and gives us back that model already trained and ready for testing
  )

  return halving_cv.fit(x_train, y_train)

