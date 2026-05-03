import pandas as pd
from datetime import datetime
import numpy as np


class StageTracker:
    def __init__(self, df):
        self.df = df.copy()
        self.stages = ['Sourcing Start', 'Submission Date', 'Interview Start', 
                       'Interview End', 'Offered', 'Filled']
        self.durations = ['Dur_Sourcing_to_Submission', 'Dur_Submission_to_InterviewStart', 
                          'Dur_InterviewStart_to_InterviewEnd', 'Dur_InterviewEnd_to_Offered', 'Dur_Offered_to_Filled']
        self.features = [
            'Sourcing_start_day',
            'Sourcing_start_month',
            'Salary ($1000)',
            'JobTitle_Encoded'
        ]

        self.models = {}

    # --------------------------
    # Preprocessing
    # --------------------------
    def preprocess(self):
        for col in self.stages:
            self.df[col] = pd.to_datetime(self.df[col], errors='coerce')
            
        self.df['Salary ($1000)'] = pd.to_numeric(
            self.df['Salary ($1000)'], errors='coerce'
        )
            
        # Compute durations in days
        self.df['Dur_Sourcing_to_Submission'] = (self.df['Submission Date'] - self.df['Sourcing Start']).dt.total_seconds() / (3600*24)
        self.df['Dur_Submission_to_InterviewStart'] = (self.df['Interview Start'] - self.df['Submission Date']).dt.total_seconds() / (3600*24)
        self.df['Dur_InterviewStart_to_InterviewEnd'] = (self.df['Interview End'] - self.df['Interview Start']).dt.total_seconds() / (3600*24)
        self.df['Dur_InterviewEnd_to_Offered'] = (self.df['Offered'] - self.df['Interview End']).dt.total_seconds() / (3600*24)
        self.df['Dur_Offered_to_Filled'] = (self.df['Filled'] - self.df['Offered']).dt.total_seconds() / (3600*24)
        
        # Add simple features
        self.df['Sourcing_start_day'] = self.df['Sourcing Start'].dt.dayofweek
        self.df['Sourcing_start_month'] = self.df['Sourcing Start'].dt.month

        # --------------------------
        # Job Title Target Encoding
        # --------------------------
        self.jobtitle_encoding = {}

        for dur in self.durations:
            self.jobtitle_encoding[dur] = (
                self.df.groupby('Job Title')[dur].mean()
            )

        # Use sourcing-to-submission as default encoding
        default_encoding = self.jobtitle_encoding['Dur_Sourcing_to_Submission']
        self.df['JobTitle_Encoded'] = self.df['Job Title'].map(default_encoding)

        # Fallback to global mean if unseen
        self.df['JobTitle_Encoded'].fillna(
            self.df['JobTitle_Encoded'].mean(), inplace=True
        )
    
    def printdf(self):
            print(self.df.head(2))
    # --------------------------
    # Train ML models for each stage
    # --------------------------
    def train_models(self):
        from sklearn.ensemble import RandomForestRegressor
        print("training happening")
        for dur in self.durations:
            valid_rows = self.df[self.df[dur].notna()]
            if len(valid_rows) == 0:
                continue
            X = valid_rows[self.features]
            print("X",X)
            y = valid_rows[dur]
            print("y",y)
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)
            self.models[dur] = model

    # --------------------------
    # Detect current stage
    # --------------------------
    def current_stage(self, record, current_time=None):
        if current_time is None:
            current_time = pd.Timestamp.now()
        last_stage = "Not Started"
        for stage in self.stages:
            ts = record.get(stage)
            if pd.isna(ts):
                break
            if pd.to_datetime(ts) <= current_time:
                last_stage = stage
            else:
                break
        return last_stage

    # --------------------------
    # Predict remaining stages
    # --------------------------
    def predict_remaining_stages(self, record, current_time=None):
        if current_time is None:
            current_time = pd.Timestamp.now()
        
        remaining_predictions = {}
        stage = self.current_stage(record, current_time)
        print("stage",stage)
        # Start prediction from last completed stage
        if stage == 'Filled':
            return remaining_predictions  # Nothing remaining
        
        start_index = self.stages.index(stage) + 1
        print("start_index",start_index)
        prev_stage = stage
        print("prev_stage",prev_stage)
        
        for i in range(start_index, len(self.stages)):
            next_stage = self.stages[i]
            # Map prev stage to duration
            stage_to_duration = {
                'Sourcing Start': 'Dur_Sourcing_to_Submission',
                'Submission Date': 'Dur_Submission_to_InterviewStart',
                'Interview Start': 'Dur_InterviewStart_to_InterviewEnd',
                'Interview End': 'Dur_InterviewEnd_to_Offered',
                'Offered': 'Dur_Offered_to_Filled'
            }
            
            model = self.models.get(stage_to_duration.get(prev_stage))
            if model is None:
                avg_duration = self.df[stage_to_duration.get(prev_stage)].mean()
                print("used average duration fallback")
            else:
                job_title = record.get('Job Title')

                # Encode job title
                encoding_map = self.jobtitle_encoding.get(
                    stage_to_duration.get(prev_stage),
                    self.jobtitle_encoding['Dur_Sourcing_to_Submission']
                )

                job_title_value = encoding_map.get(
                    job_title,
                    self.df['JobTitle_Encoded'].mean()
                )

                features_row = [[
                    pd.to_datetime(record['Sourcing Start']).dayofweek,
                    pd.to_datetime(record['Sourcing Start']).month,
                    record.get('Salary ($1000)', self.df['Salary ($1000)'].mean()),
                    job_title_value
                ]]


                avg_duration = model.predict(features_row)[0]
                print("used ML")
            
            prev_timestamp = record.get(prev_stage)
            if pd.isna(prev_timestamp):
                prev_timestamp = pd.Timestamp.now()
            
            predicted_timestamp = pd.to_datetime(prev_timestamp) + pd.Timedelta(days=avg_duration)
            remaining_predictions[next_stage] = predicted_timestamp
            prev_stage = next_stage  # update for next iteration
            record[prev_stage] = predicted_timestamp  # propagate predicted timestamp
        
        return remaining_predictions
    def evaluate_model_performance(self, test_size=0.2, random_state=42):
        """
        Evaluate model performance using train-test split
        """
        evaluation_results = {}
        
        for dur in self.durations:
            # Skip if no data
            valid_data = self.df[self.df[dur].notna()]
            if len(valid_data) < 10:  # Minimum data points
                continue
            
            # Train-test split
            from sklearn.model_selection import train_test_split
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
            X = valid_data[self.features]
            y = valid_data[dur]
            
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state
            )
            
            # Train model
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            
            # Predictions
            y_pred = model.predict(X_test)
            
            # Calculate metrics
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)
            mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100
            
            evaluation_results[dur] = {
                'MAE_days': mae,
                'RMSE_days': rmse,
                'R2_score': r2,
                'MAPE_percent': mape,
                'samples_tested': len(y_test),
                'actual_mean_days': y_test.mean(),
                'predicted_mean_days': y_pred.mean()
            }
            
            # Store test predictions for analysis
            if not hasattr(self, 'test_predictions'):
                self.test_predictions = {}
            self.test_predictions[dur] = {
                'actual': y_test.values,
                'predicted': y_pred,
                'features': X_test.values
            }
        
        return evaluation_results
    
    def cross_validate_models(self, n_splits=5):
        """
        Perform cross-validation for more robust evaluation
        """
        from sklearn.model_selection import cross_val_score, KFold
        from sklearn.ensemble import RandomForestRegressor

        cv_results = {}

        for dur in self.durations:
            valid_data = self.df[self.df[dur].notna()]
            if len(valid_data) < n_splits * 2:  # Need enough data
                continue

            X = valid_data[self.features]
            y = valid_data[dur]

            model = RandomForestRegressor(n_estimators=100, random_state=42)
            
            # Cross-validation
            kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
            
            # Get multiple metrics
            mae_scores = cross_val_score(model, X, y, cv=kf, scoring='neg_mean_absolute_error')
            rmse_scores = cross_val_score(model, X, y, cv=kf, scoring='neg_root_mean_squared_error')
            r2_scores = cross_val_score(model, X, y, cv=kf, scoring='r2')
            
            cv_results[dur] = {
                'MAE_mean': -mae_scores.mean(),
                'MAE_std': mae_scores.std(),
                'RMSE_mean': -rmse_scores.mean(),
                'RMSE_std': rmse_scores.std(),
                'R2_mean': r2_scores.mean(),
                'R2_std': r2_scores.std()
            }
        
        return cv_results
    
    def evaluate_on_historical_candidates(self, sample_size=None):
        """
        Simulate predictions for historical candidates at various stages
        """
        results = []
        
        # Use sample if dataframe is large
        test_df = self.df if sample_size is None else self.df.sample(min(sample_size, len(self.df)))
        
        for idx, row in test_df.iterrows():
            # Simulate different current times (at each stage)
            for stage in self.stages:
                if pd.notna(row[stage]):
                    # Create record up to this stage
                    record = {}
                    for s in self.stages:
                        if self.stages.index(s) <= self.stages.index(stage):
                            record[s] = row[s]
                        else:
                            record[s] = pd.NaT
                    
                    # Predict remaining stages
                    current_time = pd.to_datetime(row[stage])
                    predictions = self.predict_remaining_stages(record, current_time)
                    
                    # Compare with actual values
                    for pred_stage, pred_date in predictions.items():
                        actual_date = row.get(pred_stage)
                        if pd.notna(actual_date):
                            error_days = (pred_date - pd.to_datetime(actual_date)).days
                            results.append({
                                'stage': pred_stage,
                                'error_days': error_days,
                                'actual_date': actual_date,
                                'predicted_date': pred_date,
                                'start_stage': stage
                            })
        
        return pd.DataFrame(results)
    
    def plot_error_distribution(self, evaluation_df):
        """
        Visualize prediction errors
        """
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()
        
        for idx, dur in enumerate(self.durations[:len(axes)]):
            if dur in self.test_predictions:
                actual = self.test_predictions[dur]['actual']
                predicted = self.test_predictions[dur]['predicted']
                errors = actual - predicted
                
                axes[idx].hist(errors, bins=20, edgecolor='black', alpha=0.7)
                axes[idx].axvline(x=0, color='r', linestyle='--', linewidth=2)
                axes[idx].set_title(f'{dur}\nMAE: {np.mean(np.abs(errors)):.1f} days')
                axes[idx].set_xlabel('Error (Actual - Predicted) days')
                axes[idx].set_ylabel('Frequency')
        
        plt.tight_layout()
        plt.show()
