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











