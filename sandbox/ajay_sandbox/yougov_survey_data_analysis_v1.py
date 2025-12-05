#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec  5 17:18:00 2025

@author: ajaykumar
"""

###############
#Libraries
###############

import pandas as pd
#%% Load Yougov Survey data

df_surveys = pd.read_csv('../../data/yougov_survey_data/YouGovProcessedData.csv') 

print('length: ', len(df_surveys))


#%%

"""
Pro climate index: 'ProClimatePolSupp'

Anti-climate (obstruction): 'AntiClimatePolSupp'

"""
#%%

"""
Correlation matrix
"""
#%% 
col_list=['age','male_dummy',
  'tprofile_GOR',
  "profile_education_level",
  'tprofile_gross_household',
  'ethnicity_R',
  'parent_dummy',
  'Vote2019R',
  'pastvote_EURef',
  'new_socgrade',
  'Political_Left_Right','ProClimatePolSupp','AntiClimatePolSupp']
df_fil= df_surveys[col_list]

#%%

col_list=['ProClimatePolSupp','AntiClimatePolSupp','age','male_dummy',
  'tprofile_GOR',
  "profile_education_level",
  'tprofile_gross_household',
  'ethnicity_R',
  'parent_dummy',
  'Vote2019R',
  'pastvote_EURef',
  'new_socgrade',
  'Political_Left_Right','Selfenh_Values','Power_Values','Altr_values','Biosph_values','Selftransc_Val','ConformTrad','Openness','Author_Val','Domin_Val',\
      'EDO','SDO','Submission','Tradition','Aggression','RWA','EcoFasc1','AntiFossilFuelNorms','SufficiencyNorms','Anomie','PersClimateAction']

df_fil= df_surveys[col_list]

#%%

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# 1. Create a sample DataFrame (replace this with your actual data)
# Generating random data for demonstration
#np.random.seed(42)
#data = np.random.rand(10, 5)
#df = pd.DataFrame(data, columns=['Var1', 'Var2', 'Var3', 'Var4', 'Var5'])

# 2. Calculate the correlation matrix
corr_matrix = df_fil.corr()

# 3. Plot the heatmap
plt.figure(figsize=(10, 8))  # Set the figure size
sns.heatmap(corr_matrix, 
            annot=True,      # Show the correlation values on the squares
            cmap='coolwarm', # Color map (coolwarm is common for correlations)
            fmt=".2f",       # Format the numbers to 2 decimal places
            linewidths=.5)   # Add lines between squares

plt.title('Correlation Matrix')
plt.show()

#%%
"""
High-d visualization

"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.datasets import make_blobs

def run_tsne_visualization(df,feature_cols):
    # ---------------------------------------------------------
    # 1. Generate Dummy Data (Replace this with your DataFrame)
    # ---------------------------------------------------------
    # Creating a dataset with 500 samples, 50 features, and 4 distinct centers (clusters)
    # print("Generating synthetic data...")
    # X, y = make_blobs(n_samples=500, n_features=50, centers=4, random_state=42)
    
    # # Convert to pandas DataFrame to simulate your input
    # feature_cols = [f'feature_{i}' for i in range(X.shape[1])]
    # df = pd.DataFrame(X, columns=feature_cols)
    
    # # Add the labels (target) column for coloring the plot later
    # # If your data doesn't have labels, you can skip using 'hue' in the plot
    # df['target_label'] = y

    # ---------------------------------------------------------
    # 2. Preprocessing
    # ---------------------------------------------------------
    # t-SNE is based on distance, so it is highly recommended to scale
    # your data so that all features contribute equally.
    print("Scaling data...")
    
    # Separate features (X) from labels (y)
    features = df[feature_cols]
    
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    # ---------------------------------------------------------
    # 3. Compute t-SNE
    # ---------------------------------------------------------
    print("Running t-SNE (this might take a moment)...")
    
    # n_components=2: Reduce to 2 dimensions for X/Y plotting
    # perplexity: Related to the number of nearest neighbors (usually 5-50)
    # random_state: Ensures the plot looks the same every time you run it
    tsne = TSNE(n_components=2, perplexity=50, n_iter=1000, random_state=42)
    
    tsne_results = tsne.fit_transform(features_scaled)

    # ---------------------------------------------------------
    # 4. Prepare Data for Plotting
    # ---------------------------------------------------------
    # Create a new DataFrame containing the 2 dimensions and the original labels
    df_tsne = pd.DataFrame(data=tsne_results, columns=['tsne_1', 'tsne_2'])
    df_tsne['cluster'] = df['target_label']

    # ---------------------------------------------------------
    # 5. Visualization
    # ---------------------------------------------------------
    print("Plotting results...")
    
    plt.figure(figsize=(10, 8))
    
    sns.scatterplot(
        x='tsne_1', 
        y='tsne_2', 
        hue='cluster',     # Color points by cluster label
        palette='viridis', # Color scheme
        data=df_tsne,
        legend='full',
        alpha=0.7          # Transparency
    )

    plt.title('t-SNE Visualization of Clusters', fontsize=16)
    plt.xlabel('t-SNE Dimension 1', fontsize=12)
    plt.ylabel('t-SNE Dimension 2', fontsize=12)
    
    # Save or show the plot
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()
    print("Done!")

# if __name__ == "__main__":


feature_cols=['age','male_dummy',
  'tprofile_GOR',
  "profile_education_level",
  'tprofile_gross_household',
  'ethnicity_R',
  'parent_dummy',
  'Vote2019R',
  'pastvote_EURef',
  'new_socgrade',
  'Political_Left_Right']

#'ProClimatePolSupp','AntiClimatePolSupp'

df_fil= df_surveys[feature_cols]
df_fil['target_label'] = [int(x) for x in df_surveys['AntiClimatePolSupp']]

df_fil = df_fil.dropna(subset=df_fil.columns.values)

#run_tsne_visualization(df_fil,feature_cols)

#%%

import pandas as pd
import numpy as np
import statsmodels.api as sm

def run_backward_elimination(df):
    # ---------------------------------------------------------
    # 1. Generate Dummy Data (Replace with your actual DataFrame)
    # ---------------------------------------------------------
    # np.random.seed(42)
    # n_samples = 200

    # # Create 5 features:
    # # - Age & Income: Strong contributors
    # # - Education: Weak contributor
    # # - Hair_Length & Fav_Number: Complete noise (random)
    # data = {
    #     'Age': np.random.randint(20, 60, n_samples),
    #     'Income': np.random.normal(50000, 15000, n_samples),
    #     'Education_Years': np.random.randint(12, 20, n_samples),
    #     'Hair_Length': np.random.normal(10, 5, n_samples),   # Noise
    #     'Fav_Number': np.random.randint(0, 100, n_samples)   # Noise
    # }
    
    # df = pd.DataFrame(data)

    # # Generate a target variable 'Spend_Score' based on Age and Income (plus some randomness)
    # # We purposefully leave Hair_Length and Fav_Number out of this equation
    # df['Spend_Score'] = (
    #     0.5 * df['Age'] + 
    #     0.002 * df['Income'] + 
    #     0.8 * df['Education_Years'] + 
    #     np.random.normal(0, 5, n_samples)
    # )

    # print("--- Original Features ---")
    # print(df.columns.tolist()[:-1]) # Print everything except target
    # print("-" * 30)

    # ---------------------------------------------------------
    # 2. The Backward Elimination Function
    # ---------------------------------------------------------
    def backward_elimination(data_frame, target_col, significance_level=0.05):
        # Separate features (X) and target (y)
        X = data_frame.drop(columns=[target_col])
        y = data_frame[target_col]

        # STATSMODELS REQUIREMENT:
        # Unlike sklearn, statsmodels does not add an intercept (constant) by default.
        # We must add a column of 1s to represent the mathematical intercept.
        X = sm.add_constant(X)
        
        # Get list of current attributes
        col_list = list(X.columns)
        
        while True:
            # 1. Fit the model with current attributes
            # OLS = Ordinary Least Squares (Standard Linear Regression)
            model = sm.OLS(y, X[col_list]).fit()
            
            # 2. Get the maximum p-value in the current model
            p_values = model.pvalues
            max_p = p_values.max()
            max_feature = p_values.idxmax()
            
            # 3. Check if the worst feature is statistically insignificant
            if max_p > significance_level:
                print(f"Removing '{max_feature}' (p-value: {max_p:.4f}) -> Not significant")
                
                # Remove from list
                col_list.remove(max_feature)
            else:
                # If the highest p-value is < 0.05, ALL features are significant.
                print("Optimization Complete: All remaining features are significant.")
                break
        
        # Return the final model
        return model

    # ---------------------------------------------------------
    # 3. Run the analysis
    # ---------------------------------------------------------
    final_model = backward_elimination(df, 'target_label')

    # ---------------------------------------------------------
    # 4. Display Results
    # ---------------------------------------------------------
    print("\n" + "="*40)
    print("FINAL MODEL SUMMARY")
    print("="*40)
    print(final_model.summary())


col_list=['age','male_dummy',
  'tprofile_GOR',
  "profile_education_level",
  'tprofile_gross_household',
  'ethnicity_R',
  'parent_dummy',
  'Vote2019R',
  'pastvote_EURef',
  'new_socgrade',
  'Political_Left_Right','Selfenh_Values','Power_Values','Altr_values','Biosph_values','Selftransc_Val','ConformTrad','Openness','Author_Val','Domin_Val',\
      'EDO','SDO','Submission','Tradition','Aggression','RWA','EcoFasc1','AntiFossilFuelNorms','SufficiencyNorms','Anomie','PersClimateAction']

df_fil= df_surveys[col_list]

df_fil['target_label']=df_surveys['ProClimatePolSupp']
df_fil = df_fil.dropna(subset=df_fil.columns.values)

run_backward_elimination(df_fil)
#%%


plt.figure()
plt.scatter(df_fil['Political_Left_Right'],df_fil['ProClimatePolSupp'],color='red')
plt.show()




"""
runcell(7, '/Users/ajaykumar/Documents/GitHub/Climate-Action-GABM/sandbox/ajay_sandbox/yougov_survey_data_analysis_v1.py')
Removing 'tprofile_gross_household' (p-value: 0.6858) -> Not significant
Removing 'tprofile_GOR' (p-value: 0.3744) -> Not significant
Optimization Complete: All remaining features are significant.

========================================
FINAL MODEL SUMMARY
========================================
                            OLS Regression Results                            
==============================================================================
Dep. Variable:           target_label   R-squared:                       0.234
Model:                            OLS   Adj. R-squared:                  0.230
Method:                 Least Squares   F-statistic:                     52.81
Date:                Fri, 05 Dec 2025   Prob (F-statistic):           6.24e-84
Time:                        22:01:33   Log-Likelihood:                -2452.5
No. Observations:                1565   AIC:                             4925.
Df Residuals:                    1555   BIC:                             4979.
Df Model:                           9                                         
Covariance Type:            nonrobust                                         
===========================================================================================
                              coef    std err          t      P>|t|      [0.025      0.975]
-------------------------------------------------------------------------------------------
const                       1.1094      0.220      5.032      0.000       0.677       1.542
age                         0.0064      0.002      3.114      0.002       0.002       0.010
male_dummy                  0.1871      0.060      3.144      0.002       0.070       0.304
profile_education_level    -0.0293      0.007     -4.244      0.000      -0.043      -0.016
ethnicity_R                 0.0630      0.030      2.108      0.035       0.004       0.122
parent_dummy                0.2395      0.065      3.659      0.000       0.111       0.368
Vote2019R                  -0.0585      0.013     -4.475      0.000      -0.084      -0.033
pastvote_EURef              0.2840      0.040      7.057      0.000       0.205       0.363
new_socgrade                0.2904      0.066      4.385      0.000       0.160       0.420
Political_Left_Right        0.1903      0.015     13.110      0.000       0.162       0.219
==============================================================================
Omnibus:                       26.498   Durbin-Watson:                   2.062
Prob(Omnibus):                  0.000   Jarque-Bera (JB):               27.579
Skew:                           0.321   Prob(JB):                     1.03e-06
Kurtosis:                       2.894   Cond. No.                         400.
==============================================================================

Notes:
[1] Standard Errors assume that the covariance matrix of the errors is correctly specified.

runcell(8, '/Users/ajaykumar/Documents/GitHub/Climate-Action-GABM/sandbox/ajay_sandbox/yougov_survey_data_analysis_v1.py')

runcell(8, '/Users/ajaykumar/Documents/GitHub/Climate-Action-GABM/sandbox/ajay_sandbox/yougov_survey_data_analysis_v1.py')

runcell(7, '/Users/ajaykumar/Documents/GitHub/Climate-Action-GABM/sandbox/ajay_sandbox/yougov_survey_data_analysis_v1.py')
Removing 'Openness' (p-value: 0.9521) -> Not significant
Removing 'tprofile_gross_household' (p-value: 0.8509) -> Not significant
Removing 'Altr_values' (p-value: 0.8263) -> Not significant
Removing 'Biosph_values' (p-value: 0.8263) -> Not significant
Removing 'ethnicity_R' (p-value: 0.7215) -> Not significant
Removing 'Tradition' (p-value: 0.5332) -> Not significant
Removing 'profile_education_level' (p-value: 0.4795) -> Not significant
Removing 'Power_Values' (p-value: 0.4334) -> Not significant
Removing 'tprofile_GOR' (p-value: 0.2852) -> Not significant
Removing 'EDO' (p-value: 0.0529) -> Not significant
Removing 'Submission' (p-value: 0.0502) -> Not significant
Removing 'RWA' (p-value: 0.1890) -> Not significant
Optimization Complete: All remaining features are significant.

========================================
FINAL MODEL SUMMARY
========================================
                            OLS Regression Results                            
==============================================================================
Dep. Variable:           target_label   R-squared:                       0.589
Model:                            OLS   Adj. R-squared:                  0.584
Method:                 Least Squares   F-statistic:                     116.6
Date:                Fri, 05 Dec 2025   Prob (F-statistic):          1.22e-281
Time:                        22:15:45   Log-Likelihood:                -1966.3
No. Observations:                1565   AIC:                             3973.
Df Residuals:                    1545   BIC:                             4080.
Df Model:                          19                                         
Covariance Type:            nonrobust                                         
========================================================================================
                           coef    std err          t      P>|t|      [0.025      0.975]
----------------------------------------------------------------------------------------
const                    2.0584      0.259      7.955      0.000       1.551       2.566
age                      0.0051      0.002      3.073      0.002       0.002       0.008
male_dummy              -0.1223      0.046     -2.632      0.009      -0.213      -0.031
parent_dummy             0.1160      0.049      2.381      0.017       0.020       0.212
Vote2019R               -0.0248      0.010     -2.543      0.011      -0.044      -0.006
pastvote_EURef           0.1091      0.030      3.636      0.000       0.050       0.168
new_socgrade             0.1582      0.049      3.255      0.001       0.063       0.253
Political_Left_Right     0.0296      0.012      2.480      0.013       0.006       0.053
Selfenh_Values           0.2040      0.076      2.683      0.007       0.055       0.353
Selftransc_Val          -0.4884      0.079     -6.152      0.000      -0.644      -0.333
ConformTrad              0.2856      0.043      6.636      0.000       0.201       0.370
Author_Val              -0.0825      0.031     -2.690      0.007      -0.143      -0.022
Domin_Val               -0.2426      0.073     -3.341      0.001      -0.385      -0.100
SDO                      0.1717      0.031      5.531      0.000       0.111       0.233
Aggression              -0.0580      0.021     -2.728      0.006      -0.100      -0.016
EcoFasc1                 0.1916      0.020      9.689      0.000       0.153       0.230
AntiFossilFuelNorms     -0.3239      0.028    -11.488      0.000      -0.379      -0.269
SufficiencyNorms        -0.0671      0.027     -2.483      0.013      -0.120      -0.014
Anomie                   0.0646      0.023      2.855      0.004       0.020       0.109
PersClimateAction       -0.1484      0.018     -8.446      0.000      -0.183      -0.114
==============================================================================
Omnibus:                       17.788   Durbin-Watson:                   2.024
Prob(Omnibus):                  0.000   Jarque-Bera (JB):               19.642
Skew:                           0.208   Prob(JB):                     5.43e-05
Kurtosis:                       3.358   Cond. No.                         629.
==============================================================================

Notes:
[1] Standard Errors assume that the covariance matrix of the errors is correctly specified.
/Users/ajaykumar/Documents/GitHub/Climate-Action-GABM/sandbox/ajay_sandbox/yougov_survey_data_analysis_v1.py:294: SettingWithCopyWarning: 
A value is trying to be set on a copy of a slice from a DataFrame.
Try using .loc[row_indexer,col_indexer] = value instead

See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
  df_fil['target_label']=df_surveys['AntiClimatePolSupp']

runcell(7, '/Users/ajaykumar/Documents/GitHub/Climate-Action-GABM/sandbox/ajay_sandbox/yougov_survey_data_analysis_v1.py')
Removing 'parent_dummy' (p-value: 0.9973) -> Not significant
Removing 'Altr_values' (p-value: 0.9739) -> Not significant
Removing 'Selftransc_Val' (p-value: 0.9739) -> Not significant
Removing 'ConformTrad' (p-value: 0.7673) -> Not significant
Removing 'Submission' (p-value: 0.7589) -> Not significant
Removing 'tprofile_gross_household' (p-value: 0.6716) -> Not significant
Removing 'new_socgrade' (p-value: 0.6636) -> Not significant
Removing 'Power_Values' (p-value: 0.5952) -> Not significant
Removing 'Anomie' (p-value: 0.4123) -> Not significant
Removing 'Author_Val' (p-value: 0.2993) -> Not significant
Removing 'profile_education_level' (p-value: 0.2727) -> Not significant
Removing 'EcoFasc1' (p-value: 0.2581) -> Not significant
Removing 'SufficiencyNorms' (p-value: 0.0537) -> Not significant
Optimization Complete: All remaining features are significant.

========================================
FINAL MODEL SUMMARY
========================================
                            OLS Regression Results                            
==============================================================================
Dep. Variable:           target_label   R-squared:                       0.538
Model:                            OLS   Adj. R-squared:                  0.533
Method:                 Least Squares   F-statistic:                     100.1
Date:                Fri, 05 Dec 2025   Prob (F-statistic):          1.19e-243
Time:                        22:19:17   Log-Likelihood:                -2010.8
No. Observations:                1565   AIC:                             4060.
Df Residuals:                    1546   BIC:                             4161.
Df Model:                          18                                         
Covariance Type:            nonrobust                                         
========================================================================================
                           coef    std err          t      P>|t|      [0.025      0.975]
----------------------------------------------------------------------------------------
const                    5.1404      0.253     20.283      0.000       4.643       5.637
age                     -0.0083      0.002     -5.413      0.000      -0.011      -0.005
male_dummy               0.1003      0.048      2.099      0.036       0.007       0.194
tprofile_GOR            -0.0160      0.008     -2.053      0.040      -0.031      -0.001
ethnicity_R              0.0733      0.023      3.201      0.001       0.028       0.118
Vote2019R                0.0260      0.010      2.595      0.010       0.006       0.046
pastvote_EURef          -0.0705      0.031     -2.298      0.022      -0.131      -0.010
Political_Left_Right    -0.0482      0.012     -3.994      0.000      -0.072      -0.025
Selfenh_Values           0.1422      0.043      3.302      0.001       0.058       0.227
Biosph_values            0.1797      0.028      6.517      0.000       0.126       0.234
Openness                -0.0744      0.031     -2.367      0.018      -0.136      -0.013
Domin_Val               -0.0699      0.035     -2.005      0.045      -0.138      -0.002
EDO                     -0.0517      0.023     -2.295      0.022      -0.096      -0.008
SDO                     -0.2914      0.033     -8.850      0.000      -0.356      -0.227
Tradition               -0.2463      0.036     -6.886      0.000      -0.316      -0.176
Aggression              -0.1758      0.033     -5.263      0.000      -0.241      -0.110
RWA                      0.3500      0.077      4.574      0.000       0.200       0.500
AntiFossilFuelNorms      0.2663      0.027      9.920      0.000       0.214       0.319
PersClimateAction        0.1901      0.018     10.651      0.000       0.155       0.225
==============================================================================
Omnibus:                       25.698   Durbin-Watson:                   1.965
Prob(Omnibus):                  0.000   Jarque-Bera (JB):               28.228
Skew:                          -0.269   Prob(JB):                     7.42e-07
Kurtosis:                       3.378   Cond. No.                         604.
==============================================================================
"""






